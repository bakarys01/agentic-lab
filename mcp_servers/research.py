"""Expose source-attributed web search through MCP."""

from ddgs import DDGS
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("research_web")


@mcp.tool()
def web_search(query: str) -> str:
    """Search the web and return result titles, URLs and excerpts.

    Args:
        query: Healthcare research question or search terms.
    """
    query = query.strip()
    if not query or len(query) > 500:
        raise ValueError("Provide a web search query of 1 to 500 characters.")

    with DDGS() as search:
        results = search.text(query, max_results=10)

    if not results:
        return "No web search results found."

    return "## Search results\n\n" + "\n\n".join(
        f"[{item.get('title', 'Untitled')[:200]}]({item.get('href', '')[:1000]})\n"
        f"{item.get('body', '')[:1000]}"
        for item in results[:10]
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
