from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from medinova.agents.config_loader import load_agent_definition


def create_agent_card(agent_name: str, public_url: str) -> AgentCard:
    definition = load_agent_definition(agent_name)

    skill = AgentSkill(
        id=definition.name,
        name=definition.name.replace("_", " ").title(),
        description=definition.description,
        tags=[definition.name],
    )

    return AgentCard(
        name=definition.name.replace("_", " ").title(),
        description=definition.description,
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[skill],
        supported_interfaces=[
            AgentInterface(
                url=public_url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
    )