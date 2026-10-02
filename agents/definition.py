from dataclasses import dataclass
from typing import Literal


AgentRole = Literal["manager", "specialist"]


@dataclass(frozen=True)
class AgentDefinition:
    """Describe a local agent independently of its runtime implementation."""

    # Identity
    name: str
    role: AgentRole
    description: str

    # Prompt name passed to load_prompt(), e.g. "policy"
    prompt: str

    # Runtime adapter and model configuration reference
    runtime: str = "smolagents"
    model: str = "default"

    # References to registered capabilities
    tools: tuple[str, ...] = ()
    mcp_servers: tuple[str, ...] = ()
    delegates: tuple[str, ...] = ()

    # References to behavior configurations
    memory: str = "none"
    execution: str = "default"
    policies: tuple[str, ...] = ()

    # References to input and output contracts
    input: str = "text"
    output: str = "text"