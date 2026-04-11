from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

@tool
def search_company_info(query: str) -> str:
    """Searches the live internet for information about a company. 
    Use this to find a company's culture, recent projects, tech stack, or core values."""
    search = DuckDuckGoSearchRun()
    try:
        # We wrap the search to catch any network timeouts
        results = search.invoke(query)
        return results
    except Exception as e:
        return f"Search failed. Error: {str(e)}"