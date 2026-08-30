# Decision Log

## Key assumptions

**Join key between boards.** The two sheets identify the same client two
different ways: Work Orders uses `Customer Name Code` ("WOCOMPANY_002"),
Deals uses `Client Code` ("COMPANY002"). I confirmed by stripping the `WO`
prefix that 50/51 Work Order client codes match a Deals client code exactly,
so I normalize both to `COMPANY###` and join on that
(`src/data/normalize.normalize_client_code`). I deliberately did **not** join
on `Deal name masked` / `Deal Name` — it's a reused persona-style alias
("Sakura" appears under 27 different deal rows across many different client
codes), so joining on it would silently merge unrelated clients.

**Two corrupted rows in the Deals sheet.** Rows 50 and 179 have a spreadsheet
header row pasted into the data (every column literally contains its own
column name as the value). These are dropped at import time with a logged
warning rather than silently ignored or force-parsed
(`src/monday/build_items.rows_to_items`).

**"Revenue" is not one number.** Work Orders carries four distinct money
columns (contracted value, billed value, collected amount, receivable), each
with different — and very different — fill rates (0%–56% missing). Rather
than pick one and call it "revenue," every tool that touches money reports
the breakdown with a known/missing count per figure, and the system prompt
tells the agent to say which figure it's leading with and why.

**Date ambiguity.** Founder questions like "this quarter" don't specify which
date field to anchor on (deal created vs. tentative close vs. work order
start/end vs. invoice date), and different questions genuinely want different
ones. Tools take an explicit `date_field` parameter with a sensible default,
and the system prompt requires the agent to state which one it used rather
than pick silently.

**Sector vocabulary.** Founders will say "energy sector" when the data's
actual label is "Renewables." I didn't build a hardcoded synonym table (too
brittle, and I have no product/domain confirmation on the full mapping);
instead the system prompt tells the model to map obvious colloquial terms
itself, state the mapping it used, and ask instead of guessing when it's
genuinely ambiguous.

## Trade-offs chosen and why

**monday.com's own MCP server, with a direct-API fallback kept.** Both are
allowed ("MCP or API — your choice"). monday.com hosts the MCP server itself
at `https://mcp.monday.com/mcp` (Streamable HTTP, same personal API token as
a Bearer header) — nothing of ours to deploy — so `MONDAY_MODE=live` goes
through it (`src/monday/mcp_client.py`); a direct-GraphQL client is kept as
`MONDAY_MODE=api` in case of MCP downtime. Initially this was only unit-tested
against a mock server built from monday.com's *documented* tool schemas, with
no live account to check it against. Once credentials arrived, a live run
against a real account surfaced three real gaps the docs hadn't caught: the
actual tool is `get_board_items_page`, not `get_board_items`; its
`column_values` comes back as a flat `{column_id: text}` dict, not the
list-of-objects shape assumed; and the client imported a stray `httpx2`
package instead of `httpx`, which only "worked" locally because an unrelated
same-named package happened to be installed on the dev machine — it would
have failed on any clean deploy. All three are fixed, the test now mocks the
real contract, and `httpx` is a declared dependency. Re-verified live
end-to-end after the fix: real board data now flows correctly through the MCP
client, cleaning, join, and every agent tool. The clearest example in this
project of "unit-tested against a schema" not being "works against the real
thing" — see also the Groq entry below.

**Mock client behind the same interface, built first.** No monday.com
credentials existed at the start of the build, so `MondayClient` was made one
interface every implementation (mock, MCP, direct API) satisfies identically,
with mock fixtures generated from the **real** provided spreadsheets (not
synthetic data). Everything downstream was built and tested against real data
from day one; switching `MONDAY_MODE` is a config change, not a rewrite.

**FastAPI + React over Streamlit.** The first working version used Streamlit
for speed. Given this is a *full-stack* assignment, I rebuilt it as a proper
split: FastAPI backend (`/api/chat`, `/api/data-quality`, `/api/health`) and a
separate React/Vite frontend over REST/JSON. Costs more build time and a
hand-rolled session model (in-memory per-session tool-use history, keyed by a
UUID), but demonstrates real frontend/backend separation and deploys
flexibly — one service or two — rather than Streamlit's runtime model.

**One Docker image, not two.** A multi-stage `Dockerfile` builds the React
app and bundles it with the FastAPI backend, which serves the built assets
itself. A split image pair would mirror the "two services" deploy option, but
for a graded, link-testable prototype, one `docker run`/`docker compose up`
is less for a reviewer to get wrong.

**Groq as the default LLM, over paying for Anthropic/OpenAI.** The provider
choice was left open, and Groq's API is OpenAI-compatible with a genuinely
free tier and real tool-calling. One `OpenAICompatibleAdapter` backs both Groq
and (via `base_url`) real OpenAI; `AnthropicAdapter` stays fully working via
`LLM_PROVIDER=anthropic`. **This is the only LLM path that's been live-tested
against its real API**, and it earned its keep: it surfaced two cross-provider
bugs no stub would have caught — Groq rejects an explicit `tool_calls: null`
on a plain-text turn (must be absent, not null), and rejects `null` for an
optional parameter unless its schema declares that property nullable. Both
fixed in `llm_adapter.py`, with network-free regression tests.

**Tools return aggregates, not raw rows.** Every tool caps and summarizes
(counts, sums, breakdowns, a small sample) instead of returning full board
dumps, so the model reasons over numbers it can trust and a query against
300+ deals doesn't blow the context window.

## What I'd do differently with more time

- Fuzzy/approximate client matching for Work Orders without a resolvable
  client code, instead of excluding them from joins.
- A real caching layer (TTL + background refresh) instead of "cache for the
  process lifetime, manual refresh button."
- A lightweight eval set (founder questions with expected tool calls, run
  against all three LLM providers) to catch prompt/provider regressions.
- Push tool-call transcripts into the UI so a skeptical founder can see
  exactly which board query backs a number.
- Multi-turn clarifying questions rely entirely on the system prompt; a
  stricter state machine would make "ask before guessing" more reliable.

## How I interpreted "leadership updates"

I read this as: founders periodically need to paste a clean, accurate status
into a deck or email, and today that means someone manually pulling and
reconciling numbers from both boards. I implemented
`generate_leadership_summary` as an on-demand tool (callable via chat, e.g.
"prepare a leadership update for Mining") that assembles pipeline health,
delivery/operations status, and the revenue breakdown for a scope (all
sectors or one), and always appends the current data-quality caveats relevant
to that scope — so the summary is something a founder can hand off externally
without separately having to ask "but can I trust this number."
