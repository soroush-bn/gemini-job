import os
import json
import google.generativeai as genai
from .prompt import JOB_APPLY_PROMPT
from .skills.apply_tools import get_ready_jobs, fill_application_form, update_tracker_status
from utils.messenger import pipeline_messenger
from config import MODEL_NAME
def get_apply_agent():
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        tools=[get_ready_jobs, fill_application_form, update_tracker_status],
        system_instruction=JOB_APPLY_PROMPT
    )

def run_apply_pipeline():
    """Main entry point for the Apply Agent to process all ready jobs."""
    pipeline_messenger.send("log", "--- Starting Apply Agent ---")
    pipeline_messenger.send("agent_activity", {"stage": "Apply Agent", "activity": "Finding jobs ready for submission..."})
    
    # 1. Load User Profile
    profile_path = "user_profile.json"
    if not os.path.exists(profile_path):
        pipeline_messenger.send("log", "Error: user_profile.json not found.")
        return
    
    with open(profile_path, "r", encoding="utf-8") as f:
        user_info = json.load(f)
    
    # 2. Get Ready Jobs
    ready_jobs = get_ready_jobs()
    if not ready_jobs:
        pipeline_messenger.send("log", "No jobs ready for submission found in tracker.")
        return
    
    pipeline_messenger.send("log", f"Found {len(ready_jobs)} jobs ready to apply.")
    
    # 3. Process each job
    agent = get_apply_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    for job in ready_jobs:
        msg = f"Applying for {job['job_name']} at {job['company']}..."
        pipeline_messenger.send("log", msg)
        pipeline_messenger.send("agent_activity", {"stage": "Apply Agent", "activity": msg})
        
        # We need the application URL from job_description.txt
        jd_path = os.path.join(job['path'], "job_description.txt")
        if not os.path.exists(jd_path):
            pipeline_messenger.send("log", f"Warning: job_description.txt not found for {job['company']}")
            continue
            
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_text = f.read()
        
        # Find CV and Cover Letter
        cv_path = None
        for f in os.listdir(job['path']):
            if f.endswith(".pdf") and ("CV" in f or "Resume" in f or "tailored" in f):
                cv_path = os.path.join(job['path'], f)
                break
        
        cl_path = None
        for f in os.listdir(job['path']):
            if f.endswith(".pdf") and ("Cover" in f or "Letter" in f):
                cl_path = os.path.join(job['path'], f)
                break
        
        # Trigger the agent to handle this specific job
        # We'll pass the info to the chat
        prompt = f"Apply for this job:\nCompany: {job['company']}\nRole: {job['role']}\nJD Context: {jd_text[:1000]}...\nCV Path: {cv_path}\nCover Letter Path: {cl_path}\nUser Info: {json.dumps(user_info)}"
        
        response = chat.send_message(prompt)
        # The agent will use fill_application_form automatically via function calling
        
        pipeline_messenger.send("log", f"Agent response for {job['company']}: {response.text}")
        
        # After the user closes the browser (signaled by fill_application_form returning),
        # we ask for status update.
        # Note: In this simple implementation, we assume the user submitted it if they didn't cancel.
        # A more robust way would be to ask the user via GUI.
        
    pipeline_messenger.send("log", "--- Apply Agent Pipeline Finished ---")
    pipeline_messenger.send("agent_activity", {"stage": "Apply Agent", "activity": "All ready jobs processed."})
