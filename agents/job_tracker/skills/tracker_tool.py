import os
from config import TRACKER_FILE_PATH
from utils.messenger import pipeline_messenger

def update_job_tracker_table(job_name: str, company: str, role: str, date_posted: str, deadline: str, status: str, folder_path: str):
    """Appends a new job to the Markdown tracker table."""
    headers = "| Job Name | Company Name | Role | Date Posted | Deadline | Status | Path |\n"
    separator = "| --- | --- | --- | --- | --- | --- | --- |\n"
    
    # Relative path to keep the MD file portable
    base_dir = os.path.dirname(TRACKER_FILE_PATH)
    rel_path = os.path.relpath(folder_path, base_dir)
    
    new_row = f"| {job_name} | {company} | {role} | {date_posted} | {deadline} | {status} | [{rel_path}]({rel_path}) |\n"
    
    # Broadcast to GUI
    pipeline_messenger.send("job_tracked", {
        "job_name": job_name,
        "company": company,
        "role": role,
        "status": status
    })

    file_exists = os.path.exists(TRACKER_FILE_PATH)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(TRACKER_FILE_PATH), exist_ok=True)
    
    try:
        with open(TRACKER_FILE_PATH, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("# Job Application Tracker\n\n")
                f.write(headers)
                f.write(separator)
            f.write(new_row)
        return f"Success: Tracker updated for {company}."
    except Exception as e:
        return f"Error updating tracker: {str(e)}"
