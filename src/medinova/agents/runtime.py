"""Build and run agents from their configured definitions."""

import asyncio
import json
import threading
from functools import partial
from time import perf_counter
from typing import Any

import httpx
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from smolagents import ToolCallingAgent

from medinova.a2a_clients.client_utils import get_agent_url
from medinova.agents.config_loader import load_agent_definition, load_execution_profile
from medinova.agents.conversation_memory import recent_history
from medinova.agents.definition import AgentDefinition
from medinova.agents.models import create_model
from medinova.prompts.loader import load_prompt
from medinova.tools.delegation import AgentTool, invoke_a2a_agent
from medinova.tools.mcp_connector import load_mcp_tools


class AgentRuntime:
    def __init__(
        self,
        definition: AgentDefinition,
        ancestry: tuple[str, ...] = (),
    ) -> None:
        if definition.name in ancestry:
            chain = " -> ".join((*ancestry, definition.name))
            raise ValueError(f"Circular delegation: {chain}")

        self._validate_supported_features(definition)
        self.definition = definition
        self.instructions = load_prompt(definition.prompt)
        self.max_steps = load_execution_profile(definition.execution)
        self._langchain_runner = (
            asyncio.Runner() if definition.runtime == "langchain" else None
        )
        self._langchain_lock = threading.Lock()

        path = (*ancestry, definition.name)
        self.delegates = tuple(
            AgentRuntime(load_agent_definition(name), ancestry=path)
            for name in definition.delegates
        )

    @staticmethod
    def _validate_supported_features(definition: AgentDefinition) -> None:
        if definition.runtime not in {"smolagents", "langchain"}:
            raise ValueError(f"Unknown runtime: {definition.runtime}")

        if (
            definition.memory != "none"
            or definition.policies
            or definition.input != "text"
            or definition.output != "text"
        ):
            raise NotImplementedError(
                "Memory, policies and structured input/output are not supported yet."
            )

        if definition.runtime == "smolagents" and (
            definition.mcp_servers or definition.tools
        ):
            raise NotImplementedError(
                "MCP tools currently require the LangChain runtime."
            )

        if definition.runtime == "langchain" and definition.delegates:
            raise NotImplementedError(
                "The LangChain adapter does not support delegates."
            )

        if (
            definition.runtime == "langchain"
            and definition.tools
            and not definition.mcp_servers
        ):
            raise ValueError("Selected tools require an MCP server.")

    @staticmethod
    def _validate_question(question: str) -> None:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must be a non-empty string.")

    def run(
        self,
        question: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        self._validate_question(question)

        if self.definition.runtime == "langchain":
            if history:
                raise NotImplementedError(
                    "Conversation history is not supported by the LangChain adapter."
                )
            with self._langchain_lock:
                return self._langchain_runner.run(self._run_langchain(question))

        _, answer = self._execute_smolagents(question, history)
        return answer

    def answer_query_with_metadata(
        self,
        question: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._validate_question(question)
        if self.definition.runtime != "smolagents":
            raise NotImplementedError(
                "Metadata is not yet supported for this runtime."
            )

        started = perf_counter()
        agent, answer = self._execute_smolagents(question, history)
        called_tools = {
            call.name
            for step in agent.memory.steps
            for call in (getattr(step, "tool_calls", None) or [])
        }

        return {
            "answer": answer,
            "agents_used": [
                delegate.definition.name
                for delegate in self.delegates
                if f"ask_{delegate.definition.name}" in called_tools
            ],
            "latency_ms": int((perf_counter() - started) * 1000),
        }

    def _execute_smolagents(
        self,
        question: str,
        history: list[dict[str, Any]] | None,
    ) -> tuple[ToolCallingAgent, str]:
        tools = [
            AgentTool(
                agent_name=delegate.definition.name,
                description=delegate.definition.description,
                invoke=partial(invoke_a2a_agent, delegate.definition.name),
            )
            for delegate in self.delegates
        ]
        agent = ToolCallingAgent(
            model=create_model(
                name=self.definition.model,
                runtime=self.definition.runtime,
            ),
            tools=tools,
            max_steps=self.max_steps,
            verbosity_level=0,
        )

        context = (
            "\n\nRecent conversation (JSON):\n"
            + json.dumps(recent_history(history), ensure_ascii=False)
            if history
            else ""
        )
        task = f"{self.instructions}{context}\n\nUser question:\n{question}"
        return agent, str(agent.run(task))

    async def _run_langchain(self, question: str) -> str:
        tool_groups = []
        if self.definition.tools:
            tool_groups = [
                await load_mcp_tools(server_name)
                for server_name in self.definition.mcp_servers
            ]
        selected = set(self.definition.tools)
        tools = [
            tool for group in tool_groups for tool in group
            if tool.name in selected
        ]

        names = [tool.name for tool in tools]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate tool names across MCP servers.")
        missing = selected - set(names)
        if missing:
            raise ValueError(f"Selected MCP tools not found: {sorted(missing)}")

        agent = create_agent(
            model=create_model(
                name=self.definition.model,
                runtime=self.definition.runtime,
            ),
            tools=tools,
            name=self.definition.name,
            system_prompt=self.instructions,
            middleware=[
                ModelCallLimitMiddleware(
                    run_limit=self.max_steps,
                    exit_behavior="error",
                )
            ],
        )

        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        content = response["messages"][-1].content
        if isinstance(content, str):
            return content

        return "\n".join(
            block if isinstance(block, str) else block["text"]
            for block in content
            if isinstance(block, str)
            or (
                isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            )
        )

    def get_health(self) -> dict[str, Any]:
        services = {self.definition.name: {"status": "available"}}

        for delegate in self.delegates:
            name = delegate.definition.name
            try:
                url = f"{get_agent_url(name)}/.well-known/agent-card.json"
                response = httpx.get(url, timeout=3.0)
                status = "available" if response.status_code == 200 else "unavailable"
            except (httpx.HTTPError, ValueError):
                status = "unavailable"

            services[name] = {"status": status}

        return {
            "status": (
                "ok"
                if all(item["status"] == "available"
                    for item in services.values())
                else "degraded"
            ),
            "services": services,
        }
