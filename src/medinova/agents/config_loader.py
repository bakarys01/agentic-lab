from dataclasses import fields
from pathlib import Path
import re

import yaml

from medinova.agents.definition import AgentDefinition
from medinova.paths import PROJECT_ROOT


CONFIG_PATH = PROJECT_ROOT / "config" / "agents.yaml"

TUPLE_FIELDS = {"tools", "mcp_servers", "delegates", "policies"}


def load_agent_definition(name: str) -> AgentDefinition:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict) or config.get("version") != 1:
        raise ValueError("Expected an agent configuration with version: 1.")

    agents = config.get("agents")
    if not isinstance(agents, dict) or name not in agents:
        raise ValueError(f"Agent not found in configuration: {name}")

    settings = agents[name]
    if not isinstance(settings, dict):
        raise ValueError(f"Configuration for {name} must be a mapping.")

    allowed = {field.name for field in fields(AgentDefinition)} - {"name"}
    unknown = set(settings) - allowed
    if unknown:
        raise ValueError(f"Unknown fields for {name}: {sorted(unknown)}")

    for key, value in settings.items():
        if key in TUPLE_FIELDS:
            if not isinstance(value, list) or not all(
                isinstance(item, str) and item.strip()
                for item in value
            ):
                raise ValueError(f"{key} must be a list of non-empty strings.")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string.")

    for required in ("role", "description", "prompt"):
        if required not in settings:
            raise ValueError(f"Missing field for {name}: {required}")

    if settings["role"] not in {"manager", "specialist"}:
        raise ValueError(f"Invalid role for {name}: {settings['role']}")

    normalized = {
        key: tuple(value) if key in TUPLE_FIELDS else value
        for key, value in settings.items()
    }

    return AgentDefinition(name=name, **normalized)

def load_execution_profile(name: str) -> int:
    """Retourne le nombre maximal d'étapes du profil."""
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict) or config.get("version") != 1:
        raise ValueError("Expected configuration with version: 1.")

    profiles = config.get("execution_profiles")
    if not isinstance(profiles, dict) or name not in profiles:
        raise ValueError(f"Unknown execution profile: {name}")

    profile = profiles[name]
    if not isinstance(profile, dict):
        raise ValueError(f"Execution profile {name} must be a mapping.")

    if set(profile) != {"max_steps"}:
        raise ValueError(
            f"Execution profile {name} must contain only max_steps."
        )

    max_steps = profile["max_steps"]
    if type(max_steps) is not int or max_steps < 1:
        raise ValueError("max_steps must be a positive integer.")

    return max_steps

def load_model_config(name: str) -> dict[str, str]:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict) or config.get("version") != 1:
        raise ValueError("Expected configuration with version: 1.")

    models = config.get("models")
    if not isinstance(models, dict) or name not in models:
        raise ValueError(f"Unknown model configuration: {name}")

    settings = models[name]
    required = {"provider", "model_id", "api_key_env"}

    if not isinstance(settings, dict) or set(settings) != required:
        raise ValueError(
            f"Model {name} must define provider, model_id and api_key_env."
        )

    if not all(
        isinstance(value, str) and value.strip()
        for value in settings.values()
    ):
        raise ValueError("Model settings must be non-empty strings.")

    return dict(settings)

def load_mcp_config(name: str) -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict) or config.get("version") != 1:
        raise ValueError("Expected configuration with version: 1.")

    servers = config.get("mcp_servers")
    if not isinstance(servers, dict) or name not in servers:
        raise ValueError(f"Unknown MCP server: {name}")

    settings = servers[name]
    required = {"transport", "script", "allowed_tools"}

    if (
        not isinstance(settings, dict)
        or not required <= set(settings)
        or set(settings) - required - {"env_vars"}
    ):
        raise ValueError(
            f"MCP server {name} must define "
            "transport, script and allowed_tools."
        )

    if settings["transport"] != "stdio":
        raise ValueError("Only stdio MCP connections are supported for now.")

    script = settings["script"]
    if not isinstance(script, str) or not script.strip():
        raise ValueError("MCP script must be a non-empty string.")

    project_root = CONFIG_PATH.parent.parent.resolve()
    script_path = (project_root / script).resolve()

    if not script_path.is_relative_to(project_root):
        raise ValueError("MCP script must be inside the project.")

    if not script_path.is_file():
        raise ValueError(f"MCP script not found: {script_path}")

    allowed = settings["allowed_tools"]
    if not isinstance(allowed, list) or not allowed or not all(
        isinstance(tool, str) and tool.strip()
        for tool in allowed
    ):
        raise ValueError("allowed_tools must be a non-empty list of names.")

    env_vars = settings.get("env_vars", [])
    if not isinstance(env_vars, list) or any(
        not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name)
        for name in env_vars
    ) or len(env_vars) != len(set(env_vars)):
        raise ValueError("env_vars must be a list of unique environment variable names.")

    return {
        "transport": "stdio",
        "script": str(script_path),
        "allowed_tools": tuple(allowed),
        "env_vars": tuple(env_vars),
    }

def load_a2a_config(name: str) -> dict[str, int]:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    servers = config.get("a2a_servers")
    if not isinstance(servers, dict) or name not in servers:
        raise ValueError(f"Unknown A2A server: {name}")

    settings = servers[name]
    if not isinstance(settings, dict) or set(settings) != {"port"}:
        raise ValueError(f"A2A server {name} must define only port.")

    port = settings["port"]
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError(f"Invalid A2A port for {name}: {port}")

    return {"port": port}
