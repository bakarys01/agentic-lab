# Architecture and contributor guide

This document describes the code in this repository. [The roadmap](roadmap.md) tracks future experiments. The reference application is MediNova, a healthcare concierge that routes a question to independent specialists. Configuration selects an agent's prompt, runtime, model, tools, delegates and network port; Python adapters implement the supported combinations.

## Start here

From the repository root, use Python 3.13 and uv:

~~~bash
uv sync
~~~

Copy .env.example to .env and set OPENAI_API_KEY and HF_TOKEN. The policy and research agents use OpenAI gpt-4o; the healthcare provider uses Hugging Face openai/gpt-oss-20b. The insurance PDF and doctor directory must exist at data/2026AnthemgHIPSBC.pdf and data/doctors.json. Never commit .env or the conversation database.

Open four terminals and run one command in each:

~~~bash
uv run --env-file .env python -m a2a_servers.serve policy
uv run --env-file .env python -m a2a_servers.serve research
uv run --env-file .env python -m a2a_servers.serve healthcare_provider
uv run --env-file .env python -m backend.server
~~~

The commands above are separate long-running processes, not a single shell script. Open http://127.0.0.1:8000, create an account, and start a conversation. For a command-line check, use:

~~~bash
uv run --env-file .env python -m examples.run_agent concierge "What is my deductible, what are common treatments for depression, and which psychiatrists are in Paris?"
~~~

The A2A servers must already be running for the concierge to delegate. If an activated environment points to another project, use uv run without activating it. On Windows, the project's .venv/Scripts/python.exe is an alternative; use uv's --env-file option for command-line clients that do not load .env themselves.

The same four services are described by docker-compose.yml. Set both model tokens in .env and run docker compose up --build. docker-compose.https.yml adds the optional Caddy proxy; it is not needed for local development. Compose configuration can be checked without starting containers with docker compose --env-file .env.example config --quiet. The backend listens on port 8000; specialist ports are internal to the Compose network.

## Running architecture

~~~mermaid
flowchart LR
    User[Browser or CLI] --> API[FastAPI backend]
    API --> DB[(SQLite accounts and conversations)]
    API --> C[Concierge: AgentRuntime / smolagents]
    C -->|A2A JSON-RPC| P[Policy A2A server]
    C -->|A2A JSON-RPC| R[Research A2A server]
    C -->|A2A JSON-RPC| H[Healthcare provider A2A server]
    P -->|MCP stdio| PT[search_policy]
    PT --> PDF[(Insurance PDF)]
    R -->|MCP stdio| RT[web_search]
    RT --> Web[(Web)]
    H -->|MCP stdio| HM[list_doctors]
    HM --> Doctors[(doctors.json)]
    C -.-> O[OpenAI model]
    P -.-> O
    R -.-> O
    H -.-> HF[Hugging Face model]
~~~

The browser, API and concierge share the backend process. Each specialist has its own A2A server process. Each specialist's MCP server is a stdio subprocess started by its MCP client, not another network endpoint. A2A carries concierge-to-specialist requests; MCP connects specialists to tools, which read the PDF, doctor directory or web. The current sample uses one MCP server per specialist, but the configuration permits multiple agents to reference the same server.

The concierge's smolagents tool names are generated as ask_policy, ask_research and ask_healthcare_provider. Their descriptions come from each specialist's AgentDefinition. The model chooses tools using those descriptions and prompts/concierge.md; no fixed number of specialists is written into the prompt. Each tool calls the generic A2A client. The specialist server constructs the same AgentRuntime for its configured agent and returns a text message.

## Where things live

| Path | Responsibility |
| --- | --- |
| config/agents.yaml | Agent definitions, model references, execution profiles, selected tools, MCP server settings and A2A ports |
| agents/definition.py | Immutable AgentDefinition schema and defaults |
| agents/config_loader.py | Read and validate the configuration; resolve MCP script paths |
| agents/runtime.py | Build an agent, choose its framework adapter, run it, report tool usage and check delegate A2A cards |
| agents/models.py | Create a model from a model profile and its credential environment variable |
| agents/conversation_memory.py | Select a bounded suffix of completed conversation pairs |
| prompts/*.md and prompts/loader.py | Versioned instructions, loaded by configured prompt name |
| mcp_servers/{policy,research,healthcare}.py | Expose the policy PDF search, source-attributed web search and doctor directory as MCP tools |
| tools/delegation.py and a2a_clients/client_utils.py | Turn a synchronous manager tool call into an A2A client request |
| tools/mcp_connector.py | Connect to configured stdio MCP servers and enforce each server's allowed_tools list |
| a2a_servers/{serve,app,card,executor}.py | Start any configured A2A agent; publish its Agent Card and JSON-RPC route |
| backend/{api,auth,storage,server,title_generation}.py | HTTP API, authentication, SQLite, static files, server entry point and automatic chat titles |
| frontend/ | Browser UI served by the backend |
| main.py and examples/run_agent.py | Interactive CLI and one-shot configured agent runner |
| tests/ | Python regression, frontend and browser checks |

The generic A2A launcher is python -m a2a_servers.serve NAME. There are no agent-specific server or client modules to edit when adding a specialist.

## Configuration contract

config/agents.yaml has version: 1. Its main sections are:

- agents: name to role, description, prompt and optional runtime, model, tools, mcp_servers, delegates, execution, memory, policies, input and output. Keep tools as the agent's explicit selection, including tools: [] when it uses none.
- execution_profiles: named max_steps values.
- models: provider, model_id and api_key_env.
- mcp_servers: stdio script and server-level allowed tool names. An agent receives only the intersection of its tools selection and these allowlists; a selected tool missing from the connected servers causes an error before model invocation.
- a2a_servers: agent name to port. A corresponding public URL may be set in the environment as NAME_IN_UPPERCASE_AGENT_PUBLIC_URL.

Defaults from AgentDefinition are runtime=smolagents, model=default, execution=default, memory=none and text input/output. role accepts manager or specialist, but the current runtime does not branch on role: delegates and runtime determine what the agent does. Invalid names, profiles and settings fail early in the loaders.

Supported combinations are currently smolagents + OpenAI + A2A delegates for the concierge, and LangChain + OpenAI or Hugging Face + MCP tools for specialists. The LangChain adapter does not accept delegates; the smolagents adapter does not accept MCP tools. Memory modes other than none, policy plugins and structured input/output are declared in the schema but rejected by AgentRuntime. New providers or frameworks require a tested change to agents/models.py or agents/runtime.py; YAML alone cannot create an unsupported adapter.

A delegate is named under its manager's delegates list. AgentRuntime reads that delegate's local definition for validation and tool description, but the actual invocation crosses A2A. This means a completely external agent without a local AgentDefinition is not yet supported by configuration alone. A2A ports live in YAML; changing only an old *_AGENT_PORT environment variable has no effect. A2A_BIND_HOST controls the listen address, whereas NAME_AGENT_PUBLIC_URL is the reachable URL announced on the Agent Card and used by clients.

## Request and state flow

1. The browser signs in using backend/auth.py and calls POST /api/chat with a message, conversation_id and request_id. The API requires a session cookie, CSRF token and ownership of the conversation.
2. backend/storage.py records a pending request in SQLite and supplies completed conversation turns. Reusing a completed request_id returns its stored response; failed turns remain retryable.
3. backend/api.py calls AgentRuntime.answer_query_with_metadata on the concierge. agents/conversation_memory.py keeps at most six complete user/assistant pairs and a 16,000-character serialized budget. The question and bounded context enter a fresh smolagents execution.
4. The concierge chooses one or more generated ask_* tools. tools/delegation.py calls a2a_clients/client_utils.py; the client reads the specialist's Agent Card and sends an A2A text request.
5. a2a_servers/executor.py runs the configured specialist in a worker thread and emits a text answer. The specialist discovers tools over MCP and the runtime exposes only names in its tools list. Policy uses search_policy over the shared PDF, research uses web_search through DDGS, and healthcare provider uses list_doctors over the local JSON directory.
6. The concierge synthesizes the specialist results. Metadata records names of tools actually called and the concierge run latency. The API validates, persists and returns the answer.

After the first successful answer, the API schedules a separate background call to the `models.title` profile (currently OpenAI gpt-4o-mini) using `prompts/title.md`. It sends only truncated copies of that first question and answer and stores a short topic title in SQLite. The chat answer is returned independently; the browser checks the conversation list briefly for the new title. A failed title call leaves the provisional first-question title in place. `PATCH /api/conversations/{id}` marks a manual title, and a conditional SQLite update ensures an in-flight generated title cannot overwrite it. To change the title model, edit `models.title`; to change the naming instructions, edit `prompts/title.md`.

The A2A server publishes /.well-known/agent-card.json and accepts JSON-RPC at /. Agent Cards use the configured agent description and endpoint. The implementation is request/response text only, with in-memory A2A task stores; it does not implement streaming, persistent remote tasks or effective cancellation. Conversation history stays in the backend and is not sent as a specialist conversation; the manager reformulates a standalone specialist question.

GET /api/health checks the three specialist Agent Card endpoints and reports their reachability. It does not prove that credentials, model inference, MCP tools, PDF access or answer quality work. The backend handles one active concierge query per process; a concurrent query gets 503. A2A client calls use a 120-second HTTPX timeout, while the browser has its own timeout; neither guarantees remote cancellation.

## Add a specialist

For a new internal agent, follow this order:

1. Write prompts/NAME.md with its domain, grounding rules and response expectations. Keep routing instructions in the manager prompt generic.
2. Add agents.NAME in config/agents.yaml with a clear description, prompt: NAME, runtime: langchain, a supported model, explicit tools list and mcp_servers references. Create or reuse an MCP server script and register its stdio connection and allowed_tools. Do not put prompt text or credentials in YAML. If tools is empty, the specialist receives no tools, even when its server exposes some.
3. Add a2a_servers.NAME.port with a free port, and add NAME to agents.concierge.delegates. Start python -m a2a_servers.serve NAME; no new A2A server Python module is needed. Set NAME_AGENT_PUBLIC_URL only when the client's reachable address differs from the local default.
4. Test definition loading, Agent Card creation, direct A2A communication and a concierge question that requires this agent. Check the server access log for a POST to /. Update the Compose services and model credentials if the agent must run in containers.

A compact example for a new MCP-backed specialist:

~~~yaml
agents:
  nutrition:
    role: specialist
    description: Answers nutrition questions from its approved sources.
    prompt: nutrition
    runtime: langchain
    tools: [search_nutrition]
    mcp_servers: [nutrition_sources]

  concierge:
    role: manager
    prompt: concierge
    description: Coordinates specialist agents.
    tools: []
    delegates: [policy, research, healthcare_provider, nutrition]

mcp_servers:
  nutrition_sources:
    transport: stdio
    script: mcp_servers/nutrition.py
    allowed_tools: [search_nutrition]

a2a_servers:
  nutrition:
    port: 9996
~~~

This is a fragment to merge into the existing file, not a replacement for its other sections. The MCP server must expose search_nutrition, and prompts/nutrition.md must exist. A different model/provider or framework needs an adapter supported by create_model and AgentRuntime first. For a third-party A2A agent, the client transport is reusable, but local definition/validation and endpoint configuration need extending before it becomes configuration-only.

## API, operations and limits

The backend serves the UI and HTTP API on the same origin. Key routes are POST /api/auth/register, POST /api/auth/login, POST /api/auth/logout, GET/POST /api/conversations, GET /api/conversations/{id}/messages, PATCH /api/conversations/{id} to rename, DELETE /api/conversations/{id}, POST /api/chat and GET /api/health. The browser exposes rename and delete in each history item's actions menu. Chat requests include message, conversation_id and request_id UUIDs. Responses include answer, agents_used, request_id, latency_ms and conversation_id. Invalid input is rejected; agent failures return a sanitized 502, timeouts 504, and unavailable/busy concierge requests 503.

SQLite holds users, sessions, conversations, requests and messages. Passwords use PBKDF2 hashes; session tokens are stored hashed and the API enforces CSRF, origin/ownership checks and rate limits. DATABASE_PATH defaults to data/concierge.sqlite3. The Compose backend uses a named volume. Preserve or back up that file before replacing a deployment. Session cookies should be marked secure when HTTPS is used.

The A2A services have no application-level authentication or authorization. Keep them on loopback locally or on a private container network; the HTTPS proxy exposes only the backend. The policy PDF and doctors.json are shared application data, not per-user records. The provider directory is a static sample and does not establish appointment availability, insurance network membership or clinical suitability. The application is an engineering reference, not a source of medical advice.

The frontend and Python tests use deterministic substitutes for many agent calls. Run:

~~~bash
uv run python -m pytest tests -q -p no:cacheprovider
node --test tests/frontend.test.cjs
~~~

The browser tests require Chrome and a matching Selenium driver; the JavaScript tests require Node.js. These checks do not score answer correctness, real model quality or remote interoperability under load. Live checks require working API credentials and network access. There is no distributed tracing, token/cost ledger, long-running task recovery or CI-based AI evaluation yet. Record new architectural decisions here and future experiments in the roadmap.
