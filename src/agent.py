from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
import sqlite3
import os
from pathlib import Path


from config import Config
from tools import get_tools

load_dotenv()

Path(Config.DATA_DIR).mkdir(exist_ok=True)

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

    database_path = Config.DATA_DIR / "langgraph_checkpoints.sqlite"
    conn = sqlite3.connect(database=database_path,check_same_thread=False)
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

from typing import Generator


def extract_text_from_message(chunk) -> str:
    """
    Extract plain text from a LangChain message or streamed chunk.

    Supports:
    - Plain string content
    - List[str]
    - List[dict] (Gemini/OpenAI structured responses)
    """

    content = getattr(chunk, "content", "")

    if not content:
        return ""

    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return str(content)

    text_parts = []

    for item in content:
        if isinstance(item, str):
            text_parts.append(item)

        elif isinstance(item, dict):
            text = item.get("text") or item.get("content")
            if isinstance(text, str):
                text_parts.append(text)

    return "".join(text_parts).strip()

def agent_stream(thread_id: str, message: str, model_name: str | None = None):
    agent = get_agent("gemini-3.5-flash-lite")

    for event in agent.stream(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="messages" # stream individual message chunks
    ):
        # event is a tuple: (chunk, metadata)
        chunk, metadata = event

        # Only yield content from the chat_node, skip tool call chunks
        if (
            metadata.get("langgraph_node") == "chat_node"
            and hasattr(chunk, "content")
            and chunk.content
        ):
            text = extract_text_from_message(chunk=chunk)
            if text:
                yield text


    