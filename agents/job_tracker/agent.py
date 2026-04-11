import google.generativeai as genai
from config import GEMINI_API_KEY, MODEL_NAME
from .prompt import JOB_TRACKER_PROMPT
from .skills.tracker_tool import update_job_tracker_table

def get_job_tracker_agent():
    """Initializes the Job Tracker agent with Gemini."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        tools=[update_job_tracker_table],
        system_instruction=JOB_TRACKER_PROMPT
    )
    
    return model
