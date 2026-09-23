# main.py

from agents.concierge_agent import ConciergeAgent


def main() -> None:

    print("=" * 60)
    print("Healthcare Concierge")
    print("=" * 60)

    concierge = ConciergeAgent()

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

            response = concierge.answer_query(
                question
            )

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