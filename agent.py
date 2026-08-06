from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
import sqlite3
import os
from pathlib import Path


from utils import Config
from tools import get_tools

load_dotenv()

Path("data").mkdir(exist_ok=True)

def validate_model(model_name: str) -> str:
    """Validate the model name which is right model name or not"""
    if not model_name:
        return Config.DEFAULT_MODEL

    model_name = model_name.strip()

    if model_name not in Config.ALLOWED_MODELS:
        model_name = Config.DEFAULT_MODEL

    return model_name

def create_llm_model(model_name: str):
    """Create the llm using gemini"""
    tools = get_tools()
    selected_model = validate_model(model_name)

    llm = ChatGoogleGenerativeAI(
        model=selected_model
    )
    llm_with_tools = llm.bind_tools(tools=tools)
    return llm_with_tools

def chat_node(state: MessagesState, llm_with_tools):
    """Create the chat Node"""
    messages = [SystemMessage(content=Config.SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response]
    }

def build_agent_graph(model_name: str):
    """Create the agent graph"""
    
    llm_with_tools = create_llm_model(model_name=model_name)
    tools = get_tools()

    def chat_node(state: MessagesState):
        """Create the chat Node"""
        messages = [SystemMessage(content=Config.SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)

        return {
            "messages": [response]
        }

    workflow = StateGraph(MessagesState)

    workflow.add_node("chat_node", chat_node)
    tool_node = ToolNode(tools=tools)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "chat_node")
    workflow.add_conditional_edges("chat_node", tools_condition)
    workflow.add_edge("tools", "chat_node")

    conn = sqlite3.connect(database="data/langgraph_checkpoints.sqlite",check_same_thread=False)
    checkpoint = SqliteSaver(conn=conn)

    return workflow.compile(checkpointer=checkpoint)


_AGENT_CACHE = {}

def get_agent(model_name: str | None = None):
    """
    Return cached LangGraph agent for selected model.
    If not created yet, create it once and reuse it.
    """

    selected_model = validate_model(model_name)

    if selected_model not in _AGENT_CACHE:
        _AGENT_CACHE[selected_model] = build_agent_graph(selected_model)

    return _AGENT_CACHE[selected_model]



def agent_chat(thread_id: str, message: str):
    agent = get_agent("gemini-3.5-flash-lite")
    result = agent.invoke(
        {
            "messages": [
                HumanMessage(content=message)
            ]
        },
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )
    # last_message = result["messages"][-1]

    # print(type(last_message.content))
    # print(last_message.content[0]["text"])
    # last_message = last_message.content[0]["text"]

    return result["messages"][-1]
