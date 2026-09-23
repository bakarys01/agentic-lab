from agents.policy_agent import PolicyAgent
from agents.research_agent import ResearchAgent


# ======================policy Agent======================================
'''
agent = PolicyAgent()

response = agent.answer_query(
    "How much would I pay for mental health therapy?"
)

print(response)

'''

# ======================Research Agent======================================

agent = ResearchAgent()

response = agent.answer_query(
    "What are the common treatments for sleep apnea?"
)

print(response)