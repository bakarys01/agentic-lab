# agents/concierge_agent.py

from smolagents import (
    OpenAIServerModel,
    ToolCallingAgent,
)

from tools.concierge_tools import (
    ask_policy,
    ask_research,
)


class ConciergeAgent:
    """
    Main healthcare concierge.

    Routes questions to specialized agents through A2A
    and synthesizes their responses.
    """

    def __init__(self) -> None:

        model = OpenAIServerModel(
            model_id="gpt-4o"
        )

        self.agent = ToolCallingAgent(
            model=model,
            tools=[
                ask_policy,
                ask_research,
            ],
            max_steps=8,
            verbosity_level=2,
        )

    def answer_query(
        self,
        query: str,
    ) -> str:

        task = f"""
You are a healthcare concierge agent.

You have access to two specialized agents.

1. ask_policy
   Use this agent for questions about the user's insurance policy:
   - coverage
   - copays
   - coinsurance
   - deductibles
   - benefits
   - exclusions
   - in-network vs out-of-network costs

2. ask_research
   Use this agent for general healthcare research:
   - medical conditions
   - symptoms
   - treatments
   - procedures
   - healthcare options

Your job is to determine which specialized agent is needed.

Rules:

- For insurance-specific questions, use ask_policy.
- For general medical or healthcare research, use ask_research.
- If the question contains both insurance and medical research
  aspects, call BOTH agents.
- Do not answer specialized questions from your own knowledge
  when one of the specialized agents should be used.
- Preserve important details from the specialist responses.
- Clearly distinguish insurance policy information from general
  healthcare information.
- Do not invent information that was not provided by the
  specialized agents.
- After collecting the required information, synthesize it into
  one clear response for the user.

User question:

{query}
"""

        response = self.agent.run(task)

        return str(response)