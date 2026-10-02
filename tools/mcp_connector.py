import sys

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StdioConnection

from agents.config_loader import load_mcp_config


async def load_mcp_tools(server_name: str) -> list[BaseTool]:
    settings = load_mcp_config(server_name)

    client = MultiServerMCPClient(
        {
            server_name: StdioConnection(
                transport="stdio",
                command=sys.executable,
                args=[settings["script"]],
            )
        }
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