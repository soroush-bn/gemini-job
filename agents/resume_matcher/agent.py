import google.generativeai as genai
from config import GEMINI_API_KEY, MATCH_MODEL_NAME
from .prompt import RESUME_MATCHER_PROMPT
from .skills.latex_tools import read_latex_template, save_and_compile_latex, read_facts

def get_resume_matcher_agent():
    """Initializes the Resume Matcher agent with Gemini and LaTeX skills."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        model_name=MATCH_MODEL_NAME, # Using Pro as defined in config
        tools=[read_latex_template, save_and_compile_latex, read_facts],
        system_instruction=RESUME_MATCHER_PROMPT
    )
    
    return model
