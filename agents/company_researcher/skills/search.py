from duckduckgo_search import DDGS

def search_company_info(company_name: str) -> str:
    """Searches for information about a company using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{company_name} company overview culture values", max_results=5))
            if not results:
                return f"No results found for {company_name}."
            
            summary = []
            for r in results:
                summary.append(f"Title: {r['title']}\nSnippet: {r['body']}\nSource: {r['href']}\n")
            
            return "\n".join(summary)
    except Exception as e:
        return f"Error searching for company: {str(e)}"
