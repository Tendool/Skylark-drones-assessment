# Skylark Drones — Business Intelligence Agent

A conversational agent that answers founder-level business questions by reading
two monday.com boards — **Work Orders** (project execution) and **Deals**
(sales pipeline) — live, cleaning the real-world messiness in that data along
the way, and surfacing what it can't be sure about instead of hiding it.

See [`DECISION_LOG.md`](DECISION_LOG.md) for assumptions, trade-offs, and the
interpretation of the optional "leadership updates" requirement.

## Approach

1. **Read the real data before designing anything.** Before writing code, I
   loaded both provided spreadsheets and inspected them by hand: column
   names, missingness per column, unique values per categorical field. That's
   where the two load-bearing findings came from — the `WOCOMPANY_002` vs
   `COMPANY002` client-code mismatch (the actual cross-board join key) and
   two rows in the Deals sheet that were corrupted spreadsheet-header pastes.
   Neither is mentioned in the assignment brief; both would have silently
   broken any cross-board metric if missed.
2. **Build the data layer and tools first, the LLM last.** Cleaning,
   normalization, the data-quality report, and every BI "tool" function were
   written and unit-tested against the real (masked) data with no LLM in the
   loop at all — they're plain, verifiable Python. The agent only had to get
   good at *calling* those tools correctly and being honest about their
   caveats, not at doing arithmetic itself.
3. **Get to something runnable end-to-end early, then iterate on quality.**
   The first working version (data → tools → chat) shipped before I owned
   any monday.com credentials or a final tech-stack/hosting decision, using a
   mock client generated from the real spreadsheets. UI (Streamlit → React),
   Docker, and visual polish all came after that skeleton worked, each
   verified in a real browser (Playwright) rather than assumed from reading
   the code.
4. **State assumptions instead of stalling on them.** Ambiguities that
   needed a person to resolve (monday.com credentials, sample data files,
   LLM provider, hosting target, UI framework) were surfaced as explicit
   questions; ambiguities inherent to the data or the business question
   (which date field "this quarter" means, what "revenue" means when there
   are four different money columns, how to map "energy sector" to the
   actual taxonomy) were resolved as documented assumptions in the system
   prompt and Decision Log, per the assignment's own guidance to proceed and
   document rather than block on every open question.

## AI tools used

This project was built with **Claude** (Anthropic), operating as an
autonomous coding agent (Claude Code) with real tool access — reading the
provided files, writing/running code, executing tests, running a real
browser (Playwright) to visually verify the UI, and building/running Docker
containers to verify the deployment path. I directed it turn by turn
(architecture choices, data findings, UI/stack pivots, what to verify) and
reviewed the diffs and screenshots at each step rather than accepting a
single unreviewed generation. I can walk through and justify any file in
this repo; nothing here is an unexamined pasted answer.

## Challenges faced

- **Silent data traps.** The client-code format mismatch and the corrupted
  Deals rows would not have surfaced from reading the assignment brief —
  only from inspecting the actual data — and both would have quietly
  produced wrong cross-board numbers if missed.
- **Genuine ambiguity in "revenue" and "this quarter."** Work Orders has
  four different money columns with very different fill rates, and no field
  says which date a time-boxed question should anchor on. There's no single
  correct answer here, so the system is designed to make its assumption
  visible in every answer rather than pick one silently (see Decision Log).
- **Verifying an agent I couldn't test yet.** With no LLM API key available
  for most of the build, I verified the non-LLM-dependent layers with unit
  tests and verified the full chat loop by substituting a stubbed LLM client
  in the same tool-use protocol, rather than shipping the orchestration
  layer unexercised. A Groq API key became available later and was used for
  a real, live test (see the LLM provider entry in "Trade-offs" in the
  Decision Log) — it surfaced and fixed two real cross-provider tool-calling
  bugs that the stub couldn't have caught, which is exactly why "verified
  with a stub" and "verified live" aren't the same claim.
- **Sandbox-specific Docker networking.** `npm ci` inside the containerized
  build was unreliable on this development sandbox's network (a known npm
  CLI issue under unstable connections), unrelated to the Dockerfile itself
  — verified by building the frontend on the host and the backend stage in
  Docker separately, then confirming the assembled runtime image serves
  correctly end-to-end.
- **Switching to monday.com's MCP server without a real account to test
  against.** I didn't trust assumptions here — I looked up monday.com's
  actual developer docs for the hosted MCP endpoint, auth, and exact tool
  schemas, then verified the client mechanically against a throwaway
  in-process MCP server built to those same documented schemas
  (`tests/test_mcp_client.py`), rather than writing MCP-calling code that
  had never actually been run.

## Potential improvements

See "What I'd do differently with more time" in [`DECISION_LOG.md`](DECISION_LOG.md).

## Architecture

```
monday.com (Work Orders, Deals boards)
        │  read-only, via monday.com's hosted MCP server (mcp.monday.com)
        ▼
src/monday/mcp_client.py      ──┐
src/monday/graphql_client.py  ──┤  (direct-API alternative, MONDAY_MODE=api)
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
src/agent/llm_adapter.py  provider seam (Groq, Anthropic, OpenAI all implemented; Groq is default)
        │
        ▼
backend/main.py (FastAPI)   /api/chat, /api/data-quality, /api/health
        │  REST (JSON)
        ▼
frontend/ (React + Vite)    chat UI
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
Dockerfile, docker-compose.yml  Single-container build (frontend + backend); see "Running with Docker"
backend/main.py             FastAPI app: REST endpoints, session state, static-serves frontend/dist
frontend/                   React + Vite chat UI (src/App.jsx, src/Sidebar.jsx)
src/monday/                 monday.com client (mock + real) and board schema
src/data/                   cleaning, data-quality report, cross-board join, cached repo
src/agent/                  tool schemas/impls, LLM adapter, orchestrator + system prompt
scripts/import_to_monday.py Builds fixtures/, or pushes the real data to monday.com
data/raw/                   Source spreadsheets (Work Orders, Deals) used by the import script
fixtures/                   monday.com-shaped JSON snapshot used by the mock client
tests/                      pytest suite (no API keys required)
```

## Running locally

Backend (Python):

```bash
pip install -r requirements-dev.txt   # runtime deps + pytest/httpx
python -m pytest tests/ -v            # no credentials needed

# Mock mode (default) -- runs entirely on fixtures/, no monday.com account needed
export GROQ_API_KEY=gsk-...   # free at console.groq.com, no card required
uvicorn backend.main:app --reload --port 8000
```

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev              # http://localhost:5173, proxies API calls to :8000 (see .env.development)
```

Mock mode is on by default (`MONDAY_MODE=mock`, or unset) precisely so this
project is testable without any monday.com setup — see `.env.example`.

For a single deployable service, build the frontend first and let FastAPI
serve it (`backend/main.py` mounts `frontend/dist` at `/` when present):

```bash
cd frontend && npm run build && cd ..
uvicorn backend.main:app --port 8000    # now serves both the UI and the API
```

## Running with Docker

One image, one container: a multi-stage `Dockerfile` builds the React app and
bundles it with the FastAPI backend, which serves both.

```bash
docker compose up --build
```

Open http://localhost:8000 — runs in mock mode by default, no credentials
needed. To point it at a real monday.com account and enable the chat agent,
put the variables from `.env.example` into a `.env` file next to
`docker-compose.yml` (docker compose loads it automatically) and re-run:

```bash
cat .env.example > .env   # then fill in GROQ_API_KEY, MONDAY_API_TOKEN, etc.
docker compose up --build
```

Or without compose:

```bash
docker build -t skylark-bi-agent .
docker run -p 8000:8000 \
  -e GROQ_API_KEY=gsk-... \
  -e MONDAY_MODE=live \
  -e MONDAY_API_TOKEN=eyJ... \
  -e MONDAY_WORK_ORDERS_BOARD_ID=... \
  -e MONDAY_DEALS_BOARD_ID=... \
  skylark-bi-agent
```

The one-time monday.com import script also runs inside the image:

```bash
docker run --rm -e MONDAY_API_TOKEN=eyJ... skylark-bi-agent \
  python scripts/import_to_monday.py --mode live
```

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
   export GROQ_API_KEY=gsk-...
   uvicorn backend.main:app --port 8000
   ```

`MONDAY_MODE=live` reads through monday.com's own hosted MCP server
(`https://mcp.monday.com/mcp`, via `src/monday/mcp_client.py`) rather than
calling the GraphQL API directly — same API token, no extra setup. The
direct-GraphQL client built earlier is still available as `MONDAY_MODE=api`
if you'd rather not depend on monday.com's MCP server (see Decision Log).

On a host like Render, set the same variables as environment variables /
secrets in the service settings.

## Deploying

The backend (`backend/main.py`) and frontend (`frontend/`) can ship as one
service or two:

- **One service** (simplest): the `Dockerfile` builds and serves both from a
  single container — push it to any container host (Render, Railway,
  Fly.io, ECS, Cloud Run). Without Docker, `npm run build` in `frontend/`
  then deploy the repo to something that runs `uvicorn backend.main:app`
  works the same way.
- **Two services**: deploy `frontend/` to a static host (e.g. Vercel) and
  `backend/` to an API host (e.g. Render), setting `VITE_API_BASE` (frontend
  build-time env var) to the backend's public URL and `CORS_ALLOW_ORIGINS`
  (backend env var) to the frontend's origin.

## Environment variables

See `.env.example`. Summary:

| Variable | Default | Purpose |
|---|---|---|
| `MONDAY_MODE` | `mock` | `mock` (fixtures), `live` (real account via monday.com's MCP server), or `api` (real account via direct GraphQL) |
| `MONDAY_API_TOKEN` | — | required when `MONDAY_MODE` is `live` or `api` |
| `MONDAY_WORK_ORDERS_BOARD_ID` | — | required when `MONDAY_MODE` is `live` or `api` |
| `MONDAY_DEALS_BOARD_ID` | — | required when `MONDAY_MODE` is `live` or `api` |
| `MONDAY_MCP_URL` | `https://mcp.monday.com/mcp` | override only for testing against a different MCP endpoint |
| `LLM_PROVIDER` | `groq` | `groq` (free tier, default), `anthropic`, or `openai` -- all three fully implemented |
| `GROQ_API_KEY` | — | required when `LLM_PROVIDER=groq`; free at console.groq.com |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq's current recommended tool-use model |
| `ANTHROPIC_API_KEY` | — | required when `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | — | required when `LLM_PROVIDER=openai` |
| `CORS_ALLOW_ORIGINS` | `*` | backend: comma-separated allowed origins (set to the frontend's URL when hosted separately) |
| `VITE_API_BASE` | *(empty)* | frontend build-time: backend URL when hosted separately; leave empty for same-origin (single-service) deploys |

## Tests

`python -m pytest tests/ -v` — covers client-code normalization, sector/status
canonicalization, the corrupted-row-drop logic found in the real Deals sheet,
the cross-board join, every agent tool running against the real (masked)
sample data end to end, and `MCPMondayClient` against a throwaway in-process
MCP server that mimics monday.com's documented tool contracts. None of it
needs network access, API keys, or a real monday.com account.
