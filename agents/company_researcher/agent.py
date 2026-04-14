import google.generativeai as genai
from config import GEMINI_API_KEY, MODEL_NAME
from .prompt import COMPANY_RESEARCHER_PROMPT

def get_company_researcher_agent():
    """Initializes the Expert Company Researcher agent (Knowledge-based)."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Tools removed to rely on internal knowledge and JD context
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=COMPANY_RESEARCHER_PROMPT
    )
    
    return model
