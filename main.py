import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import json
from datetime import datetime

# Setup Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv
from config import JOBS_EVALUATED_DIR, ML_TEMPLATE_NAME
from langgraph.graph import StateGraph, END
from graph_state import AgentState

# Import agents
from agents.job_reader.agent import get_job_reader_agent
from agents.company_researcher.agent import get_company_researcher_agent
from agents.resume_matcher.agent import get_resume_matcher_agent
from agents.job_tracker.agent import get_job_tracker_agent
from agents.ml_tailor.agent import get_ml_tailor_agent
from agents.coverletter_tailor.agent import get_coverletter_tailor_agent

load_dotenv()

def get_response_text(response):
    """Robustly extract text from a Gemini response, even if no text part is present."""
    try:
        return response.text
    except Exception:
        if response.candidates and response.candidates[0].content.parts:
            return str(response.candidates[0].content.parts[0])
        return "No text response returned."

def job_reader_node(state: AgentState):
    print(f"--- Job Reader: Processing {state['job_url']} ---")
    agent = get_job_reader_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(f"Analyze this URL: {state['job_url']}")
    job_details = get_response_text(response)
    with open(os.path.join(state['output_dir'], "job_description.txt"), "w", encoding="utf-8") as f:
        f.write(job_details)
    return {"job_details": job_details, "messages": ["Job Reader: Extracted requirements."]}

def company_researcher_node(state: AgentState):
    print(f"--- Company Researcher: Researching ---")
    agent = get_company_researcher_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(f"Research the company in these details: {state['job_details']}")
    company_info = get_response_text(response)
    with open(os.path.join(state['output_dir'], "company_info.txt"), "w", encoding="utf-8") as f:
        f.write(company_info)
    return {"company_info": company_info, "messages": ["Company Researcher: Gathered research."]}

def android_tailor_node(state: AgentState):
    print(f"--- Android Tailor: Tailoring AndroidCV ---")
    agent = get_resume_matcher_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    company_name = "Company"
    if state['job_details']:
        try:
            jd_json = json.loads(state['job_details'].strip('`').strip('json'))
            company_name = jd_json.get("Company Name", "Company")
        except: pass
    prompt = f"Tailor androidCV.tex for {company_name}.\nJD: {state['job_details']}\nResearch: {state['company_info']}\nTarget: {state['output_dir']}"
    response = chat.send_message(prompt)
    status = get_response_text(response)
    return {"compilation_status": status, "messages": ["Android Tailor: Done."]}

def ml_tailor_node(state: AgentState):
    print(f"--- ML Tailor: Tailoring MLCV ---")
    agent = get_ml_tailor_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    company_name = "Company"
    if state['job_details']:
        try:
            jd_json = json.loads(state['job_details'].strip('`').strip('json'))
            company_name = jd_json.get("Company Name", "Company")
        except: pass
    prompt = f"Tailor {ML_TEMPLATE_NAME} for {company_name}.\nJD: {state['job_details']}\nResearch: {state['company_info']}\nTarget: {state['output_dir']}"
    response = chat.send_message(prompt)
    status = get_response_text(response)
    return {"compilation_status": status, "messages": ["ML Tailor: Done."]}

def coverletter_tailor_node(state: AgentState):
    print(f"--- Cover Letter Tailor: Tailoring Cover Letter ---")
    agent = get_coverletter_tailor_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    company_name = "Company"
    if state['job_details']:
        try:
            jd_json = json.loads(state['job_details'].strip('`').strip('json'))
            company_name = jd_json.get("Company Name", "Company")
        except: pass
    prompt = f"Tailor cover letter for {company_name}.\nJD: {state['job_details']}\nResearch: {state['company_info']}\nTarget: {state['output_dir']}"
    response = chat.send_message(prompt)
    
    cover_letter_text = get_response_text(response)

    print(f"\n--- TAILORED COVER LETTER ---\n{cover_letter_text}\n---------------------------\n")
    
    return {"messages": ["Cover Letter Tailor: Generated .txt and .pdf."]}

def job_tracker_node(state: AgentState):
    print(f"--- Job Tracker: Updating Record ---")
    agent = get_job_tracker_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    prompt = f"Log this job: {state['job_details']} to {state['output_dir']}"
    response = chat.send_message(prompt)
    return {"messages": ["Job Tracker: Updated."], "next_step": END}

def route_to_tailor(state: AgentState):
    details = state['job_details'].lower()
    ml_keywords = ["machine learning", "ml ", "artificial intelligence", "ai ", "data science", "nlp", "computer vision"]
    if any(kw in details for kw in ml_keywords):
        return "ml_tailor"
    return "android_tailor"

# Workflow setup
workflow = StateGraph(AgentState)
workflow.add_node("job_reader", job_reader_node)
workflow.add_node("company_researcher", company_researcher_node)
workflow.add_node("android_tailor", android_tailor_node)
workflow.add_node("ml_tailor", ml_tailor_node)
workflow.add_node("coverletter_tailor", coverletter_tailor_node)
workflow.add_node("job_tracker", job_tracker_node)

workflow.set_entry_point("job_reader")
workflow.add_edge("job_reader", "company_researcher")
workflow.add_conditional_edges(
    "company_researcher",
    route_to_tailor,
    {
        "ml_tailor": "ml_tailor",
        "android_tailor": "android_tailor"
    }
)
# After tailoring the CV, always tailor the cover letter
workflow.add_edge("android_tailor", "coverletter_tailor")
workflow.add_edge("ml_tailor", "coverletter_tailor")
# Final step is the tracker
workflow.add_edge("coverletter_tailor", "job_tracker")
workflow.add_edge("job_tracker", END)

app = workflow.compile()

def run_job_application_pipeline(url: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(JOBS_EVALUATED_DIR, f"job_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    initial_state = {
        "job_url": url, "messages": [], "job_details": None, "company_info": None,
        "compilation_status": None, "next_step": "job_reader", "output_dir": output_dir
    }
    for output in app.stream(initial_state):
        for key, value in output.items():
            if "messages" in value: print(f"--- {value['messages'][-1]} ---")
    print(f"\nPipeline Complete! Output: {output_dir}")

if __name__ == "__main__":
    run_job_application_pipeline("https://jobright.ai/jobs/info/b2b_1774921041335_26?utm_source=5012&utm_campaign=b2b_1774921041335_26")
