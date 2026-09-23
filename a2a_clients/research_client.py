# a2a_clients/research_client.py

import asyncio

import httpx

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_message_text, new_text_message
from a2a.types import (
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
)


# ============================================================
# CONFIGURATION
# ============================================================

RESEARCH_AGENT_URL = "http://127.0.0.1:9998"


async def main() -> None:

    print("=" * 60)
    print("Health Research Agent - A2A Client")
    print("=" * 60)

    print(f"\nConnecting to: {RESEARCH_AGENT_URL}")

    # ========================================================
    # 1. CREATE HTTP CLIENT
    # ========================================================
    #
    # The Research Agent can take longer than the Policy Agent
    # because it performs:
    #
    #   LLM -> Web Search -> LLM -> Response
    #
    # Therefore we increase the HTTP timeout.

    httpx_client = httpx.AsyncClient(
        timeout=httpx.Timeout(120.0)
    )

    # ========================================================
    # 2. CONFIGURE A2A CLIENT
    # ========================================================

    client_config = ClientConfig(
        httpx_client=httpx_client
    )

    # ========================================================
    # 3. CONNECT TO THE RESEARCH AGENT
    # ========================================================

    client = await create_client(
        RESEARCH_AGENT_URL,
        client_config=client_config,
    )

    # ========================================================
    # 4. CREATE USER QUESTION
    # ========================================================

    question = (
        "What are the common treatments for sleep apnea?"
    )

    message = new_text_message(
        question,
        role=Role.ROLE_USER,
    )

    # ========================================================
    # 5. CREATE A2A REQUEST
    # ========================================================

    request = SendMessageRequest(
        message=message,
        configuration=SendMessageConfiguration(
            return_immediately=False,
        ),
    )

    print(f"\nQuestion: {question}")
    print("\nSending message through A2A...\n")

    # ========================================================
    # 6. SEND MESSAGE
    # ========================================================

    try:

        async for response in client.send_message(request):

            # ------------------------------------------------
            # Direct message
            # ------------------------------------------------

            if response.HasField("message"):

                answer = get_message_text(
                    response.message
                )

                print("=" * 60)
                print("Research Agent response")
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
            # Status update
            # ------------------------------------------------

            elif response.HasField("status_update"):

                print("=" * 60)
                print("Status update")
                print("=" * 60)

                print(response.status_update)

            # ------------------------------------------------
            # Artifact update
            # ------------------------------------------------

            elif response.HasField("artifact_update"):

                print("=" * 60)
                print("Artifact update")
                print("=" * 60)

                print(response.artifact_update)

    # ========================================================
    # 7. CLEANUP
    # ========================================================

    finally:

        await client.close()
        await httpx_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())