from duckduckgo_search import DDGS
from utils.messenger import pipeline_messenger
import json

def search_web_jobs(role: str, country: str, timeframe: str = "w") -> str:
    """Searches the web (DuckDuckGo) for job listings matching the role and country.
    timeframe: 'd' (day), 'w' (week), 'm' (month).
    Returns a list of potential job URLs."""
    
    query = f'"{role}" job "{country}" (site:lever.co OR site:greenhouse.io OR site:workable.com OR site:boards.greenhouse.io)'
    pipeline_messenger.send("log", f"Searching the web for jobs: {query}")
    pipeline_messenger.send("agent_activity", {"stage": "Job Finder", "activity": f"Web Search: {query}"})
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=15, safesearch="off", timelimit=timeframe))
            if not results:
                return "No jobs found via web search."
            
            urls = [r['href'] for r in results]
            pipeline_messenger.send("log", f"Web search found {len(urls)} potential job links.")
            return json.dumps(urls)
    except Exception as e:
        error_msg = f"Error during web search: {str(e)}"
        pipeline_messenger.send("log", error_msg)
        return error_msg
