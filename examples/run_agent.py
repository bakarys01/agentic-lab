import argparse

from agents.config_loader import load_agent_definition
from agents.runtime import AgentRuntime


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an agent defined in config/agents.yaml."
    )
    parser.add_argument("agent", help="Agent name from the configuration")
    parser.add_argument("question", help="Question to ask")
    args = parser.parse_args()

    definition = load_agent_definition(args.agent)
    agent = AgentRuntime(definition)

    print(agent.run(args.question))


if __name__ == "__main__":
    main()