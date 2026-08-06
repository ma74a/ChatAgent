from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from pathlib import Path
from typing import List
from utils import Config

Path("data").mkdir(exist_ok=True)

"""
check_same_thread=False

SQLite normally allows only the thread that created the connection to use it.

FastAPI handles requests using multiple threads.
"""
#This creates a connection between your Python program and the database.
engine = create_engine(
    Config.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# The session is how you talk to the database.
SessionLocal = sessionmaker(bind=engine, # Connect this session factory to the engine.
                            autoflush=False, # you control when changes are flushed or committed.
                            autocommit=False) # This lets you group several operations into a single transaction.

# This is the parent class for all your tables.
Base = declarative_base()

# Conversation class stores information about the chat itself.
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, unique=True, index=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

# ChatMessage class stores the actual messages.
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, index=True)
    role = Column(String) # The role column tells you who sent the message.( User, AI)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class LongTermMemory(Base):
    __tablename__ = "long_term_memory"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, index=True)
    memory = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Function to initialize The DataBase"""
    Base.metadata.create_all(bind=engine)



def create_or_update_conversation(thread_id: str, first_message: str | None=None):
    """
    Create a new conversation if it does not exist, or update its
    last activity timestamp if it already exists.

    When creating a new conversation, the title is generated from the
    first user message (up to 40 characters). If no first message is
    provided, the default title "New Chat" is used.

    Args:
        thread_id (str): Unique identifier for the conversation.
        first_message (str | None, optional): The first user message,
            used to generate the conversation title.

    Returns:
        None
    """
    db = SessionLocal()

    try:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.thread_id==thread_id)
            .first()
        )

        if not conversation:
            title = "New Chat"

            if first_message:
                title = first_message.strip()[:40]
                if len(first_message.strip()) > 40:
                    title += "..."

            conversation = Conversation(
                thread_id=thread_id,
                title=title,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.add(conversation)

        else:
            conversation.updated_at = datetime.utcnow()

        db.commit()

    finally:
        db.close()


def list_conversations() -> List[Conversation]:
    """
    Retrieve all conversations from the database ordered by their
    last activity time in descending order.

    The most recently updated conversations appear first, making it
    suitable for displaying the chat history in the application's UI.

    Returns:
        list[Conversation]: A list of Conversation objects sorted by
            their `updated_at` timestamp (newest first).
    """
    db = SessionLocal()

    try:
        return(
            db.query(Conversation)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    finally:
        db.close()


def save_chat_message(thread_id: str, role: str, content: str):
    """
    Save a chat message to the database and update the conversation's
    last activity timestamp.

    A new ChatMessage record is created for the specified conversation.
    If the conversation exists, its `updated_at` field is refreshed to
    reflect the latest activity.

    Args:
        thread_id (str): Unique identifier of the conversation.
        role (str): The sender of the message (e.g., "user", "assistant").
        content (str): The message text.

    Returns:
        None
    """
    db = SessionLocal()

    try:
        msg = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            created_at=datetime.utcnow()
        )

        db.add(msg)

        conversation = (
            db.query(Conversation)
            .filter(Conversation.thread_id == thread_id)
            .first()
        )

        if conversation:
            conversation.updated_at = datetime.utcnow()

        db.commit()

    finally:
        db.close()


def get_chat_history(thread_id: str) -> List[ChatMessage]:
    """
    Retrieve the complete chat history for a specific conversation.

    Fetches all messages associated with the given `thread_id`, ordered
    from oldest to newest. This preserves the natural
    conversation flow and is suitable for reconstructing the chat history
    for display in the UI or providing context to the LLM.

    Args:
        thread_id (str): Unique identifier of the conversation.

    Returns:
        list[ChatMessage]: A list of ChatMessage objects ordered by
            their `created_at` timestamp in ascending order.
    """
    db = SessionLocal()

    try: 
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.thread_id==thread_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

    finally:
        db.close()


def save_memory(thread_id: str, memory: str) -> str:
    """
    Save a long-term memory associated with a specific conversation.

    Creates a new LongTermMemory record containing information that
    should persist beyond the current chat session, such as user
    preferences, personal details, or important facts.

    Args:
        thread_id (str): Unique identifier of the conversation.
        memory (str): The memory or fact to be stored.

    Returns:
        str: A confirmation message indicating that the memory was
            successfully saved.
    """
    db = SessionLocal()

    try:
        exits = (
            db.query(LongTermMemory)
            .filter(
                LongTermMemory.thread_id == thread_id,
                LongTermMemory.memory == memory
            )
            .first()
        )

        if exits:
            return "Memory already exists."

        
        item = LongTermMemory(
            thread_id=thread_id,
            memory=memory,
            created_at=datetime.utcnow()
        )

        db.add(item)
        db.commit()

        return "Memory saved successfully."

    finally:
        db.close()


def search_memory(thread_id: str) -> str:
    """
    Retrieve the most recent long-term memories associated with a
    specific conversation.

    Fetches up to 20 memories for the given `thread_id`, ordered from
    newest to oldest. The retrieved memories are formatted as a single
    string, making them suitable for inclusion in an LLM prompt. If no
    memories are found, a message indicating that no memories exist is
    returned.

    Args:
        thread_id (str): Unique identifier of the conversation.

    Returns:
        str: A formatted string containing the retrieved memories, or
            a message indicating that no memories were found.
    """
    db = SessionLocal()

    try:
        memories = (
            db.query(LongTermMemory)
            .filter(LongTermMemory.thread_id==thread_id)
            .order_by(LongTermMemory.created_at.desc())
            .limit(20)
            .all()
        )

        if not memories:
            return "No saved Memory found"

        return "\n".join([f"- {m.memory}" for m in memories])

    finally:
        db.close()



def conversation_exit(thread_id: str) -> bool:
    """
    Check whether a conversation with the given thread ID exists.

    Args:
        thread_id (str): Unique identifier of the conversation.

    Returns:
        bool: True if the conversation exists, otherwise False.
    """
    db = SessionLocal()

    try:
        conversation = (
        db.query(Conversation)
        .filter(Conversation.thread_id==thread_id)
        .first()
        )

        return conversation is not None

    finally:
        db.close()