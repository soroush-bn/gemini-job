from langgraph.graph import StateGraph, END
from graph_state import AgentState
from .nodes import (
    supervisor_node,
    job_reader_node, 
    company_researcher_node, 
    cv_tailor_node,
    coverletter_tailor_node, 
    job_tracker_node
)

def build_workflow():
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("job_reader", job_reader_node)
    workflow.add_node("company_researcher", company_researcher_node)
    workflow.add_node("cv_tailor", cv_tailor_node)
    workflow.add_node("coverletter_tailor", coverletter_tailor_node)
    workflow.add_node("job_tracker", job_tracker_node)

    # Set Entry Point
    workflow.set_entry_point("supervisor")

    # The Supervisor is the router
    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x["next_step"],
        {
            "job_reader": "job_reader",
            "company_researcher": "company_researcher",
            "cv_tailor": "cv_tailor",
            "coverletter_tailor": "coverletter_tailor",
            "job_tracker": "job_tracker"
        }
    )

    # Every worker returns to the supervisor
    workflow.add_edge("job_reader", "supervisor")
    workflow.add_edge("company_researcher", "supervisor")
    workflow.add_edge("cv_tailor", "supervisor")
    workflow.add_edge("coverletter_tailor", "supervisor")
    
    # Job Tracker is the final step
    workflow.add_edge("job_tracker", END)

    return workflow.compile()
