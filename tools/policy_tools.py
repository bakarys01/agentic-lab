
from pathlib import Path

import pymupdf
from smolagents import Tool, tool

POLICY_PATH = Path("data/2026AnthemgHIPSBC.pdf")


def _load_policy() -> list[dict]:
    """Load the policy once and preserve page numbers."""
    doc = pymupdf.open(POLICY_PATH)

    return [
        {
            "page": page_number,
            "text": page.get_text(),
        }
        for page_number, page in enumerate(doc, start=1)
    ]


POLICY_PAGES = _load_policy()


@tool
def search_policy(query: str) -> str:
    """
    Search the health insurance policy for passages relevant to a query.

    Args:
        query: What to search for in the insurance policy.
    """

    query_terms = set(query.lower().split())

    scored_pages = []

    for page in POLICY_PAGES:
        text = page["text"]
        text_lower = text.lower()

        score = sum(term in text_lower for term in query_terms)

        if score > 0:
            scored_pages.append(
                (score, page["page"], text)
            )

    scored_pages.sort(reverse=True)

    if not scored_pages:
        return "No relevant information found in the policy."

    results = []

    for _, page_number, text in scored_pages[:3]:
        results.append(
            f"""
SOURCE: Insurance Policy
PAGE: {page_number}

{text[:5000]}
"""
        )

    return "\n\n".join(results)