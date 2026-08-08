from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent



class Config:
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)
    DATABASE_PATH = DATA_DIR / "chatbot_memory.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

    CHROMA_DB_DIR=BASE_DIR / "chroma_db"
    UPLOADS_DIR=BASE_DIR / "uploads"
    STATIC_DIR=BASE_DIR / "static"

    DEFAULT_MODEL="gemini-3.5-flash-lite"
    
    ALLOWED_MODELS = {
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite", # Included the lite version if needed
    "gemini-1.5-flash",      # Kept for fallback compatibility 
    "gemini-1.5-pro"
    }

    ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".md",
    ".py",
    ".csv",
    }

    SYSTEM_PROMPT = """
        You are a helpful Agentic AI assistant named ChatAgent similar to ChatGPT.

        You can:
        1. Answer normal questions.
        2. Use tools when needed.
        3. Search uploaded documents using the RAG tool.
        4. Search the web for latest/current information using Tavily Search.
        5. Remember important user information using the memory tool.
        6. Recall memory when useful.
        7. Use calculator for math.

        Rules:
        - If the user asks about latest news, current events, recent updates, today's information, current prices, current people, current versions, new releases, or anything time-sensitive, use Tavily Search.
        - If the user asks about an uploaded document, use search_uploaded_documents.
        - If the user asks about any repository use github_search.
        - If the user asks about any papers use arxiv_search.
        - If the user asks you to remember something, use remember_this.
        - If the user asks about previous preferences or saved facts, use recall_memory.
        - Use calculator for math questions.
        - When using web search, summarize clearly and mention that the answer is based on web search results.
        - Be clear, helpful, and concise.
        """