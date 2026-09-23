import asyncio

from a2a_clients.client_utils import ask_policy_agent


async def main() -> None:

    question = (
        "How much would I pay for mental health therapy?"
    )

    print("=" * 60)
    print("Policy Agent - A2A Client")
    print("=" * 60)

    print(f"\nQuestion: {question}")
    print("\nSending message through A2A...\n")

    response = await ask_policy_agent(
        question
    )

    print("=" * 60)
    print("Policy Agent response")
    print("=" * 60)

    print(response)


if __name__ == "__main__":
    asyncio.run(main())