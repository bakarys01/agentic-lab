import sys
import os

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StdioConnection
from mcp.client.stdio import get_default_environment

from medinova.agents.config_loader import load_mcp_config
from medinova.agents.trace_context import current_trace_parent


def _stdio_environment(required: tuple[str, ...]) -> dict[str, str]:
    environment = get_default_environment()
    environment.update({name: os.environ[name] for name in required})
    for name in (
        "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "no_proxy",
        "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
    ):
        if os.getenv(name):
            environment[name] = os.environ[name]
    parent = current_trace_parent.get()
    if parent and os.getenv("LANGFUSE_ENABLED", "false").lower() == "true":
        environment.update({
            "MEDINOVA_TRACE_ID": parent["trace_id"],
            "MEDINOVA_PARENT_SPAN_ID": parent["parent_span_id"],
        })
        for name in (
            "LANGFUSE_ENABLED", "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
        ):
            if os.getenv(name):
                environment[name] = os.environ[name]
    return environment


async def load_mcp_tools(server_name: str) -> list[BaseTool]:
    settings = load_mcp_config(server_name)

    connection = StdioConnection(
        transport="stdio",
        command=sys.executable,
        args=[settings["script"]],
    )
    missing = [name for name in settings["env_vars"] if not os.getenv(name)]
    if missing:
        raise ValueError(f"Missing MCP environment variables: {missing}")
    if settings["env_vars"] or current_trace_parent.get():
        connection["env"] = _stdio_environment(settings["env_vars"])

    client = MultiServerMCPClient(
        {server_name: connection}
    )

    discovered = await client.get_tools(server_name=server_name)

    available = {tool.name for tool in discovered}
    allowed = set(settings["allowed_tools"])

    missing = allowed - available
    if missing:
        raise ValueError(
            f"Tools missing from MCP server {server_name}: "
            f"{sorted(missing)}"
        )

    return [
        tool
        for tool in discovered
        if tool.name in allowed
    ]
