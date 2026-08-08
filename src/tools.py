from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
from sympy import sympify
import requests
import arxiv
import os

from rag import retrieve_documents
from database import save_memory, search_memory


load_dotenv()

# CURRENT_THREAD_ID = "default"
# def set_current_thread_id(thread_id: str):
#     global CURRENT_THREAD_ID
#     CURRENT_THREAD_ID = thread_id


TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

# third tool
@tool
def github_search(query: str):
    """
    Search GitHub repositories.
    """

    url = "https://api.github.com/search/repositories"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 5,
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
    ).json()

    repos = []

    for repo in response["items"]:
        repos.append({
            "name": repo["full_name"],
            "description": repo["description"],
            "stars": repo["stargazers_count"],
            "url": repo["html_url"],
        })

    return repos


# def arxiv_search(query: str):
#     search = arxiv.Search(
#         query=query,
#         max_results=5
#     )
#     client = arxiv.Client()
#     for paper in client.results(search=search):
#         print(paper)


# forth tool
@tool
def arxiv_search(query: str):
    """
    Search arXiv papers.
    """

    client = arxiv.Client()

    search = arxiv.Search(
        query=query,
        max_results=5
    )

    papers = []

    for paper in client.results(search):
        papers.append({
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "published": paper.published.strftime("%Y-%m-%d"),
            "summary": paper.summary,
            "pdf": paper.pdf_url,
            "url": paper.entry_id,
        })

    return papers


# first tool
web_search = TavilySearch(
    max_results=5,
    topic="general",
    search_depth="advanced"
)

# second tool
@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = sympify(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# fifth tool
@tool
def search_uploaded_docs(query: str, config: RunnableConfig):
    """
    Search uploaded documents for relevant information.
    Use this when the user asks about uploaded PDFs, DOCX, TXT, notes, files, or documents.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Unable to search documents: conversation thread ID is missing."
    return retrieve_documents(
        query=query,
        thread_id=thread_id
    )


# sixth tool
@tool
def remember_this(memory: str, config: RunnableConfig) -> str:
    """
    function to save the memory into the LongTermMemory
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Unable to save memory: conversation thread ID is missing."
    return save_memory(thread_id=thread_id, memory=memory)

# seventh tool
@tool
def recall_memory(config: RunnableConfig):
    """
    Recall saved long-term memories about the user or this conversation.
    """
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "Unable to recall memory: conversation thread ID is missing."
    return search_memory(thread_id=thread_id)



def get_tools():
    tools = [
        web_search,
        calculator,
        github_search,
        arxiv_search,
        search_uploaded_docs,
        remember_this,
        recall_memory,
        ]
    return tools


# def get_tools(thread_id: str):
#     """
#     Build and return the list of tools for a given thread.
#     RAG and memory tools are scoped to the thread_id via closures,
#     so each conversation only accesses its own documents and memories.
#     """
 
#     # fifth tool — scoped to thread_id via closure
#     @tool
#     def search_uploaded_docs(query: str) -> str:
#         """
#         Search uploaded documents for relevant information.
#         Use this when the user asks about uploaded PDFs, DOCX, TXT, notes, files, or documents.
#         """
#         return retrieve_documents(query=query, thread_id=thread_id)
 
#     # sixth tool — scoped to thread_id via closure
#     @tool
#     def remember_this(memory: str) -> str:
#         """
#         Save an important fact or user preference to long-term memory.
#         Use this when the user asks you to remember something.
#         """
#         return save_memory(thread_id=thread_id, memory=memory)
 
#     # seventh tool — scoped to thread_id via closure
#     @tool
#     def recall_memory() -> str:
#         """
#         Recall saved long-term memories about the user or this conversation.
#         Use this when the user asks about previous preferences or saved facts.
#         """
#         return search_memory(thread_id=thread_id)
 
#     return [
#         web_search,
#         calculator,
#         github_search,
#         arxiv_search,
#         search_uploaded_docs,
#         remember_this,
#         recall_memory,
#     ]