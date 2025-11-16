# state.py
from typing import List, TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    tool_calls: List[dict]  # AI tool calls extracted after LLM node

