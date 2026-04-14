import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Setup Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

load_dotenv()

# Workflow and Utilities
from workflow.builder import build_workflow
from utils.helpers import get_url_hash, find_existing_job, get_response_text
from utils.messenger import pipeline_messenger
from config import JOBS_EVALUATED_DIR

# Agents
from agents.job_finder.agent import get_job_finder_agent

# Initialize Workflow (Supervisor-Worker Graph)
app = build_workflow()

def run_job_finder(input_func=input, initial_query=None):
    """Interactively finds jobs and returns a list of URLs."""
    msg = "--- Starting Job Finder Agent ---"
    print(f"\n{msg}")
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Job Finder", "activity": "Searching for jobs..."})
    
    agent = get_job_finder_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    user_msg = initial_query if initial_query else "Hello! I want to find some jobs."
    
    while True:
        if not user_msg or not user_msg.strip():
            user_msg = "Please continue or provide more instructions."

        try:
            response = chat.send_message(user_msg)
            text = get_response_text(response)
            print(f"\nAgent: {text}")
            pipeline_messenger.send("agent_chat", {"role": "agent", "content": text})
            
            if "```json" in text:
                try:
                    json_str = text.split("```json")[1].split("```")[0].strip()
                    urls = json.loads(json_str)
                    if isinstance(urls, list) and len(urls) > 0:
                        return urls
                except: pass
        except Exception as e:
            print(f"AI Communication Error: {e}")
            return None
        
        user_msg = input_func("\nYou: ")
        if user_msg is None: return None
        pipeline_messenger.send("agent_chat", {"role": "user", "content": user_msg})

def run_job_application_pipeline(url: str):
    """Executes the Supervisor-led application pipeline."""
    existing_path = find_existing_job(url)
    if existing_path:
        msg = f"SKIPPING: Job already processed in {os.path.basename(existing_path)}"
        print(f"\n[SYSTEM] {msg}")
        pipeline_messenger.send("log", msg)
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    url_hash = get_url_hash(url)
    output_dir = os.path.join(JOBS_EVALUATED_DIR, f"Processing_{url_hash}")
    os.makedirs(output_dir, exist_ok=True)
    
    initial_state = {
        "job_url": url, 
        "messages": [], 
        "job_details": None, 
        "company_info": None,
        "compilation_status": None, 
        "cl_status": None,
        "next_step": "supervisor", 
        "output_dir": output_dir,
        "timestamp": timestamp, 
        "total_cost": 0.0
    }
    
    final_cost = 0.0
    # Stream the graph execution
    for output in app.stream(initial_state):
        for key, value in output.items():
            if "total_cost" in value:
                final_cost = value["total_cost"]
    
    msg = f"Pipeline Complete! Total Cost: ${final_cost:.4f} CAD"
    print(f"\n{msg}")
    pipeline_messenger.send("log", msg)
    pipeline_messenger.send("agent_activity", {"stage": "Complete", "activity": msg})

if __name__ == "__main__":
    print("\n=== Gemini Job Application Pipeline (Supervisor Model) ===")
    print("G. GUI")
    print("T. Terminal")
    mode = input("\nSelect mode (G/T): ").strip().upper()

    if mode == "G":
        try:
            from gui.app import main as run_gui
            run_gui()
        except Exception as e:
            print(f"Failed to start GUI: {e}")
            mode = "T"

    if mode == "T":
        print("\n--- Terminal Mode ---")
        print("1. Find jobs")
        print("2. Process specific URL")
        choice = input("\nSelect an option (1/2): ")
        
        if choice == "1":
            job_urls = run_job_finder()
            if job_urls:
                for url in job_urls:
                    run_job_application_pipeline(url)
        elif choice == "2":
            target_url = input("\nEnter the job URL: ")
            run_job_application_pipeline(target_url)
