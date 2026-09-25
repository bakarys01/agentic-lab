from smolagents import ToolCallingAgent, OpenAIServerModel

from tools.policy_tools import search_policy


class PolicyAgent:
    """
    Agent responsible for answering questions
    about the health insurance policy.
    """

    def __init__(self) -> None:

        model = OpenAIServerModel(
            model_id="gpt-4o"
        )

        self.agent = ToolCallingAgent(
            model=model,
            tools=[search_policy],
            max_steps=6,
            verbosity_level=0,
        )

    def answer_query(self, query: str) -> str:

        task = f"""
You are a health insurance policy assistant.

Use the search_policy tool to find relevant information
inside the insurance policy.

Rules:
- Base your answer only on information returned by search_policy.
- Do not invent policy information.
- Mention the page number when available.
- If the information cannot be found, say that you don't know.

User question:
{query}
"""

        response = self.agent.run(task)

        return str(response)