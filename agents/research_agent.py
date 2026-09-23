from smolagents import (
    DuckDuckGoSearchTool,
    OpenAIServerModel,
    ToolCallingAgent,
)


class ResearchAgent:
    """
    Agent responsible for researching healthcare information
    using up-to-date web search results.
    """

    def __init__(self) -> None:

        model = OpenAIServerModel(
            model_id="gpt-4o"
        )

        self.agent = ToolCallingAgent(
            model=model,
            tools=[
                DuckDuckGoSearchTool()
            ],
            max_steps=8,
            verbosity_level=2,
        )

    def answer_query(self, query: str) -> str:

        task = f"""
You are a healthcare research agent.

Your job is to research health conditions, symptoms,
treatments, procedures, and healthcare options using
up-to-date web information.

Use the web search tool whenever external healthcare
information is required.

Rules:
- Search the web before answering healthcare research questions.
- Prefer reliable medical and public-health sources.
- Clearly distinguish general information from medical advice.
- Do not invent medical facts.
- Include the sources/URLs returned by the search tool when possible.
- If reliable information cannot be found, say so.

User question:
{query}
"""

        response = self.agent.run(task)

        return str(response)