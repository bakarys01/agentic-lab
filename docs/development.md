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

Each submission posts `{ "message": "..." }` to `/api/chat`. Questions are limited to 8,000 characters. The browser displays questions and replies in order until the page is refreshed. Requests are independent; earlier messages are not sent as conversation context. The response includes the answer, consulted specialists, request ID and elapsed time. Errors keep the question available for retry. Browser requests time out after three minutes; stopping the browser request does not cancel work already running on the server.

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

The example file explicitly sets both public URLs. Update those URLs when changing ports so clients and health checks use the new address. Keep the API local: it has no authentication. Normal terminals must permit outbound HTTPS to the model API; the research service also needs web access.

Stop each service with Ctrl+C in its terminal. Before restarting, stop the old process to avoid serving an outdated backend or encountering a port-in-use error.

## Dependencies

Runtime dependencies cover A2A, the Python API, OpenAI-backed smolagents, web search and PDF retrieval. Course-demo libraries were removed. `uv sync` also installs the default development group (pytest and Selenium); use `uv sync --no-dev` for runtime only.

## Checks

Run API and concierge regression tests:

```bash
uv run python -m pytest tests/test_api.py tests/test_backend_concierge.py tests/test_agent_configuration.py tests/test_static_assets.py -q -p no:cacheprovider
```

Run dependency-free frontend tests (Node.js 22+):

```bash
node --test tests/frontend.test.cjs
```

Run real-browser integration tests with Chrome installed (Selenium may download a matching driver on first use):

```bash
uv run python -m pytest tests/test_frontend_browser.py -q -p no:cacheprovider
```

Browser tests start a temporary local API with a deterministic concierge. They exercise page serving, same-origin submission, response rendering, error recovery, quick questions and mobile layout without paid model requests.

## Troubleshooting

- **Offline indicator:** start the backend and open its URL, rather than opening `index.html` from disk.
- **Concierge unavailable:** check server configuration and `OPENAI_API_KEY` in `.env`.
- **Limited indicator:** start both A2A servers and check their configured URLs/ports.
- **Green indicator but request fails:** check model credentials/credit and outbound HTTPS permissions. Health checks do not invoke the model. User-facing errors do not expose provider details.
- **Busy response (503):** another request is already running; retry after it finishes. Requests are not queued.
- **Old styles or missing messages:** reload the page and confirm you opened the backend URL. Restart any old backend process so the current static-file cache policy is active.

Default specialist health URLs:

```text
http://127.0.0.1:9999/.well-known/agent-card.json
http://127.0.0.1:9998/.well-known/agent-card.json
```

The frontend is in `frontend/index.html`, `frontend/styles.css`, and `frontend/app.js`. API routes live in `backend/api.py`; orchestration lives in `agents/concierge_agent.py` and `tools/concierge_tools.py`.
