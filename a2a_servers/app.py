from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from starlette.applications import Starlette

from agents.config_loader import load_a2a_config
from a2a_servers.card import create_agent_card
from a2a_servers.executor import RuntimeAgentExecutor


def create_a2a_app(agent_name: str, public_url: str | None = None) -> Starlette:
    port = load_a2a_config(agent_name)["port"]
    url = public_url or f"http://127.0.0.1:{port}"

    card = create_agent_card(agent_name, url)
    handler = DefaultRequestHandler(
        agent_executor=RuntimeAgentExecutor(agent_name),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )

    routes = [
        *create_agent_card_routes(card),
        *create_jsonrpc_routes(handler, rpc_url="/"),
    ]
    return Starlette(routes=routes)