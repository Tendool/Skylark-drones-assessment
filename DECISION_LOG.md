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

**Direct GraphQL API over MCP.** Both are allowed by the assignment. I chose
a small, purpose-built read-only GraphQL client
(`src/monday/graphql_client.py`) over monday.com's MCP server because it's a
single dependency-free HTTP call I fully control and can unit-test, and it
deploys as one process with no separate MCP server to host and keep alive for
a graded, link-testable demo. The trade-off: I don't get MCP's
tool-discovery for free, and a future integration with other monday.com
boards means writing more GraphQL by hand instead of getting it from the MCP
server's schema introspection.

**Mock/live client behind one interface, built first.** I had no monday.com
credentials in the assessment environment. Rather than block on that, I built
`MondayClient` as an interface both a fixture-backed mock and the real
GraphQL client implement identically (`{"id","name","column_values":[...]}`),
generated the mock fixtures from the **real** provided spreadsheets (not
synthetic data), and wrote `scripts/import_to_monday.py` to do the real
push once credentials exist. Everything downstream — cleaning, tools, agent,
UI — was built and tested against real data from day one; switching to
`MONDAY_MODE=live` is a config change, not a rewrite.

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

**LLM provider is pluggable but only Anthropic is implemented.** The choice
of provider/API key wasn't settled at build time, so `src/agent/llm_adapter.py`
defines a small `LLMAdapter` protocol; `AnthropicAdapter` is complete,
`OpenAIAdapter` is a documented stub with the same interface. Swapping is a
one-line change in `src/config.py` plus filling in the stub.

**Tools return aggregates, not raw rows.** Every tool caps and summarizes
(counts, sums, breakdowns, a small sample) instead of returning full board
dumps, so the model reasons over numbers it can trust rather than re-deriving
sums from a wall of text, and so a query against 300+ deals doesn't blow the
context window.

## What I'd do differently with more time

- Fuzzy/approximate client matching for the small number of Work Orders
  without a resolvable client code, instead of excluding them from joins.
- A real caching layer with TTL + background refresh instead of "cache for
  the Streamlit session, manual refresh button."
- Finish the OpenAI adapter and add a lightweight eval set (a dozen founder
  questions with expected tool calls) to catch prompt regressions.
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
