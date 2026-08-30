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
allowed ("MCP or API — your choice"). I first built a read-only GraphQL
client (`src/monday/graphql_client.py`), assuming MCP would mean hosting a
separate server process alongside the app for no functional gain. Checking
monday.com's docs corrected that: monday.com hosts the MCP server itself, at
`https://mcp.monday.com/mcp` (Streamable HTTP, same personal API token as a
Bearer header) — nothing of ours to deploy. That removed the objection, so
`MONDAY_MODE=live` now goes through it (`src/monday/mcp_client.py`, the
documented `get_board_info`/`get_board_items` tools, official `mcp` Python
SDK); the direct-GraphQL client is kept as `MONDAY_MODE=api`, since a hard
dependency on monday.com's own MCP uptime is itself worth a fallback for.
Built and unit-tested against an in-process MCP server mirroring monday.com's
published tool schemas (`tests/test_mcp_client.py`) — not yet exercised
against the real endpoint, since no live account was available.

**Mock client behind the same interface, built first.** I had no monday.com
credentials in the assessment environment. Rather than block on that, I built
`MondayClient` as one interface every implementation (mock, MCP, direct API)
satisfies identically (`{"id","name","column_values":[...]}`), generated the
mock fixtures from the **real** provided spreadsheets (not synthetic data),
and wrote `scripts/import_to_monday.py` to do the real push once credentials
exist. Everything downstream — cleaning, tools, agent, UI — was built and
tested against real data from day one; switching `MONDAY_MODE` is a config
change, not a rewrite.

**FastAPI + React over Streamlit.** The first working version used Streamlit
for speed. Given this is titled a *full-stack* assignment, I rebuilt the UI
as a proper split: a FastAPI backend (`backend/main.py`, exposing
`/api/chat`, `/api/data-quality`, `/api/health`) and a separate React/Vite
frontend (`frontend/`), talking over REST/JSON. This costs more build time
than Streamlit and requires picking a session model by hand (in-memory
per-session tool-use history, keyed by a UUID the frontend holds), but
demonstrates an actual frontend/backend separation and deploys flexibly —
one service (FastAPI serving the built React app) or two (static frontend +
API host) — rather than being locked into Streamlit's runtime model.

**One Docker image, not two.** The `Dockerfile` is a multi-stage build: a
Node stage builds the React app, then a Python stage bundles it with the
FastAPI backend, which serves the built assets itself
(`backend/main.py` mounts `frontend/dist`). A separate frontend/backend
image pair would mirror the "two services" deploy option, but for a
graded, link-testable prototype, one image that runs with a single
`docker run`/`docker compose up` is less for a reviewer to get wrong.

**Groq as the default LLM, over paying for Anthropic/OpenAI.** The provider
choice was explicitly left open, and a free option turned out to exist:
Groq's API is OpenAI-compatible with a genuinely free tier (no card) and
real tool-calling. I implemented one `OpenAICompatibleAdapter` (works
against real OpenAI or any compatible provider via `base_url`) and pointed
`GroqAdapter` at it with `openai/gpt-oss-120b` — Groq's recommended model
for tool use since deprecating `llama-3.3-70b-versatile` in June 2026. This
finishes the OpenAI adapter for free (same code path); `AnthropicAdapter`
stays fully working via `LLM_PROVIDER=anthropic`. **This is the only path
here that's been live-tested against its real API**, and it earned its
keep: it surfaced two cross-provider bugs no stub or doc-reading would have
caught — Groq rejects an explicit `tool_calls: null` on a plain-text turn
(must be absent, not null), and rejects `null` for an optional parameter
unless its schema declares that property nullable (Claude just omits unused
params instead). Both fixed in `llm_adapter.py`, with network-free
regression tests (`tests/test_llm_adapter.py`) — the clearest case in this
project of "verified against a stub" not being "verified live."

**Tools return aggregates, not raw rows.** Every tool caps and summarizes
(counts, sums, breakdowns, a small sample) instead of returning full board
dumps, so the model reasons over numbers it can trust rather than re-deriving
sums from a wall of text, and so a query against 300+ deals doesn't blow the
context window.

## What I'd do differently with more time

- Fuzzy/approximate client matching for the small number of Work Orders
  without a resolvable client code, instead of excluding them from joins.
- A real caching layer with TTL + background refresh instead of "cache for
  the process lifetime, manual refresh button."
- Add a lightweight eval set (a dozen founder questions with expected tool
  calls, run against all three LLM providers) to catch prompt regressions
  and provider-specific behavior differences going forward.
- Push tool-call transcripts into the UI (collapsible) so a skeptical founder
  can see exactly which board query backs a number, not just trust the
  agent's summary.
- Multi-turn clarifying questions currently rely entirely on the system
  prompt; a stricter state machine would make "ask before guessing" more
  reliable under adversarial phrasing.

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
