from graph import build_graph
from langchain_core.messages import HumanMessage, SystemMessage
from prompts import SYSTEM_PROMPT

agent = build_graph()

print("\nAgent Ready. Type your question:\n")

conversation_history = [SystemMessage(content=SYSTEM_PROMPT)]
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        break
    conversation_history.append(HumanMessage(content=user_input))
    result = agent.invoke({"messages": conversation_history})
    final_msg = result["messages"][-1]
    if hasattr(final_msg, 'content') and final_msg.content:
        print("\nAgent:", final_msg.content, "\n")
    else:
        print("\nAgent:", final_msg, "\n")
