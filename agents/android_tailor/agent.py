import google.generativeai as genai
from config import GEMINI_API_KEY, MODEL_NAME
from .prompt import RESUME_MATCHER_PROMPT
from .skills.cv_tools import save_and_compile_latex

def get_android_tailor_agent():
    """Initializes the Android Tailor agent with full LaTeX saving skill."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        model_name=MODEL_NAME, 
        tools=[save_and_compile_latex],
        system_instruction=RESUME_MATCHER_PROMPT
    )
    
    return model
