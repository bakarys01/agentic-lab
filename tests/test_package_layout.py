"""The installed package must resolve repository resources after migration."""

from pathlib import Path

from medinova.agents.config_loader import load_agent_definition, load_mcp_config
from medinova.paths import PROJECT_ROOT
from medinova.prompts.loader import load_prompt


def test_package_loads_external_config_and_packaged_prompt():
    definition = load_agent_definition("medication")

    assert definition.prompt == "medication"
    assert "get_medication" in load_prompt(definition.prompt)
    assert PROJECT_ROOT.joinpath("config", "agents.yaml").is_file()
    script = Path(load_mcp_config("medication_catalog")["script"])
    assert script == PROJECT_ROOT / "src" / "medinova" / "mcp_servers" / "medication.py"
