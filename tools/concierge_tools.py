# tools/concierge_tools.py

import asyncio

from smolagents import tool

from a2a_clients.client_utils import (
    ask_policy_agent,
    ask_research_agent,
)


def run_async(coro):
    """
    Run an async A2A call from a synchronous smolagents tool.
    """

    return asyncio.run(coro)


@tool
def ask_policy(question: str) -> str:
    """
    Ask the Insurance Policy Agent a question about the user's
    health insurance policy.

    Args:
        question: Question about insurance coverage, copays,
            coinsurance, deductibles, benefits, or exclusions.

    Returns:
        The response from the Policy Agent.
    """

    return run_async(
        ask_policy_agent(question)
    )


@tool
def ask_research(question: str) -> str:
    """
    Ask the Health Research Agent for healthcare information.

    Args:
        question: Question about medical conditions, symptoms,
            treatments, procedures, or healthcare options.

    Returns:
        The response from the Research Agent.
    """

    return run_async(
        ask_research_agent(question)
    )