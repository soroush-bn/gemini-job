import warnings
# Suppress Google SDK and Python version deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys

# Force the project root into sys.path to ensure correct imports
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

print(f"DEBUG: Running from: {os.getcwd()}")
print(f"DEBUG: Project Root: {PROJECT_ROOT}")

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from graph_state import AgentState

# Import agents
from agents.job_reader.agent import get_job_reader_agent
from agents.company_researcher.agent import get_company_researcher_agent
from agents.resume_matcher.agent import get_resume_matcher_agent

load_dotenv()

# Define nodes (Agent actions)
def job_reader_node(state: AgentState):
    print(f"--- Job Reader: Processing {state['job_url']} ---")
    agent = get_job_reader_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(f"Analyze this URL: {state['job_url']}")
    
    # Robustly handle the response
    job_details = "Failed to extract job details."
    try:
        job_details = response.text
    except Exception:
        if response.candidates and response.candidates[0].content.parts:
            # If there's no text attribute, but parts exist (like a function call result)
            job_details = str(response.candidates[0].content.parts[0])
        else:
            print(f"DEBUG: Response candidate issue. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'No candidate'}")

    print(f"\n--- EXTRACTED JOB DETAILS ---\n{job_details}\n-----------------------------\n")
    return {
        "job_details": job_details,
        "messages": [f"Job Reader: Extracted requirements for {state['job_url']}"],
        "next_step": "company_researcher"
    }

def company_researcher_node(state: AgentState):
    print(f"--- Company Researcher: Researching for details ---")
    agent = get_company_researcher_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    response = chat.send_message(f"Research the company in these job details: {state['job_details']}")
    
    company_info = "Failed to extract company research."
    try:
        company_info = response.text
    except Exception:
        if response.candidates and response.candidates[0].content.parts:
            company_info = str(response.candidates[0].content.parts[0])

    print(f"\n--- COMPANY RESEARCH ---\n{company_info}\n------------------------\n")
    return {
        "company_info": company_info,
        "messages": ["Company Researcher: Gathered culture and mission data."],
        "next_step": "resume_matcher"
    }

def resume_matcher_node(state: AgentState):
    print(f"--- Resume Matcher: Tailoring and Compiling ---")
    agent = get_resume_matcher_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    # Extract company name from job details for the filename
    company_name = "Company"
    if state['job_details']:
        import json
        try:
            # Try to parse the JSON if the model returned it that way
            jd_json = json.loads(state['job_details'].strip('`').strip('json'))
            company_name = jd_json.get("Company Name", "Company")
        except:
            pass

    prompt = f"""
    Tailor your existing CV for the position at {company_name}.
    
    JOB DETAILS: {state['job_details']}
    COMPANY INFO: {state['company_info']}
    
    STEPS:
    1. Call read_latex_template() to get the content of 'androidCV.tex'.
    2. Rewrite the LaTeX code using the EXACT structure from the template.
    3. Call save_and_compile_latex(latex_content, company_name='{company_name}') with the updated code.
    """
    response = chat.send_message(prompt)
    
    compilation_status = "Tailoring process finished, check output folder."
    try:
        compilation_status = response.text
    except Exception:
        if response.candidates and response.candidates[0].content.parts:
            compilation_status = str(response.candidates[0].content.parts[0])

    print(f"\n--- COMPILATION STATUS ---\n{compilation_status}\n--------------------------\n")
    return {
        "compilation_status": compilation_status,
        "messages": ["Resume Matcher: CV tailored and compiled."],
        "next_step": END
    }

# Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("job_reader", job_reader_node)
workflow.add_node("company_researcher", company_researcher_node)
workflow.add_node("resume_matcher", resume_matcher_node)

# Set entry point
workflow.set_entry_point("job_reader")

# Add edges (Simple linear sequence for this request)
workflow.add_edge("job_reader", "company_researcher")
workflow.add_edge("company_researcher", "resume_matcher")
workflow.add_edge("resume_matcher", END)

# Compile the app
app = workflow.compile()

def run_job_application_pipeline(url: str):
    """Executes the full pipeline for a given job URL."""
    initial_state = {
        "job_url": url,
        "messages": [],
        "job_details": None,
        "company_info": None,
        "compilation_status": None,
        "next_step": "job_reader"
    }
    
    print(f"Starting pipeline for: {url}...")
    for output in app.stream(initial_state):
        # Print progress
        for key, value in output.items():
            if "messages" in value:
                print(f"--- {value['messages'][-1]} ---")
    
    print("\nPipeline Complete!")

if __name__ == "__main__":
    # Example usage:
    run_job_application_pipeline("https://www.bestjobtool.com/job-description-ca/3095575051")
    # pass
