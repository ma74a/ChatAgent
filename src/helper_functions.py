from langchain_core.messages import HumanMessage

from agent import get_agent

def agent_chat(thread_id: str, message: str):
    agent = get_agent()
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
    agent = get_agent(model_name=model_name)

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