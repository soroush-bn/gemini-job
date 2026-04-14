import os
import json
import re
from langgraph.graph import END
from graph_state import AgentState
from config import JOBS_EVALUATED_DIR, CV_WORKSPACE, TEMPLATE_NAME, ML_TEMPLATE_NAME
from utils.helpers import get_response_text, get_url_hash, sanitize_for_filesystem
from utils.messenger import pipeline_messenger

# Import agents
from agents.job_reader.agent import get_job_reader_agent
from agents.company_researcher.agent import get_company_researcher_agent
from agents.cv_tailor.agent import get_cv_tailor_agent
from agents.job_tracker.agent import get_job_tracker_agent
from agents.coverletter_tailor.agent import get_coverletter_tailor_agent
from agents.job_tracker.skills.token_tracker import log_token_usage

# Skills
from agents.cv_tailor.skills.cv_tools import save_and_compile_latex
from agents.coverletter_tailor.skills.coverletter_tools import save_coverletter_as_pdf

def supervisor_node(state: AgentState):
    """Supervisor decides which agent to call next based on current state."""
    job_details = state.get("job_details")
    company_info = state.get("company_info")
    compilation_status = state.get("compilation_status")
    cl_status = state.get("cl_status")

    if not job_details:
        return {"next_step": "job_reader"}
    
    if not company_info:
        return {"next_step": "company_researcher"}
    
    if not compilation_status:
        return {"next_step": "cv_tailor"}
    
    if not cl_status:
        return {"next_step": "coverletter_tailor"}
    
    return {"next_step": "job_tracker"}

def job_reader_node(state: AgentState):
    msg = f"--- Job Reader Agent: Processing {state['job_url']} ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    
    agent = get_job_reader_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(f"Analyze this URL: {state['job_url']}")
    
    cost = log_token_usage("Job Reader", response.usage_metadata, model_type="flash-lite") if response.usage_metadata else 0.0
    job_details = get_response_text(response)
    
    # Save raw description
    with open(os.path.join(state['output_dir'], "job_description.txt"), "w", encoding="utf-8") as f:
        f.write(job_details)

    # Sanitize and rename dir
    company = "Unknown"
    url_hash = get_url_hash(state['job_url'])
    try:
        json_clean = job_details.strip('`').strip('json').strip()
        if json_clean.startswith('{'):
            jd_json = json.loads(json_clean)
            company = jd_json.get("Company Name", "Unknown")
            url_hash = get_url_hash(jd_json.get("Current URL", state['job_url']))
    except: pass

    company = sanitize_for_filesystem(company)
    new_dir_name = f"{company}_{url_hash}"
    new_output_dir = os.path.join(JOBS_EVALUATED_DIR, new_dir_name)
    
    if not os.path.exists(new_output_dir):
        os.rename(state['output_dir'], new_output_dir)
        state['output_dir'] = new_output_dir

    return {
        "job_details": job_details, 
        "output_dir": state['output_dir'],
        "total_cost": state.get('total_cost', 0.0) + cost
    }

def company_researcher_node(state: AgentState):
    msg = "--- Company Researcher Agent: Researching Company ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    
    agent = get_company_researcher_agent()
    chat = agent.start_chat(enable_automatic_function_calling=False)
    response = chat.send_message(f"Research this company based on the JD:\n\n{state['job_details']}")
    
    cost = log_token_usage("Company Researcher", response.usage_metadata, model_type="flash-lite") if response.usage_metadata else 0.0
    company_info = get_response_text(response)
    
    with open(os.path.join(state['output_dir'], "company_info.txt"), "w", encoding="utf-8") as f:
        f.write(company_info)
        
    return {"company_info": company_info, "total_cost": state.get('total_cost', 0.0) + cost}

def cv_tailor_node(state: AgentState):
    msg = "--- CV Tailor Agent: Selecting and Tailoring Template ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    
    agent = get_cv_tailor_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    company_name = "Company"
    try:
        jd_json = json.loads(state['job_details'].strip('`').strip('json').strip())
        company_name = jd_json.get("Company Name", "Company")
    except: pass

    prompt = f"Tailor my CV for {company_name}.\n\nTarget Directory: {state['output_dir']}\n\nJD: {state['job_details']}\n\nResearch: {state['company_info']}"
    response = chat.send_message(prompt)
    
    cost = log_token_usage("CV Tailor", response.usage_metadata, model_type="flash-lite") if response.usage_metadata else 0.0
    status = get_response_text(response)
    
    # Fallback if agent returned LaTeX instead of calling tool
    if "Success!" not in status and "```latex" in status:
        latex_code = status.split("```latex")[1].split("```")[0].strip()
        status = save_and_compile_latex(latex_code, company_name, state['output_dir'])
    
    return {"compilation_status": status, "total_cost": state.get('total_cost', 0.0) + cost}

def coverletter_tailor_node(state: AgentState):
    msg = "--- Cover Letter Agent: Tailoring CL ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    
    agent = get_coverletter_tailor_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    company_name = "Company"
    try:
        jd_json = json.loads(state['job_details'].strip('`').strip('json').strip())
        company_name = jd_json.get("Company Name", "Company")
    except: pass

    prompt = f"Write a tailored cover letter for {company_name}.\n\nTarget Directory: {state['output_dir']}\n\nJD: {state['job_details']}\n\nResearch: {state['company_info']}"
    response = chat.send_message(prompt)
    
    cost = log_token_usage("Cover Letter Tailor", response.usage_metadata, model_type="flash-lite") if response.usage_metadata else 0.0
    status = get_response_text(response)
    
    # Fallback if agent returned text instead of calling tool
    if "Success!" not in status and len(status) > 100:
        status = save_coverletter_as_pdf(status, state['output_dir'], company_name)

    return {"cl_status": status, "total_cost": state.get('total_cost', 0.0) + cost}

def job_tracker_node(state: AgentState):
    msg = "--- Job Tracker Agent: Updating Log ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    
    agent = get_job_tracker_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    url_hash = get_url_hash(state['job_url'])
    prompt = f"Log this application:\nJD: {state['job_details']}\nOutput: {state['output_dir']}\nHash: {url_hash}"
    response = chat.send_message(prompt)
    
    cost = log_token_usage("Job Tracker", response.usage_metadata, model_type="flash-lite") if response.usage_metadata else 0.0
    return {"total_cost": state.get('total_cost', 0.0) + cost}
