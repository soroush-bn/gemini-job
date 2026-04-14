import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import json
import re
import hashlib
from datetime import datetime

# Setup Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv
from config import JOBS_EVALUATED_DIR, ML_TEMPLATE_NAME, CV_WORKSPACE, FACTS_FILE, TEMPLATE_NAME, COVERLETTER_TEMPLATE
from langgraph.graph import StateGraph, END
from graph_state import AgentState

def read_workspace_file(filename):
    """Helper to read files from the cv_workspace directory."""
    path = os.path.join(CV_WORKSPACE, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# Import agents
from agents.job_reader.agent import get_job_reader_agent
from agents.company_researcher.agent import get_company_researcher_agent
from agents.android_tailor.agent import get_android_tailor_agent
from agents.job_tracker.agent import get_job_tracker_agent
from agents.ml_tailor.agent import get_ml_tailor_agent
from agents.coverletter_tailor.agent import get_coverletter_tailor_agent
from agents.job_finder.agent import get_job_finder_agent
from agents.job_tracker.skills.token_tracker import log_token_usage
from utils.messenger import pipeline_messenger

load_dotenv()

def get_response_text(response):
    """Robustly extract text from a Gemini response, even if no text part is present."""
    try:
        if hasattr(response, 'text') and response.text:
            return response.text
    except Exception:
        pass
    
    try:
        # Check if it's a function call or other non-text part
        if response.candidates and response.candidates[0].content.parts:
            # Join all text parts if multiple exist
            text_parts = [part.text for part in response.candidates[0].content.parts if hasattr(part, 'text') and part.text]
            if text_parts:
                return "".join(text_parts)
                
            part = response.candidates[0].content.parts[0]
            if hasattr(part, 'function_call'):
                return f"[Executing Tool: {part.function_call.name}]"
            return str(part)
    except:
        pass
    return ""

def run_job_finder(input_func=input, initial_query=None):
    """Interactively finds jobs and returns a list of URLs."""
    msg = "--- Starting Job Finder Agent ---"
    print(f"\n{msg}")
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Job Finder", "activity": "Searching for jobs..."})
    
    agent = get_job_finder_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    user_msg = initial_query if initial_query else "Hello! I want to find some jobs."
    
    # Track turns to avoid immediate input prompt if query was provided
    turn_count = 0
    
    while True:
        if not user_msg or not user_msg.strip():
            user_msg = "Please continue or provide more instructions."

        try:
            response = chat.send_message(user_msg)
            text = get_response_text(response)
            print(f"\nAgent: {text}")
            pipeline_messenger.send("agent_chat", {"role": "agent", "content": text})
            pipeline_messenger.send("agent_activity", {"stage": "Job Finder", "activity": text})
            
            # Check if the agent outputted a JSON list of URLs
            if "```json" in text:
                try:
                    # Extract JSON block
                    json_str = text.split("```json")[1].split("```")[0].strip()
                    urls = json.loads(json_str)
                    if isinstance(urls, list) and len(urls) > 0:
                        return urls
                except:
                    pass
            
            # If we just started with a query and got NO jobs, 
            # let the agent try one more time or then ask user
            if turn_count == 0 and initial_query and "```json" not in text:
                # If agent didn't give JSON, it might be describing what it found
                # or asking for clarification. Only ask user if it seems stuck.
                pass

        except Exception as e:
            err = f"AI Communication Error: {e}"
            print(err)
            pipeline_messenger.send("log", err)
            return None
        
        turn_count += 1
        user_msg = input_func("\nYou: ")
        if user_msg is None: # Dialog cancelled
            return None
        pipeline_messenger.send("agent_chat", {"role": "user", "content": user_msg})

def get_url_hash(url: str):
    """Generates a short 8-character hash of the URL."""
    return hashlib.md5(url.encode()).hexdigest()[:8]

def job_reader_node(state: AgentState):
    msg = f"--- Job Reader: Processing {state['job_url']} ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Job Reader", "activity": f"Analyzing URL: {state['job_url']}"})
    agent = get_job_reader_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(f"Analyze this URL: {state['job_url']}")
    
    # Log usage
    cost = 0.0
    if response.usage_metadata:
        cost = log_token_usage("Job Reader", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="flash-lite")

    job_details = get_response_text(response)
    pipeline_messenger.send("agent_activity", {"stage": "Job Reader", "activity": job_details})
    
    # Save raw details first
    with open(os.path.join(state['output_dir'], "job_description.txt"), "w", encoding="utf-8") as f:
        f.write(job_details)

    # Robust extraction for renaming directory
    company = "Unknown"
    url_hash = get_url_hash(state['job_url'])
    is_error = False
    
    # Detect plain text errors from scraper tool
    if "error" in job_details.lower() and ("fetching" in job_details.lower() or "extract" in job_details.lower()):
        is_error = True

    try:
        # Try to find JSON block
        json_str = job_details
        if "```" in json_str:
            json_str = re.split(r'```(?:json)?', json_str)[1].split('```')[0]
        
        json_clean = json_str.strip()
        if json_clean.startswith('{'):
            jd_json = json.loads(json_clean)
            
            # Check for error status from agent
            if jd_json.get("Status") == "Error" or jd_json.get("status") == "Error":
                is_error = True
                msg = f"Job Reader failed: {jd_json.get('Message', 'Unknown reason')}"
                print(f"\n[ERROR] {msg}")
                pipeline_messenger.send("log", msg)
            
            company = jd_json.get("Company Name") or jd_json.get("company_name") or jd_json.get("Company") or "Unknown"
            canonical_url = jd_json.get("Current URL") or jd_json.get("current_url") or state['job_url']
            url_hash = get_url_hash(canonical_url)
    except Exception:
        pass

    # Sanitize for filesystem
    def sanitize(text):
        text = text.replace(" ", "_")
        return re.sub(r'[^\w\-]', '', text)

    company = sanitize(company)
    new_dir_name = f"{company}_{url_hash}"
    new_output_dir = os.path.join(JOBS_EVALUATED_DIR, new_dir_name)
    
    # Perform rename
    state['output_dir'] = os.path.abspath(state['output_dir'])
    new_output_dir = os.path.abspath(os.path.join(JOBS_EVALUATED_DIR, new_dir_name))
    
    if state['output_dir'] != new_output_dir:
        if os.path.exists(new_output_dir):
            state['output_dir'] = new_output_dir
        else:
            try:
                os.rename(state['output_dir'], new_output_dir)
                state['output_dir'] = new_output_dir
            except Exception as e:
                print(f"[WARNING] Could not rename folder: {e}")
    
    if not is_error:
        msg = f"Directory finalized and stored in state: {state['output_dir']}"
        print(f"\n[SYSTEM] {msg}")
        pipeline_messenger.send("log", msg)

    return {
        "job_details": job_details, 
        "output_dir": state['output_dir'], 
        "total_cost": state.get('total_cost', 0.0) + cost, 
        "messages": [f"Job Reader: {'Failed' if is_error else 'Processed'}."],
        "next_step": "END" if is_error else "company_researcher"
    }

def check_reader_success(state: AgentState):
    if state.get("next_step") == "END":
        return "END"
    return "company_researcher"

def company_researcher_node(state: AgentState):
    msg = "--- Company Researcher: Researching ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Company Researcher", "activity": "Researching company details and culture..."})
    agent = get_company_researcher_agent()
    chat = agent.start_chat(enable_automatic_function_calling=False)
    
    prompt = f"Research this company based on the following job details:\n\n{state['job_details']}"
    response = chat.send_message(prompt)
    
    # Log usage
    cost = 0.0
    if response.usage_metadata:
        cost = log_token_usage("Company Researcher", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="flash-lite")

    company_info = get_response_text(response)
    pipeline_messenger.send("agent_activity", {"stage": "Company Researcher", "activity": company_info})
    with open(os.path.join(state['output_dir'], "company_info.txt"), "w", encoding="utf-8") as f:
        f.write(company_info)
    return {"company_info": company_info, "output_dir": state['output_dir'], "total_cost": state.get('total_cost', 0.0) + cost, "messages": ["Company Researcher: Gathered research."]}

from agents.android_tailor.skills.cv_tools import save_and_compile_latex

def android_tailor_node(state: AgentState):
    msg = "--- Android Tailor: Tailoring AndroidCV ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "CV Tailor (Android)", "activity": "Tailoring Android CV for the job..."})
    
    # Pre-read required files
    facts = read_workspace_file(FACTS_FILE)
    template = read_workspace_file(TEMPLATE_NAME)
    
    agent = get_android_tailor_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    company_name = "Company"
    try:
        clean_jd = state['job_details'].strip('`').strip('json').strip()
        jd_json = json.loads(clean_jd)
        company_name = jd_json.get("Company Name") or jd_json.get("company_name") or "Company"
    except: pass

    prompt = f"""
    TASK: Tailor the provided LaTeX CV template for {company_name}.
    
    MY CAREER FACTS:
    {facts}
    
    JOB DESCRIPTION:
    {state['job_details']}
    
    COMPANY RESEARCH:
    {state['company_info']}
    
    LATEX TEMPLATE TO EDIT:
    {template}
    
    INSTRUCTIONS:
    1. Update the CV content to highlight skills and experience relevant to this job.
    2. Keep the LaTeX structure intact.
    3. Return the COMPLETE updated LaTeX code.
    4. Call the save_and_compile_latex tool ONCE.
       REQUIRED ARGUMENTS:
       - latex_content: (The tailored code)
       - company_name: "{company_name}"
       - target_dir: r"{state['output_dir']}"
    """
    
    # Retry loop for malformed function calls or text-only responses
    status = ""
    current_node_cost = 0.0
    for attempt in range(2):
        try:
            response = chat.send_message(prompt)
            # Log usage
            if response.usage_metadata:
                current_node_cost = log_token_usage("Android Tailor", {
                    "prompt_token_count": response.usage_metadata.prompt_token_count,
                    "candidates_token_count": response.usage_metadata.candidates_token_count,
                    "total_token_count": response.usage_metadata.total_token_count
                }, model_type="flash-lite")
            
            status = get_response_text(response)
            
            # Fallback: only if the model returned latex in a block AND the tool wasn't already successful
            if "```latex" in status and "Success!" not in status:
                latex_code = status.split("```latex")[1].split("```")[0].strip()
                print("[SYSTEM] Tool call missing or failed, but LaTeX found in text. Compiling manually...")
                status = save_and_compile_latex(latex_code, company_name, state['output_dir'])
            
            break
        except Exception as e:
            if "MALFORMED_FUNCTION_CALL" in str(e) and attempt < 1:
                print(f"WARNING: Malformed function call. Retrying Android Tailor (Attempt {attempt + 2})...")
                continue
            status = f"Error: {str(e)}"

    print(f"[SYSTEM] {status}")
    
    # Fallback Mechanism: If compilation failed, copy and compile the original template
    if "Success!" not in status:
        msg = f"[FALLBACK] Tailoring failed. Copying original {TEMPLATE_NAME} as fallback..."
        print(msg)
        pipeline_messenger.send("log", msg)
        try:
            orig_path = os.path.join(CV_WORKSPACE, TEMPLATE_NAME)
            with open(orig_path, "r", encoding="utf-8") as f:
                orig_content = f.read()
            status = save_and_compile_latex(orig_content, f"{company_name}_Original", state['output_dir'])
            msg = f"[FALLBACK] Original CV status: {status}"
            print(msg)
            pipeline_messenger.send("log", msg)
        except Exception as e:
            print(f"[ERROR] Fallback failed: {e}")

    pipeline_messenger.send("agent_activity", {"stage": "CV Tailor (Android)", "activity": status})
    return {"compilation_status": status, "output_dir": state['output_dir'], "total_cost": state.get('total_cost', 0.0) + current_node_cost, "messages": ["Android Tailor: Done."]}

def ml_tailor_node(state: AgentState):
    msg = "--- ML Tailor: Tailoring MLCV ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "CV Tailor (ML)", "activity": "Tailoring ML CV for the job..."})
    
    # Pre-read required files
    facts = read_workspace_file(FACTS_FILE)
    template = read_workspace_file(ML_TEMPLATE_NAME)

    agent = get_ml_tailor_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    company_name = "Company"
    try:
        clean_jd = state['job_details'].strip('`').strip('json').strip()
        jd_json = json.loads(clean_jd)
        company_name = jd_json.get("Company Name") or jd_json.get("company_name") or "Company"
    except: pass

    prompt = f"""
    TASK: Tailor the provided ML LaTeX CV template for {company_name}.
    
    MY CAREER FACTS:
    {facts}
    
    JOB DESCRIPTION:
    {state['job_details']}
    
    COMPANY RESEARCH:
    {state['company_info']}
    
    LATEX TEMPLATE TO EDIT:
    {template}
    
    INSTRUCTIONS:
    1. Focus on Machine Learning and Data Science experience relevant to the JD.
    2. Keep the LaTeX structure intact.
    3. Return the COMPLETE updated LaTeX code.
    4. Call the save_and_compile_latex tool ONCE.
       REQUIRED ARGUMENTS:
       - latex_content: (The tailored code)
       - company_name: "{company_name}"
       - target_dir: r"{state['output_dir']}"
    """
    
    # Retry loop for malformed function calls or text-only responses
    status = ""
    current_node_cost = 0.0
    for attempt in range(2):
        try:
            response = chat.send_message(prompt)
            # Log usage
            if response.usage_metadata:
                current_node_cost = log_token_usage("ML Tailor", {
                    "prompt_token_count": response.usage_metadata.prompt_token_count,
                    "candidates_token_count": response.usage_metadata.candidates_token_count,
                    "total_token_count": response.usage_metadata.total_token_count
                }, model_type="flash-lite")
            
            status = get_response_text(response)
            
            # Fallback: only if the model returned latex in a block AND the tool wasn't already successful
            if "```latex" in status and "Success!" not in status:
                latex_code = status.split("```latex")[1].split("```")[0].strip()
                print("[SYSTEM] Tool call missing or failed, but LaTeX found in text. Compiling manually...")
                status = save_and_compile_latex(latex_code, company_name, state['output_dir'])
            
            break
        except Exception as e:
            if "MALFORMED_FUNCTION_CALL" in str(e) and attempt < 1:
                print(f"WARNING: Malformed function call. Retrying ML Tailor (Attempt {attempt + 2})...")
                continue
            status = f"Error: {str(e)}"

    print(f"[SYSTEM] {status}")

    # Fallback Mechanism: If compilation failed, copy and compile the original template
    if "Success!" not in status:
        msg = f"[FALLBACK] Tailoring failed. Copying original {ML_TEMPLATE_NAME} as fallback..."
        print(msg)
        pipeline_messenger.send("log", msg)
        try:
            orig_path = os.path.join(CV_WORKSPACE, ML_TEMPLATE_NAME)
            with open(orig_path, "r", encoding="utf-8") as f:
                orig_content = f.read()
            status = save_and_compile_latex(orig_content, f"{company_name}_Original", state['output_dir'])
            msg = f"[FALLBACK] Original CV status: {status}"
            print(msg)
            pipeline_messenger.send("log", msg)
        except Exception as e:
            print(f"[ERROR] Fallback failed: {e}")

    pipeline_messenger.send("agent_activity", {"stage": "CV Tailor (ML)", "activity": status})
    return {"compilation_status": status, "output_dir": state['output_dir'], "total_cost": state.get('total_cost', 0.0) + current_node_cost, "messages": ["ML Tailor: Done."]}






from agents.coverletter_tailor.skills.coverletter_tools import save_coverletter_outputs

def coverletter_tailor_node(state: AgentState):
    msg = "--- Cover Letter Tailor: Tailoring Cover Letter ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Cover Letter Tailor", "activity": "Generating tailored cover letter..."})
    
    # Pre-read required files
    facts = read_workspace_file(FACTS_FILE)
    template = read_workspace_file(COVERLETTER_TEMPLATE)

    agent = get_coverletter_tailor_agent()
    chat = agent.start_chat(enable_automatic_function_calling=False)
    
    company_name = "Company"
    if state['job_details']:
        try:
            json_clean = state['job_details'].strip('`').strip()
            if json_clean.startswith('json'): json_clean = json_clean[4:].strip()
            jd_json = json.loads(json_clean)
            company_name = jd_json.get("Company Name") or jd_json.get("company_name") or "Company"
        except: pass
    
    prompt = f"""
    TASK: Write a tailored cover letter for {company_name}.
    
    MY CAREER FACTS:
    {facts}
    
    BASE COVER LETTER TEMPLATE:
    {template}
    
    JOB DESCRIPTION (JSON):
    {state['job_details']}
    
    COMPANY RESEARCH:
    {state['company_info']}
    
    INSTRUCTIONS:
    1. Write a professional, high-impact cover letter.
    2. Use the read facts to match my experience to their requirements.
    3. Return ONLY the COMPLETE tailored cover letter text. Do not include markdown blocks or conversational text.
    """
    
    response = chat.send_message(prompt)

    # Log usage
    cost = 0.0
    if response.usage_metadata:
        cost = log_token_usage("Cover Letter Tailor", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="flash-lite")

    cover_letter_text = get_response_text(response).strip()
    
    # Manually save the cover letter
    try:
        if cover_letter_text:
            status_msg = save_coverletter_outputs(cover_letter_text, state['output_dir'], company_name)
        else:
            status_msg = "Cover Letter Tailor failed to generate text."
    except Exception as e:
        status_msg = f"Error saving cover letter: {str(e)}"
        
    print(f"[SYSTEM] {status_msg}")

    pipeline_messenger.send("agent_activity", {"stage": "Cover Letter Tailor", "activity": status_msg})

    tailored_msg = f"\n--- TAILORED COVER LETTER ---\n{cover_letter_text}\n---------------------------\n"
    pipeline_messenger.send("log", tailored_msg)
    
    return {"messages": ["Cover Letter Tailor: Generated .txt and .pdf."], "output_dir": state['output_dir'], "total_cost": state.get('total_cost', 0.0) + cost}

def job_tracker_node(state: AgentState):
    msg = "--- Job Tracker: Updating Record ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Job Tracker", "activity": "Updating job application tracker..."})
    
    agent = get_job_tracker_agent()
    url_hash = get_url_hash(state['job_url'])
    
    # Force the agent to focus on the task
    prompt = f"""
    ACTION REQUIRED: Call the update_job_tracker_table tool.
    
    Job Details: {state['job_details']}
    Output Folder: {state['output_dir']}
    URL Hash: {url_hash}
    
    Extract the company name, role, and other details from the JSON and log them.
    Identify any apply links in the job details.
    Set the status to 'ready to submit'.
    """
    
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(prompt)

    # Log usage
    cost = 0.0
    if response.usage_metadata:
        cost = log_token_usage("Job Tracker", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="flash-lite")

    pipeline_messenger.send("agent_activity", {"stage": "Complete", "activity": "Job evaluation finished successfully."})
    return {"messages": ["Job Tracker: Update tool called."], "next_step": END, "output_dir": state['output_dir'], "total_cost": state.get('total_cost', 0.0) + cost}

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

# Only proceed if reader succeeded
workflow.add_conditional_edges(
    "job_reader",
    check_reader_success,
    {
        "company_researcher": "company_researcher",
        "END": END
    }
)

workflow.add_edge("company_researcher", "company_researcher_end_node") # Dummy or logic below

# Redefine routing logic slightly for clarity
def route_research_to_tailor(state: AgentState):
    details = state['job_details'].lower()
    # Check if job_details is just an error message
    if len(details) < 200 and ("error" in details or "could not" in details):
        print("[SYSTEM] Stopping pipeline: Job description is invalid or missing.")
        return "END"
        
    ml_keywords = ["machine learning", "ml ", "artificial intelligence", "ai ", "data science", "nlp", "computer vision"]
    if any(kw in details for kw in ml_keywords):
        return "ml_tailor"
    return "android_tailor"

# Clean up workflow edges
workflow = StateGraph(AgentState)
workflow.add_node("job_reader", job_reader_node)
workflow.add_node("company_researcher", company_researcher_node)
workflow.add_node("android_tailor", android_tailor_node)
workflow.add_node("ml_tailor", ml_tailor_node)
workflow.add_node("coverletter_tailor", coverletter_tailor_node)
workflow.add_node("job_tracker", job_tracker_node)

workflow.set_entry_point("job_reader")
workflow.add_conditional_edges("job_reader", check_reader_success, {"company_researcher": "company_researcher", "END": END})
workflow.add_conditional_edges(
    "company_researcher",
    route_research_to_tailor,
    {
        "ml_tailor": "ml_tailor",
        "android_tailor": "android_tailor",
        "END": END
    }
)
workflow.add_edge("android_tailor", "coverletter_tailor")
workflow.add_edge("ml_tailor", "coverletter_tailor")
workflow.add_edge("coverletter_tailor", "job_tracker")
workflow.add_edge("job_tracker", END)

app = workflow.compile()

def find_existing_job(url: str):
    """Checks all evaluated jobs to see if this URL was already processed."""
    if not os.path.exists(JOBS_EVALUATED_DIR):
        return None
    
    for folder in os.listdir(JOBS_EVALUATED_DIR):
        folder_path = os.path.join(JOBS_EVALUATED_DIR, folder)
        jd_path = os.path.join(folder_path, "job_description.txt")
        if os.path.exists(jd_path):
            with open(jd_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple check for the URL in the JD file
                if url in content:
                    return folder_path
    return None

def run_job_application_pipeline(url: str):
    # Check if job already exists
    existing_path = find_existing_job(url)
    if existing_path:
        msg = f"SKIPPING: Job already processed in {os.path.basename(existing_path)}"
        print(f"\n[SYSTEM] {msg}")
        pipeline_messenger.send("log", msg)
        pipeline_messenger.send("agent_activity", {"stage": "Complete", "activity": msg})
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    url_hash = get_url_hash(url)
    # Initial directory using hash to maintain consistency
    output_dir = os.path.join(JOBS_EVALUATED_DIR, f"Processing_{url_hash}")
    os.makedirs(output_dir, exist_ok=True)
    initial_state = {
        "job_url": url, "messages": [], "job_details": None, "company_info": None,
        "compilation_status": None, "next_step": "job_reader", "output_dir": output_dir,
        "timestamp": timestamp, "total_cost": 0.0
    }
    
    final_cost = 0.0
    for output in app.stream(initial_state):
        for key, value in output.items():
            if "messages" in value: print(f"--- {value['messages'][-1]} ---")
            if "total_cost" in value:
                final_cost = value["total_cost"]
    
    msg = f"Pipeline Complete! Total Run Cost: ${final_cost:.4f} CAD"
    print(f"\n{msg}")
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Complete", "activity": msg})

if __name__ == "__main__":
    print("\n=== Gemini Job Application Pipeline ===")
    print("Do you want to run the GUI or Terminal?")
    print("G. GUI")
    print("T. Terminal")
    mode = input("\nSelect mode (G/T): ").strip().upper()

    if mode == "G":
        try:
            from gui.app import main as run_gui
            run_gui()
        except ImportError as e:
            print(f"Error loading GUI: {e}")
            print("Falling back to Terminal mode...")
            mode = "T"
        except Exception as e:
            print(f"Failed to start GUI: {e}")
            print("Falling back to Terminal mode...")
            mode = "T"

    if mode == "T":
        print("\n--- Terminal Mode ---")
        print("1. Find jobs on datanerd.tech")
        print("2. Process a specific job URL")
        choice = input("\nSelect an option (1/2): ")
        
        if choice == "1":
            job_urls = run_job_finder()
            if job_urls:
                print(f"\nFound {len(job_urls)} jobs. Starting pipeline for each...")
                for url in job_urls:
                    print(f"\n>>> Processing: {url}")
                    try:
                        run_job_application_pipeline(url)
                    except Exception as e:
                        print(f"Error processing {url}: {e}")
            else:
                print("No jobs to process.")
        elif choice == "2":
            target_url = input("\nEnter the job URL: ")
            run_job_application_pipeline(target_url)
        else:
            print("Invalid choice.")
