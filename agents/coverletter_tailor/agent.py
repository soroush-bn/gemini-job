import google.generativeai as genai
from config import GEMINI_API_KEY, MODEL_NAME
from .prompt import COVERLETTER_TAILOR_PROMPT
from .skills.coverletter_tools import save_coverletter_as_pdf, get_career_facts, get_coverletter_template

def get_coverletter_tailor_agent():
    """Initializes the Cover Letter Tailor agent with tools."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=COVERLETTER_TAILOR_PROMPT,
        tools=[save_coverletter_as_pdf, get_career_facts, get_coverletter_template]
    )
    
    return model
