# ChatAgent 🤖

A full-stack agentic AI chatbot powered by **Google Gemini** and **LangGraph**, with persistent conversations, real-time streaming, RAG over uploaded documents, long-term memory, and web search — served through a **FastAPI** backend.

## Features

- 💬 **Multi-turn Conversations** — persistent chat history with SQLite, each conversation is an independent thread
- 🔁 **Streaming Responses** — real-time token-by-token output via Server-Sent Events (SSE)
- 🧠 **Long-Term Memory** — agent saves and recalls facts within a conversation
- 📄 **Document RAG** — upload files and query them via ChromaDB similarity search, scoped per thread
- 🌐 **Web Search** — Tavily real-time search for current events and time-sensitive queries
- 🔬 **arXiv Search** — look up research papers directly from chat
- 🐙 **GitHub Search** — find repositories by keyword via the GitHub API
- 🧮 **Calculator** — symbolic math via SymPy
- 🎨 **Modern UI** — dark-theme SPA with Markdown rendering, syntax highlighting, TTS, voice input, model switcher

## Agent Graph

```
      __start__
          │
          ▼
     chat_node
     ╱        ╲
__end__       tools
               │
               ▼
          chat_node
```

## Tools

| Tool | Description |
|------|-------------|
| `web_search` | Tavily real-time web search |
| `calculator` | Symbolic math via SymPy |
| `github_search` | GitHub repo search, sorted by stars |
| `arxiv_search` | arXiv paper search with abstract and PDF link |
| `search_uploaded_docs` | Similarity search over uploaded documents in ChromaDB |
| `remember_this` | Save a fact to long-term memory |
| `recall_memory` | Retrieve saved memories for the conversation |

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Serve the chat UI |
| `POST` | `/conversations` | Create a new conversation |
| `GET` | `/conversations` | List all conversations |
| `GET` | `/history/{thread_id}` | Fetch chat history for a thread |
| `POST` | `/chat` | Send a message, get a full response |
| `POST` | `/chat/stream` | Send a message, stream response via SSE |
| `POST` | `/upload` | Upload a file and index it into ChromaDB |

## Getting Started

### Prerequisites

- Python 3.10+
- API keys for Google Gemini and Tavily
- GitHub Personal Access Token (optional)

### Installation

```bash
git clone https://github.com/ma74a/ChatAgent.git
cd ChatAgent
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key
GITHUB_TOKEN=your_github_token   # optional
```

### Run

```bash
cd src
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Supported File Types

`.pdf` · `.docx` · `.txt` · `.md` · `.py` · `.csv`

## Tech Stack

| | Technology |
|-|-----------|
| LLM | Google Gemini |
| Agent | LangGraph |
| Backend | FastAPI + Uvicorn |
| Vector Store | ChromaDB |
| Embeddings | `gemini-embedding-001` |
| Database | SQLite + SQLAlchemy |
| Web Search | Tavily |
| Frontend | Vanilla JS, Marked.js, Highlight.js |

## License

MIT