# tools/concierge_tools.py

import asyncio
from contextvars import ContextVar

from smolagents import tool

from a2a_clients.client_utils import (
    ask_policy_agent,
    ask_research_agent,
)

_AGENT_USAGE: ContextVar[set[str] | None] = ContextVar(
    "agent_usage",
    default=None,
)


def record_agent_usage(agent_name: str) -> None:
    """Track which specialist agents were used during a single concierge run."""
    usage = _AGENT_USAGE.get() or set()
    _AGENT_USAGE.set(usage | {agent_name})


def clear_agent_usage() -> None:
    """Reset the usage tracking before starting a new query."""
    _AGENT_USAGE.set(set())


def get_agent_usage() -> list[str]:
    """Return the ordered set of specialists invoked for the current request."""
    usage = _AGENT_USAGE.get() or set()
    return [
        agent
        for agent in ("policy", "research")
        if agent in usage
    ]


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

    record_agent_usage("policy")
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

    record_agent_usage("research")
    return run_async(
        ask_research_agent(question)
    )
