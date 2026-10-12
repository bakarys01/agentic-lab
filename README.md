# Agentic Lab — MediNova Healthcare Concierge

MediNova is a modular healthcare concierge reference application. A manager agent routes questions over A2A to four specialists: insurance policy, health research, provider directory and medication catalog. Each specialist accesses its tools through MCP. The browser application adds accounts and persistent conversations.

The repository has three detailed documents:

- [Architecture and contributor guide](docs/architecture.md): actual components, setup, configuration, request flow, adding an agent, tests and limits.
- [Agent guide (French)](docs/agents.md): each agent's role, request flow, sources, limits and extension steps.
- [Roadmap](docs/roadmap.md): future experiments and evidence needed to complete them.

## Quick start

From the repository root, copy `.env.example` to `.env` and set `OPENAI_API_KEY`, `HF_TOKEN` and a strong `MEDICATION_DB_PASSWORD`. Ensure the sample insurance PDF and doctor directory are present in `data/`. Start the complete application with one command:

~~~bash
docker compose up -d --build
~~~

Compose starts the backend, four specialist services and PostgreSQL. Open http://127.0.0.1:8000, create an account, and start chatting. Use `docker compose ps` to check that all six services are healthy; `docker compose down` stops them. The database volumes remain intact. A fresh PostgreSQL volume has only its schema until the medication sample is imported.

To load a reproducible sample of 500 real specialties and all their related presentations and compositions from the [French public medication database (BDPM)](https://base-donnees-publique.medicaments.gouv.fr/telechargement), run `docker compose --profile import run --rm medication-importer`. This is a separate, on-demand import; it replaces the previous BDPM sample in one database transaction and records each source file's URL, update date and SHA-256. To change the sample size, append `--limit N` to the command.

To inspect the tables in a browser, set `PGADMIN_EMAIL` and `PGADMIN_PASSWORD` in `.env`, then run `docker compose --profile admin up -d pgadmin` and open http://127.0.0.1:5050. Sign in with those pgAdmin credentials and open the preconfigured **MediNova medications** server; when prompted, enter `MEDICATION_DB_PASSWORD`. The interface is only bound to the local machine. Stop it with `docker compose stop pgadmin`.

To run or debug components independently without Docker, install Python 3.13 and uv, then run `uv sync` to install the package from `src/medinova/`. Start these commands in separate terminals. The medication specialist additionally needs a reachable PostgreSQL server and PGHOST, PGDATABASE, PGUSER and PGPASSWORD set locally; Compose provides them automatically:

~~~bash
uv run --env-file .env python -B -m medinova.a2a_servers.serve policy
uv run --env-file .env python -B -m medinova.a2a_servers.serve research
uv run --env-file .env python -B -m medinova.a2a_servers.serve healthcare_provider
uv run --env-file .env python -B -m medinova.a2a_servers.serve medication
uv run --env-file .env python -B -m medinova.backend.server
~~~

With the specialist services running, you can also call a configured agent from the CLI:

~~~bash
uv run --env-file .env python -B -m medinova.examples.run_agent concierge "What is my deductible, what treatments exist for depression, and which psychiatrists are in Paris?"
~~~

Keep model credentials in .env and keep specialist A2A endpoints private. See the [architecture guide](docs/architecture.md) for the complete setup, contracts and extension steps.

## Checks

~~~bash
uv run python -B -m pytest tests -q
node --test tests/frontend.test.cjs
~~~

This is a local engineering reference. Policy retrieval uses a shared PDF, provider results use a static directory, and tests do not establish medical correctness or production readiness.
