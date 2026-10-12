# main.py

from medinova.agents.config_loader import load_agent_definition
from medinova.agents.runtime import AgentRuntime

def main() -> None:

    print("=" * 60)
    print("Healthcare Concierge")
    print("=" * 60)

    concierge = AgentRuntime(load_agent_definition("concierge"))

    while True:

        question = input(
            "\nYou: "
        ).strip()

        if question.lower() in {
            "exit",
            "quit",
            "q",
        }:
            print("\nGoodbye!")
            break

        if not question:
            continue

        print("\nThinking...\n")

        try:

            response = concierge.run(question)

            print("\n" + "=" * 60)
            print("Healthcare Concierge")
            print("=" * 60)

            print(response)

        except Exception as exc:

            print(
                f"\nError: {exc}"
            )


if __name__ == "__main__":
    main()
