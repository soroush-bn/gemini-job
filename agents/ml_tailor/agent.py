import google.generativeai as genai
from config import GEMINI_API_KEY, MATCH_MODEL_NAME
from .prompt import ML_TAILOR_PROMPT
from agents.resume_matcher.skills.latex_tools import read_latex_template, save_and_compile_latex

def get_ml_tailor_agent():
    """Initializes the ML Tailor agent with Gemini."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        model_name=MATCH_MODEL_NAME,
        tools=[read_latex_template, save_and_compile_latex],
        system_instruction=ML_TAILOR_PROMPT
    )
    
    return model
