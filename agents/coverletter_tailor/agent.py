import google.generativeai as genai
from config import GEMINI_API_KEY, MATCH_MODEL_NAME
from .prompt import COVERLETTER_TAILOR_PROMPT
from .skills.coverletter_tools import read_coverletter_template, save_coverletter_outputs

def get_coverletter_tailor_agent():
    """Initializes the Cover Letter Tailor agent with Gemini."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        model_name=MATCH_MODEL_NAME,
        tools=[read_coverletter_template, save_coverletter_outputs],
        system_instruction=COVERLETTER_TAILOR_PROMPT
    )
    
    return model
