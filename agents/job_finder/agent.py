import google.generativeai as genai
from .prompt import JOB_FINDER_PROMPT
from .skills.playwright_scraper import search_datanerd_jobs
from .skills.web_search import search_web_jobs
from config import MODEL_NAME
def get_job_finder_agent():
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        tools=[search_datanerd_jobs, search_web_jobs],
        system_instruction=JOB_FINDER_PROMPT
    )
