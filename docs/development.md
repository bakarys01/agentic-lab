# Development Guide

## Start the app

Use Python 3.13 and `uv`:

```bash
uv sync
```

Copy `.env.example` to `.env` only if you do not already have one, and configure `OPENAI_API_KEY`. Start these services in separate terminals from the project root:

```bash
uv run python -m a2a_servers.policy_server
uv run python -m a2a_servers.research_server
uv run python -m backend.server
```

Open **http://127.0.0.1:8000**. The Python backend serves `frontend/index.html`, CSS, JavaScript and `/api/*` on the same origin. There is no frontend installation, build step, or separate Vite server. Opening the HTML file directly will not connect to the API.

The page checks `/api/health` when loaded. Click the connection indicator in the top-right corner to recheck after starting or restarting a service. Green means the concierge and specialists are reachable; amber means limited availability; red means offline. Hover over the indicator for connection details. A healthy status checks local configuration and specialist reachability; it does not prove that an external model credential is valid or has credit.

Sign in or create a local account before chatting. Each submission posts `{ "message": "...", "conversation_id": "...", "request_id": "..." }` to `/api/chat`. History is persisted per user and conversation; the concierge receives bounded recent context. See [accounts and memory](accounts-and-memory.md) for the session/CSRF contract, retries and limits.

## Configuration and service lifecycle

All three server entrypoints load the project-root `.env`. Existing process environment variables take precedence. Restart the relevant server after changing Python code or configuration. HTML/CSS/JavaScript changes are served directly; frontend responses use `Cache-Control: no-store`, and asset URLs are versioned to replace older cached assets.

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Required | Model access; all three agents use `gpt-4o` |
| `BACKEND_HOST` / `BACKEND_PORT` | `127.0.0.1` / `8000` | UI and API listener |
| `A2A_BIND_HOST` | `127.0.0.1` | Specialist listener interface |
| `POLICY_AGENT_PORT` | `9999` | Policy listener port |
| `RESEARCH_AGENT_PORT` | `9998` | Research listener port |
| `POLICY_AGENT_PUBLIC_URL` | `http://127.0.0.1:<policy port>` | Policy card and client URL |
| `RESEARCH_AGENT_PUBLIC_URL` | `http://127.0.0.1:<research port>` | Research card and client URL |

The example file explicitly sets both public URLs. Update those URLs when changing ports so clients and health checks use the new address. Keep the API local: account authentication is intended for this prototype, not public deployment. Normal terminals must permit outbound HTTPS to the model API; the research service also needs web access.

Stop each service with Ctrl+C in its terminal. Before restarting, stop the old process to avoid serving an outdated backend or encountering a port-in-use error.

`DATABASE_PATH` selects the SQLite file (default `data/concierge.sqlite3`, relative to the project root). `SESSION_COOKIE_SECURE=false` permits local HTTP; set it to true for HTTPS. Run a single backend process/worker. Accounts/history are created automatically on first use; do not commit the database.

## Docker development

From the repository root, with Docker running and `OPENAI_API_KEY` configured in `.env`:

```bash
docker compose up --build -d --wait
docker compose ps
```

Open `http://127.0.0.1:8000`. Only the backend port is published, bound to host loopback. Specialist traffic uses internal service names. All services have healthchecks; the backend waits for healthy specialist cards and its own check requires `/api/health` to return `status: ok`. These checks do not invoke the model, validate credit, or automatically restart an unhealthy running process.

The backend runs as `appuser` with `DATABASE_PATH=/app/data/concierge.sqlite3`. The named `backend-data` volume persists accounts/history across container recreation; its actual name is prefixed by the Compose project name. The image pre-creates `/app/data` with runtime-user ownership for a new volume. An existing volume must have compatible ownership. The Policy image copies only the example PDF; SQLite files and journals are excluded from the build context.

Use `docker compose down` to stop/remove containers while retaining data. **Do not use `docker compose down -v` unless deliberately deleting accounts and history.** A volume is not a backup: stop the backend before an offline SQLite copy, retain the backup privately outside the container, and test restoration.

When upgrading from the original configuration without a volume, stop the old backend and copy its `/app/data/concierge.sqlite3` to a private backup **before recreating it**. Restore that database into the new volume before starting the backend, with ownership matching `appuser`. Do not overwrite an already populated volume. The host's `data/concierge.sqlite3` and the container's database are separate; do not assume they contain the same accounts. Preserve the original backup until login/history have been verified.

## HTTPS preparation (MED-3 — in progress)

`docker-compose.https.yml` adds Caddy in front of the same-origin UI/API, removes the backend's published port and enables `SESSION_COOKIE_SECURE=true`. Only the proxy publishes ports 80/443. Uvicorn trusts forwarded client/protocol headers from `172.30.50.2` only in this configuration. Docker allocates dynamic proxy-network addresses from `172.30.50.128/25`, keeping Caddy's fixed address outside that range.

Set `APP_DOMAIN` (hostname only) and `ACME_EMAIL` in `.env`; `.env.example` documents these variables but does not supply them to Compose. Placeholder values are suitable for configuration checks only. The proxy waits up to 170 seconds for backend response headers, before the frontend's 180-second timeout, and provides a JSON error on proxy failure. This does not cancel ongoing agent execution.

Preparation checks:

```bash
docker compose -f docker-compose.yml -f docker-compose.https.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.https.yml run --rm --no-deps proxy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
uv run python -m pytest tests/test_proxy_headers.py -q
```

Recorded during setup: Compose/Caddy configuration validation succeeded and both proxy-header unit tests passed. These tests check Uvicorn middleware behavior for trusted/untrusted peers; they do not test the deployed Caddy-to-backend chain. The validation container does not publish service ports, but Compose may create networks and volumes.

The source file is named `Caddyfile`, matching the Compose mount exactly. Preserve this capitalization when deploying on Linux.

**Still pending:** a controlled domain and server, DNS, a valid public certificate and renewal verification, HTTP-to-HTTPS redirection, secure-cookie/CSRF login flows, actual forwarded client addresses and proxy timeout behavior. Local HTTPS testing was deferred. Do not start the public HTTPS configuration with placeholder domain values or consider MED-3 complete. Private-access controls must be ready before exposing the beta.

Continue using `docker compose up -d --wait` and `http://127.0.0.1:8000` for local development. If switching back from the HTTPS stack, first run `docker compose -f docker-compose.yml -f docker-compose.https.yml down` **without `-v`** to retain the database and Caddy volumes. Caddy certificate state is stored in `caddy-data`; do not delete it during normal updates.

## Dependencies

Runtime dependencies cover A2A, the Python API, OpenAI-backed smolagents, web search and PDF retrieval. Course-demo libraries were removed. `uv sync` also installs the default development group (pytest and Selenium); use `uv sync --no-dev` for runtime only.

## Checks

Run API and concierge regression tests:

```bash
uv run python -m pytest tests --ignore=tests/test_frontend_browser.py -q -p no:cacheprovider
```

Run dependency-free frontend tests (Node.js 22+):

```bash
node --test tests/frontend.test.cjs
```

Run real-browser integration tests with Chrome installed (Selenium may download a matching driver on first use):

```bash
uv run python -m pytest tests/test_frontend_browser.py -q -p no:cacheprovider
```

Browser tests start a temporary local API with a deterministic concierge. They exercise page serving, same-origin submission, response rendering, error recovery, quick questions and mobile layout without paid model requests. They create temporary accounts/databases and also verify login, account isolation, follow-up context, history restoration and deletion.

For Python coverage of the backend and memory code:

```bash
uv run --with pytest-cov python -m pytest tests --cov=backend --cov=agents.concierge_agent --cov=agents.conversation_memory --cov-report=term-missing --cov-fail-under=80
```

## Troubleshooting

- **Offline indicator:** start the backend and open its URL, rather than opening `index.html` from disk.
- **Concierge unavailable:** check server configuration and `OPENAI_API_KEY` in `.env`.
- **Limited indicator:** start both A2A servers and check their configured URLs/ports.
- **Green indicator but request fails:** check model credentials/credit and outbound HTTPS permissions. Health checks do not invoke the model. User-facing errors do not expose provider details.
- **Session expired (401):** sign in again; persisted conversations remain available.
- **Session verification failed (403):** reload to obtain the current CSRF token.
- **Busy response (503):** another request is already running; retry after it finishes. Requests are not queued.
- **Old styles or missing messages:** reload the page and confirm you opened the backend URL. Restart any old backend process so the current static-file cache policy is active.

Default specialist health URLs:

```text
http://127.0.0.1:9999/.well-known/agent-card.json
http://127.0.0.1:9998/.well-known/agent-card.json
```

The frontend is in `frontend/index.html`, `frontend/styles.css`, and `frontend/app.js`. API routes live in `backend/api.py`; orchestration lives in `agents/concierge_agent.py` and `tools/concierge_tools.py`.
