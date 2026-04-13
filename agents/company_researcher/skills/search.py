from duckduckgo_search import DDGS
from utils.messenger import pipeline_messenger

def search_company_website(company_name: str) -> str:
    """Searches for the official website and basic info of a company."""
    pipeline_messenger.send("agent_activity", {"stage": "Company Researcher", "activity": f"Searching for company website: {company_name}"})
    try:
        with DDGS() as ddgs:
            # specifically looking for the official site
            results = list(ddgs.text(f"{company_name} official website company overview", max_results=3))
            if not results:
                return f"No search results found for {company_name}."

            summary = []
            for r in results:
                summary.append(f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}\n")

            full_summary = "\n".join(summary)
            pipeline_messenger.send("agent_activity", {"stage": "Company Researcher", "activity": f"Found company info:\n{full_summary}"})
            return full_summary
    except Exception as e:
        return f"Error searching for company website: {str(e)}"