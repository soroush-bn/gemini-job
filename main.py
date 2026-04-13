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
from agents.job_finder.agent import get_job_finder_agent
from agents.job_tracker.skills.token_tracker import log_token_usage
from utils.messenger import pipeline_messenger

load_dotenv()

def get_response_text(response):
    """Robustly extract text from a Gemini response, even if no text part is present."""
    try:
        if response.text:
            return response.text
    except Exception:
        pass
    
    try:
        # Check if it's a function call or other non-text part
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if hasattr(part, 'text') and part.text:
                return part.text
            if hasattr(part, 'function_call'):
                return f"[Executing Tool: {part.function_call.name}]"
            return str(part)
    except:
        pass
    return "The agent is processing or waiting for input..."

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

def job_reader_node(state: AgentState):
    msg = f"--- Job Reader: Processing {state['job_url']} ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Job Reader", "activity": f"Analyzing URL: {state['job_url']}"})
    agent = get_job_reader_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(f"Analyze this URL: {state['job_url']}")
    
    # Log usage
    if response.usage_metadata:
        log_token_usage("Job Reader", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="flash-lite")

    job_details = get_response_text(response)
    pipeline_messenger.send("agent_activity", {"stage": "Job Reader", "activity": job_details})
    
    # Parse for renaming directory
    try:
        # Robust JSON extraction
        json_str = job_details
        if "```" in json_str:
            json_str = re.split(r'```(?:json)?', json_str)[1].split('```')[0]
        
        json_clean = json_str.strip()
        jd_json = json.loads(json_clean)
        
        # Try different possible key formats
        company = jd_json.get("Company Name") or jd_json.get("company_name") or jd_json.get("Company") or "Unknown"
        role = jd_json.get("Job Title") or jd_json.get("job_title") or jd_json.get("Role") or "Unknown"
        
        # Sanitize for filesystem (remove spaces and special chars)
        def sanitize(text):
            text = text.replace(" ", "_")
            return re.sub(r'[^\w\-]', '', text)

        company = sanitize(company)
        role = sanitize(role)
        
        new_dir_name = f"{company}_{role}_{state.get('timestamp', 'now')}"
        new_output_dir = os.path.join(JOBS_EVALUATED_DIR, new_dir_name)
        
        # Perform rename
        if os.path.exists(state['output_dir']):
            os.rename(state['output_dir'], new_output_dir)
            state['output_dir'] = new_output_dir
            msg = f"Directory finalized: {new_dir_name}"
            print(f"\n[SYSTEM] {msg}")
            pipeline_messenger.send("log", msg)
    except Exception as e:
        err_msg = f"Folder rename failed: {e}. Keeping temp name."
        print(f"\n[WARNING] {err_msg}")
        pipeline_messenger.send("log", err_msg)

    # Save details in the (potentially renamed) directory
    with open(os.path.join(state['output_dir'], "job_description.txt"), "w", encoding="utf-8") as f:
        f.write(job_details)
    return {"job_details": job_details, "output_dir": state['output_dir'], "messages": ["Job Reader: Extracted requirements."]}

def company_researcher_node(state: AgentState):
    msg = "--- Company Researcher: Researching ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Company Researcher", "activity": "Researching company details and culture..."})
    agent = get_company_researcher_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(f"Research the company in these details: {state['job_details']}")
    
    # Log usage
    if response.usage_metadata:
        log_token_usage("Company Researcher", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="flash-lite")

    company_info = get_response_text(response)
    pipeline_messenger.send("agent_activity", {"stage": "Company Researcher", "activity": company_info})
    with open(os.path.join(state['output_dir'], "company_info.txt"), "w", encoding="utf-8") as f:
        f.write(company_info)
    return {"company_info": company_info, "messages": ["Company Researcher: Gathered research."]}

def android_tailor_node(state: AgentState):
    msg = "--- Android Tailor: Tailoring AndroidCV ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "CV Tailor (Android)", "activity": "Tailoring Android CV for the job..."})
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

    # Log usage
    if response.usage_metadata:
        log_token_usage("Android Tailor", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="pro")

    status = get_response_text(response)
    pipeline_messenger.send("agent_activity", {"stage": "CV Tailor (Android)", "activity": status})
    return {"compilation_status": status, "messages": ["Android Tailor: Done."]}

def ml_tailor_node(state: AgentState):
    msg = "--- ML Tailor: Tailoring MLCV ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "CV Tailor (ML)", "activity": "Tailoring ML CV for the job..."})
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

    # Log usage
    if response.usage_metadata:
        log_token_usage("ML Tailor", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="pro")

    status = get_response_text(response)
    pipeline_messenger.send("agent_activity", {"stage": "CV Tailor (ML)", "activity": status})
    return {"compilation_status": status, "messages": ["ML Tailor: Done."]}

def coverletter_tailor_node(state: AgentState):
    msg = "--- Cover Letter Tailor: Tailoring Cover Letter ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Cover Letter Tailor", "activity": "Generating tailored cover letter..."})
    agent = get_coverletter_tailor_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    company_name = "Company"
    if state['job_details']:
        try:
            json_clean = state['job_details'].strip('`').strip()
            if json_clean.startswith('json'): json_clean = json_clean[4:].strip()
            jd_json = json.loads(json_clean)
            company_name = jd_json.get("Company Name", "Company")
        except: pass
    
    prompt = f"""
    TAILOR COVER LETTER FOR: {company_name}
    
    JOB DETAILS (JSON):
    {state['job_details']}
    
    COMPANY RESEARCH:
    {state['company_info']}
    
    TARGET DIRECTORY:
    {state['output_dir']}
    
    Use the tools to read the template and facts, then save the output.
    """
    response = chat.send_message(prompt)
    
    # Log usage
    if response.usage_metadata:
        log_token_usage("Cover Letter Tailor", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="pro")

    cover_letter_text = get_response_text(response)
    pipeline_messenger.send("agent_activity", {"stage": "Cover Letter Tailor", "activity": cover_letter_text})

    tailored_msg = f"\n--- TAILORED COVER LETTER ---\n{cover_letter_text}\n---------------------------\n"
    print(tailored_msg)
    pipeline_messenger.send("log", tailored_msg)
    
    return {"messages": ["Cover Letter Tailor: Generated .txt and .pdf."]}

def job_tracker_node(state: AgentState):
    msg = "--- Job Tracker: Updating Record ---"
    print(msg)
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Job Tracker", "activity": "Updating job application tracker..."})
    
    agent = get_job_tracker_agent()
    # Force the agent to focus on the task
    prompt = f"""
    ACTION REQUIRED: Call the update_job_tracker_table tool.
    
    Job Details: {state['job_details']}
    Output Folder: {state['output_dir']}
    
    Extract the company name, role, and other details from the JSON and log them.
    Set the status to 'ready to submit'.
    """
    
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(prompt)

    # Log usage
    if response.usage_metadata:
        log_token_usage("Job Tracker", {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }, model_type="flash-lite")

    pipeline_messenger.send("agent_activity", {"stage": "Complete", "activity": "Job evaluation finished successfully."})
    return {"messages": ["Job Tracker: Update tool called."], "next_step": END}

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
    # Initial temporary directory
    output_dir = os.path.join(JOBS_EVALUATED_DIR, f"temp_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    initial_state = {
        "job_url": url, "messages": [], "job_details": None, "company_info": None,
        "compilation_status": None, "next_step": "job_reader", "output_dir": output_dir,
        "timestamp": timestamp
    }
    for output in app.stream(initial_state):
        for key, value in output.items():
            if "messages" in value: print(f"--- {value['messages'][-1]} ---")
    
    # Check if directory was renamed and print final path
    final_output_dir = output_dir
    # Note: State is not easily accessible here after stream, 
    # but we can look for the most recent directory with this timestamp
    # or just trust the print from the node.
    print(f"\nPipeline Complete!")

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
