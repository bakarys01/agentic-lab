# Agentic Lab — MediNova Healthcare Concierge

MediNova is a modular healthcare concierge reference application. A manager agent routes questions over A2A to three specialists: insurance policy, health research and provider directory. Each specialist accesses its tools through MCP. The browser application adds accounts and persistent conversations.

The repository has two detailed documents:

- [Architecture and contributor guide](docs/architecture.md): actual components, setup, configuration, request flow, adding an agent, tests and limits.
- [Roadmap](docs/roadmap.md): future experiments and evidence needed to complete them.

## Quick start

From the repository root, copy `.env.example` to `.env` and set `OPENAI_API_KEY` and `HF_TOKEN`. Ensure the sample insurance PDF and doctor directory are present in `data/`. Start the complete application with one command:

~~~bash
docker compose up -d --build
~~~

Compose starts the backend and all configured specialist services. Open http://127.0.0.1:8000, create an account, and start chatting. Use `docker compose ps` to check that all four services are healthy; `docker compose down` stops them. The conversation database remains in the Compose volume.

To run or debug components independently without Docker, install Python 3.13 and uv, then run `uv sync`. Start these commands in separate terminals:

~~~bash
uv run --env-file .env python -m a2a_servers.serve policy
uv run --env-file .env python -m a2a_servers.serve research
uv run --env-file .env python -m a2a_servers.serve healthcare_provider
uv run --env-file .env python -m backend.server
~~~

With the specialist services running, you can also call a configured agent from the CLI:

~~~bash
uv run --env-file .env python -m examples.run_agent concierge "What is my deductible, what treatments exist for depression, and which psychiatrists are in Paris?"
~~~

Keep model credentials in .env and keep specialist A2A endpoints private. See the [architecture guide](docs/architecture.md) for the complete setup, contracts and extension steps.

## Checks

~~~bash
uv run python -m pytest tests -q -p no:cacheprovider
node --test tests/frontend.test.cjs
~~~

This is a local engineering reference. Policy retrieval uses a shared PDF, provider results use a static directory, and tests do not establish medical correctness or production readiness.
