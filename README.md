# Skylark Drones — Business Intelligence Agent

A conversational agent that answers founder-level business questions by reading
two monday.com boards — **Work Orders** (project execution) and **Deals**
(sales pipeline) — live, cleaning the real-world messiness in that data along
the way, and surfacing what it can't be sure about instead of hiding it.

See [`DECISION_LOG.md`](DECISION_LOG.md) for assumptions, trade-offs, and the
interpretation of the optional "leadership updates" requirement.

## Architecture

```
monday.com (Work Orders, Deals boards)
        │  read-only GraphQL API
        ▼
src/monday/graphql_client.py  ──┐
src/monday/mock_client.py     ──┴─►  MondayClient interface (client_interface.py)
        │
        ▼
src/data/normalize.py   clean dates, canonical sectors/status, client-code join key
src/data/quality.py     missingness + known-issue report per board
src/data/join.py        cross-board join on normalized client code
        │
        ▼
src/data/repo.py (DataRepo)   cached cleaned DataFrames + quality report for a session
        │
        ▼
src/agent/tools.py        BI functions (pipeline, revenue, operations, leadership brief)
src/agent/orchestrator.py tool-use loop + system prompt
src/agent/llm_adapter.py  provider seam (Anthropic implemented, OpenAI stubbed)
        │
        ▼
app/streamlit_app.py   chat UI
```

One-time, out-of-band (not part of the running app):

```
data/raw/*.xlsx  →  scripts/import_to_monday.py  →  monday.com boards
                                                  └─► fixtures/*.json (mock mode)
```

The app itself only ever **reads** from monday.com, per the assignment's
Integration Requirements.

## Repo layout

```
app/streamlit_app.py        Chat UI
src/monday/                 monday.com client (mock + real) and board schema
src/data/                   cleaning, data-quality report, cross-board join, cached repo
src/agent/                  tool schemas/impls, LLM adapter, orchestrator + system prompt
scripts/import_to_monday.py Builds fixtures/, or pushes the real data to monday.com
data/raw/                   Source spreadsheets (Work Orders, Deals) used by the import script
fixtures/                   monday.com-shaped JSON snapshot used by the mock client
tests/                      pytest suite (no API keys required)
```

## Running locally

```bash
pip install -r requirements.txt
python -m pytest tests/ -v          # no credentials needed

# Mock mode (default) -- runs entirely on fixtures/, no monday.com account needed
export ANTHROPIC_API_KEY=sk-...
streamlit run app/streamlit_app.py
```

Mock mode is on by default (`MONDAY_MODE=mock`, or unset) precisely so this
project is testable without any monday.com setup — see `.env.example`.

## Connecting to a real monday.com account

1. **Get an API token**: monday.com → avatar → *Admin* → *API* (or *Developers*
   → *My Access Tokens*). Needs at least read access to the target workspace.
2. **Create the boards and load the data**:
   ```bash
   export MONDAY_API_TOKEN=eyJ...
   python scripts/import_to_monday.py --mode live
   ```
   This creates a "Work Orders" and a "Deals" board with columns matching
   `src/monday/schema.py`, and pushes every row from `data/raw/*.xlsx` as an
   item. It prints the two board IDs at the end.
3. **Point the app at them**:
   ```bash
   export MONDAY_MODE=live
   export MONDAY_API_TOKEN=eyJ...
   export MONDAY_WORK_ORDERS_BOARD_ID=<from step 2>
   export MONDAY_DEALS_BOARD_ID=<from step 2>
   export ANTHROPIC_API_KEY=sk-...
   streamlit run app/streamlit_app.py
   ```

On Streamlit Community Cloud, set the same variables under the app's
**Settings → Secrets** instead of shell exports — `app/streamlit_app.py`
mirrors `st.secrets` into `os.environ` on startup.

## Environment variables

See `.env.example`. Summary:

| Variable | Default | Purpose |
|---|---|---|
| `MONDAY_MODE` | `mock` | `mock` (fixtures) or `live` (real monday.com API) |
| `MONDAY_API_TOKEN` | — | required when `MONDAY_MODE=live` |
| `MONDAY_WORK_ORDERS_BOARD_ID` | — | required when `MONDAY_MODE=live` |
| `MONDAY_DEALS_BOARD_ID` | — | required when `MONDAY_MODE=live` |
| `LLM_PROVIDER` | `anthropic` | `anthropic` (implemented) or `openai` (stub, see `src/agent/llm_adapter.py`) |
| `ANTHROPIC_API_KEY` | — | required for the chat agent to run |

## Tests

`python -m pytest tests/ -v` — covers client-code normalization, sector/status
canonicalization, the corrupted-row-drop logic found in the real Deals sheet,
the cross-board join, and every agent tool running against the real (masked)
sample data end to end. None of it needs network access or API keys.
