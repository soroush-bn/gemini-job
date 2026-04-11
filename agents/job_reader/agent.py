import google.generativeai as genai
from config import GEMINI_API_KEY, MODEL_NAME
from .prompt import JOB_READER_PROMPT
from .skills.fetch_web import fetch_web_content

def get_job_reader_agent():
    """Initializes the Job Reader agent with Gemini and its web fetching skill."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Initialize the Gemini model with the specified tool
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        tools=[fetch_web_content],
        system_instruction=JOB_READER_PROMPT
    )
    
    return model
