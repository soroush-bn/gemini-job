import google.generativeai as genai
from config import GEMINI_API_KEY, MATCH_MODEL_NAME, MODEL_NAME
from .prompt import CV_TAILOR_PROMPT
from .skills.cv_tools import get_career_facts, get_cv_template, save_and_compile_latex

def get_cv_tailor_agent():
    """Initializes the unified CV Tailor agent with LaTeX tools."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        model_name=MATCH_MODEL_NAME, 
        system_instruction=CV_TAILOR_PROMPT,
        tools=[get_career_facts, get_cv_template, save_and_compile_latex]
    )
    
    return model
