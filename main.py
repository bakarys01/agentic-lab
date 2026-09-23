from agents.policy_agent import PolicyAgent


agent = PolicyAgent()

response = agent.answer_query(
    "How much would I pay for mental health therapy?"
)

print(response)