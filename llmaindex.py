from agents.policy_agent import policy_agent


question = """
How much would I pay for mental health therapy?
"""

answer = policy_agent.run(question)

print(answer)