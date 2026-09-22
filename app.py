from dotenv import load_dotenv

# --------------------------------------------------
# 1. Load environment variables FIRST
# --------------------------------------------------
load_dotenv()


# --------------------------------------------------
# 2. Initialize Langfuse
# --------------------------------------------------
from langfuse import get_client

langfuse = get_client()

if langfuse.auth_check():
    print("✅ Langfuse connected")
else:
    print("❌ Langfuse authentication failed")


# --------------------------------------------------
# 3. Instrument smolagents
# --------------------------------------------------
from openinference.instrumentation.smolagents import SmolagentsInstrumentor

SmolagentsInstrumentor().instrument()


# --------------------------------------------------
# 4. Now import/use smolagents
# --------------------------------------------------
from smolagents import (
    CodeAgent,
    InferenceClientModel,
    DuckDuckGoSearchTool,
    VisitWebpageTool,
    FinalAnswerTool,
)

from tools.my_tools import (
    suggest_menu,
    catering_service_tool,
    SuperheroPartyThemeTool,
)


model = InferenceClientModel(
    model_id="openai/gpt-oss-120b"
)


agent = CodeAgent(
    tools=[
        DuckDuckGoSearchTool(),
        VisitWebpageTool(),
        suggest_menu,
        catering_service_tool,
        SuperheroPartyThemeTool(),
        FinalAnswerTool(),
    ],
    model=model,
    max_steps=10,
    verbosity_level=2,
)
'''
# 
agent.push_to_hub(
    "bsidibe/BakyAgent",
    private=False,
)
'''

with langfuse.start_as_current_observation(
    as_type="span",
    name="wayne-villain-party-agent",
):
    result = agent.run(
        "Give me the best playlist for a party at Wayne's mansion. "
        "The party idea is a 'villain masquerade' theme."
    )

print("*************************************************")
print(result)
print("*************************************************")


# Important for short-lived scripts
langfuse.flush()