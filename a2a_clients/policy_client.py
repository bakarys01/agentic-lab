# a2a_clients/policy_client.py

import asyncio

from a2a.client import create_client
from a2a.helpers import get_message_text, new_text_message
from a2a.types import (
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
)


POLICY_AGENT_URL = "http://127.0.0.1:9999"


async def main() -> None:

    print("=" * 60)
    print("Policy Agent - A2A Client")
    print("=" * 60)

    # ========================================================
    # 1. CONNECT TO THE A2A AGENT
    # ========================================================

    print(f"\nConnecting to: {POLICY_AGENT_URL}")

    client = await create_client(
        POLICY_AGENT_URL
    )

    # ========================================================
    # 2. CREATE USER MESSAGE
    # ========================================================

    question = (
        "How much would I pay for mental health therapy?"
    )

    message = new_text_message(
        question,
        role=Role.ROLE_USER,
    )

    # ========================================================
    # 3. CREATE THE A2A REQUEST
    # ========================================================

    request = SendMessageRequest(
        message=message,

        configuration=SendMessageConfiguration(
            # Wait for the agent to finish before returning.
            return_immediately=False,
        ),
    )

    print(f"\nQuestion: {question}")
    print("\nSending message through A2A...\n")

    # ========================================================
    # 4. SEND REQUEST
    # ========================================================

    try:

        async for response in client.send_message(request):

            # ------------------------------------------------
            # Direct Message
            # ------------------------------------------------

            if response.HasField("message"):

                answer = get_message_text(
                    response.message
                )

                print("=" * 60)
                print("Agent response")
                print("=" * 60)

                print(answer)

            # ------------------------------------------------
            # Task
            # ------------------------------------------------

            elif response.HasField("task"):

                print("=" * 60)
                print("Task received")
                print("=" * 60)

                print(response.task)

            # ------------------------------------------------
            # Status Update
            # ------------------------------------------------

            elif response.HasField("status_update"):

                print("=" * 60)
                print("Status update")
                print("=" * 60)

                print(response.status_update)

            # ------------------------------------------------
            # Artifact Update
            # ------------------------------------------------

            elif response.HasField("artifact_update"):

                print("=" * 60)
                print("Artifact update")
                print("=" * 60)

                print(response.artifact_update)

    finally:

        await client.close()


if __name__ == "__main__":
    asyncio.run(main())