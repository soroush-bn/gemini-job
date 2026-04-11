import google.generativeai as genai
from config import GEMINI_API_KEY, MODEL_NAME
from .prompt import COMPANY_RESEARCHER_PROMPT
from .skills.search import search_company_website
from agents.job_reader.skills.fetch_web import fetch_web_content

def get_company_researcher_agent():
    """Initializes the improved Company Researcher with search AND browsing capabilities."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # We now give the agent BOTH tools: Search (to find the site) and Fetch (to read it)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        tools=[search_company_website, fetch_web_content],
        system_instruction=COMPANY_RESEARCHER_PROMPT
    )
    
    return model
