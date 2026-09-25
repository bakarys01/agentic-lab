# Architecture

## Overview

The project implements a healthcare concierge built around a small multi-agent pattern:

- a concierge agent orchestrates the conversation
- a policy specialist handles insurance questions
- a research specialist handles general healthcare questions
- each specialist runs as an A2A-compatible service
- the front end calls a lightweight Python API layer

This keeps the user experience simple while preserving the agent boundaries that matter for correctness and trust.

## Request flow

1. The user enters a question in the static HTML/JavaScript front end.
2. The front end sends the message to the Python API at `/api/chat`.
3. The API invokes `answer_query_with_metadata()` on the concierge agent.
4. The concierge agent runs a `ToolCallingAgent` with `ask_policy` and `ask_research` tools.
5. Each tool sends a request to one of the specialist A2A services.
6. The specialist returns domain-specific information.
7. The concierge synthesizes the final answer and returns it to the API.
8. The API sends the structured response back to the browser.

## Agent boundaries

### Concierge agent

The concierge is responsible for:

- deciding whether the question is policy-focused, research-focused, or mixed
- invoking the correct specialist tool(s)
- combining specialist output into a single response
- returning metadata like which specialist agents were used

It does not perform the policy lookup or web research itself. It delegates those tasks to specialty services.

### Policy agent

The policy agent answers questions about:

- coverage and benefits
- deductibles and copays
- coinsurance
- exclusions and limitations
- in-network and out-of-network differences

It uses the local PDF-based retrieval tool attached to the policy service.

### Research agent

The research agent answers questions about:

- symptoms and disease descriptions
- treatment options
- medical procedures
- general healthcare context

It uses search-oriented tools and responds with internet-derived context.

## A2A communication

The specialist services expose agent cards and callable endpoints. The concierge calls them through the A2A client utilities in `a2a_clients/`.

The relevant layers are:

- `a2a_servers/policy_server.py`
- `a2a_servers/research_server.py`
- `a2a_clients/client_utils.py`
- `tools/concierge_tools.py`

This allows the orchestration layer to remain loosely coupled from the specialist implementation.

## Health model

The API health endpoint checks the status of each service through the `get_health()` method on the concierge. That method probes:

- whether the concierge can be initialized locally (no model inference call)
- the policy agent card URL
- the research agent card URL

The frontend shows a compact indicator: green when all services are available, amber when specialists are unavailable or service is degraded, red when the concierge cannot be reached or initialized. Hover text provides details; clicking reruns the check. It does not verify model credentials, quota, or outbound inference connectivity.

## Data flow and contracts

The API contract is intentionally small:

- POST `/api/chat`
  - body: `{ "message": "...", "conversation_id": "UUID", "request_id": "UUID" }` (authenticated session and CSRF header required)
  - response: `{ "answer": "...", "agents_used": ["..."], "request_id": "...", "latency_ms": 123, "conversation_id": "..." }`
- GET `/api/health`
  - response: status summary for the concierge, policy service, and research service

This gives the browser a stable API surface while hiding the A2A and tool-layer complexity.

## Execution and browser state

The backend creates the real concierge lazily after loading `.env`. Chat and health handlers run in FastAPI worker threads, allowing synchronous smolagents tools to call `asyncio.run()` for A2A work. A nonblocking lock permits one active concierge query per API process; concurrent queries receive 503 instead of waiting indefinitely. Tool usage metadata comes from completed agent memory, including parallel specialist calls.

The browser sends the current question, conversation ID and stable request ID. The backend identifies the owner from a server-side session, loads authorized completed turns from SQLite and supplies bounded context. Agent memory is reset for every run. The browser reloads persisted messages and renders content using `textContent`. See [accounts and memory](accounts-and-memory.md) for the schema, endpoints and lifecycle.

The backend serves the frontend on the same origin. Static HTML/CSS/JavaScript responses use `Cache-Control: no-store`, including conditional requests. Versioned asset URLs prevent clients with older cached assets from mixing frontend versions.

### Chat validation and errors

Messages must contain non-whitespace text and may contain at most 8,000 characters. Empty/invalid input returns 400 or 422. Response payloads are validated before returning them to the browser.

| Status | Meaning |
| --- | --- |
| 502 | Agent execution failed or returned an invalid/empty response |
| 503 | Concierge initialization unavailable, or another query is running |
| 504 | A `TimeoutError` reached the API from specialist execution |

The browser aborts its request after three minutes. This does not cancel work already executing in the server. Local account authentication and SQLite persistence are implemented. Streaming and public deployment hardening are not implemented. Only a single backend worker is supported.

## Why this design works

The project deliberately separates:

- reasoning (`smolagents` inside each agent)
- inter-agent communication (`A2A`)
- tool execution (PDF retrieval and web search)

That separation means the app can evolve without collapsing the specialist boundaries into one monolithic agent.
