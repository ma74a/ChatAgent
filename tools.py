from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
from sympy import sympify
import requests
import arxiv
import os

from rag import retrieve_documents


load_dotenv()

CURRENT_THREAD_ID = "default"


def set_current_thread_id(thread_id: str):
    global CURRENT_THREAD_ID
    CURRENT_THREAD_ID = thread_id

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
def search_uploaded_docs(query: str):
    """
    Search uploaded documents for relevant information.
    Use this when the user asks about uploaded PDFs, DOCX, TXT, notes, files, or documents.
    """
    return retrieve_documents(
        query=query,
        thread_id=CURRENT_THREAD_ID
    )

def get_tools():
    tools = [
        web_search,
        calculator,
        github_search,
        arxiv_search,
        ]
    return tools