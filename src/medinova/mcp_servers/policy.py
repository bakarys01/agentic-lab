"""Expose the shared insurance PDF through MCP."""

from functools import lru_cache

import pymupdf
from mcp.server.fastmcp import FastMCP

from medinova.paths import PROJECT_ROOT


mcp = FastMCP("policy_documents")
POLICY_PATH = PROJECT_ROOT / "data" / "2026AnthemgHIPSBC.pdf"


@lru_cache(maxsize=1)
def _policy_pages() -> tuple[tuple[int, str], ...]:
    with pymupdf.open(POLICY_PATH) as document:
        return tuple((number, page.get_text()) for number, page in enumerate(document, start=1))


@mcp.tool()
def search_policy(query: str) -> str:
    """Find relevant passages in the insurance policy, with their page numbers.

    Args:
        query: Insurance coverage question or search terms.
    """
    terms = set(query.casefold().split())
    if not terms or len(query) > 500:
        raise ValueError("Provide a policy query of 1 to 500 characters.")

    scored = []
    for page_number, text in _policy_pages():
        lowered = text.casefold()
        score = sum(term in lowered for term in terms)
        if score:
            scored.append((score, page_number, text))

    scored.sort(reverse=True)
    if not scored:
        return "No relevant information found in the policy."

    return "\n\n".join(
        f"SOURCE: Insurance Policy\nPAGE: {page_number}\n\n{text[:5000]}"
        for _, page_number, text in scored[:3]
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
