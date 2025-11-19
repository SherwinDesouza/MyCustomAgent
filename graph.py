# graph.py
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from tools import TOOLS
from state import AgentState
from dotenv import load_dotenv
import os
import json
load_dotenv()

llm = ChatGroq(
    model="moonshotai/kimi-k2-instruct-0905",
    api_key=os.getenv("GROQ_API_KEY"),

).bind_tools(TOOLS)

# ------------------ Nodes ------------------

def llm_node(state: AgentState):
    try:
        response = llm.invoke(state["messages"])
        # Use response.tool_calls directly (LangChain format)
        tool_calls = response.tool_calls if response.tool_calls else []
        print("RAW RESPONSE:", response)  # or log to a file
        print("Tool calls in response:", response.tool_calls)
        return {
            "messages": [response],
            "tool_calls": tool_calls
        }
    except Exception as e:
        # Handle Groq API errors (like malformed tool calls)
        error_msg = str(e)
        if "tool_use_failed" in error_msg or "failed_generation" in error_msg:
            error_response = AIMessage(
                content=f"I encountered an error trying to call a tool. This usually happens when trying to use file paths with backslashes. "
                       f"Please try a different approach: use list_attached_files() first, then read the file content and pass only the code to python_tool, not file reading operations. "
                       f"Error details: {error_msg[:200]}"
            )
            return {
                "messages": [error_response],
                "tool_calls": []
            }
        else:
            # Re-raise other errors
            raise

def tool_node(state: AgentState):
    # Get the last tool call
    tool_call = state["tool_calls"][-1]
    tool_name = tool_call["name"]  # LangChain format: direct "name" key
    args = tool_call["args"]  # LangChain format: already parsed dict, not JSON string
    print("tool called: ",tool_name)
    print("Tool args: ",args)
    print("-----")
    
    # Execute tool with error handling
    result = None
    for tool in TOOLS:
        if tool.name == tool_name:
            try:
                result = tool.func(**args)
            except Exception as e:
                # Catch any unhandled exceptions and return helpful error message
                error_msg = f"ERROR in {tool_name}: {type(e).__name__} - {str(e)}"
                if "FileNotFoundError" in str(type(e)) or "file" in str(e).lower():
                    error_msg += " Hint: If you're trying to access a file, make sure to use list_attached_files() first to get the correct absolute path."
                result = error_msg
            break
    else:
        result = f"Tool {tool_name} not found. Available tools: {[t.name for t in TOOLS]}"
    
    msg = ToolMessage(
        content=str(result),
        name=tool_name,
        tool_call_id=tool_call["id"]
    )
    
    # Remove the executed tool call and return updated list
    remaining_tool_calls = state["tool_calls"][:-1]
    
    return {
        "messages": [msg],
        "tool_calls": remaining_tool_calls
    }

def router(state: AgentState):
    """Route logic: if tool_call exists, run tool. Otherwise end."""
    if state["tool_calls"]:
        return "tool"
    return END

# ------------------ Build Graph ------------------

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("llm", llm_node)
    workflow.add_node("tool", tool_node)

    workflow.set_entry_point("llm")

    # Correct conditional routing:
    workflow.add_conditional_edges(
        "llm",
        router,
        {
            "tool": "tool",
            END: END
        }
    )

    workflow.add_edge("tool", "llm")

    return workflow.compile()
