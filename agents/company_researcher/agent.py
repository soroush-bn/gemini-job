import google.generativeai as genai
from config import GEMINI_API_KEY, MODEL_NAME
from .prompt import COMPANY_RESEARCHER_PROMPT
from .skills.search import search_company_info

def get_company_researcher_agent():
    """Initializes the Company Researcher agent with Gemini and search tools."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        tools=[search_company_info],
        system_instruction=COMPANY_RESEARCHER_PROMPT
    )
    
    return model
