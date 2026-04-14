from typing import TypedDict, Annotated, Sequence, Optional
import operator

class AgentState(TypedDict):
    """The shared memory (State) for our multi-agent recruiter."""
    # Conversation history
    messages: Annotated[Sequence[str], operator.add]
    # To track the next agent in line (used by Supervisor)
    next_step: str
    # Data extracted about the job
    job_details: Optional[str]
    # Data researched about the company
    company_info: Optional[str]
    # The URL to process
    job_url: str
    # Results of the CV tailoring
    compilation_status: Optional[str]
    # Result of the cover letter tailoring
    cl_status: Optional[str]
    # Unique directory for this specific job evaluation
    output_dir: Optional[str]
    # The timestamp of the run
    timestamp: Optional[str]
    # The total cost of the run in CAD
    total_cost: float
