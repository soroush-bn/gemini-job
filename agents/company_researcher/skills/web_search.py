from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from utils.messenger import pipeline_messenger

@tool
def search_company_info(query: str) -> str:
    """Searches the live internet for information about a company. 
    Use this to find a company's culture, recent projects, tech stack, or core values."""
    pipeline_messenger.send("agent_activity", {"stage": "Company Researcher", "activity": f"Searching DDG for: {query}"})
    search = DuckDuckGoSearchRun()
    try:
        # We wrap the search to catch any network timeouts
        results = search.invoke(query)
        pipeline_messenger.send("agent_activity", {"stage": "Company Researcher", "activity": f"Search Results for '{query}':\n{results[:1000]}..."})
        return results
    except Exception as e:
        return f"Search failed. Error: {str(e)}"