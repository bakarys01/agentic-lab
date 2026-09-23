import asyncio

from a2a_clients.client_utils import ask_research_agent


async def main() -> None:

    question = (
        "What are the common treatments for sleep apnea?"
    )

    print("=" * 60)
    print("Health Research Agent - A2A Client")
    print("=" * 60)

    print(f"\nQuestion: {question}")
    print("\nSending message through A2A...\n")

    response = await ask_research_agent(
        question
    )

    print("=" * 60)
    print("Research Agent response")
    print("=" * 60)

    print(response)


if __name__ == "__main__":
    asyncio.run(main())