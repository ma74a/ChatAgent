from langchain_tavily import TavilySearch
from dotenv import load_dotenv


load_dotenv()


# first tool
web_search = TavilySearch(
    max_results=5,
    topic="general",
    search_depth="advanced"
)



def get_tools():
    tools = [web_search]
    return tools