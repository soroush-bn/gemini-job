import os
import re
import json
import hashlib
from config import JOBS_EVALUATED_DIR

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

def get_url_hash(url: str):
    """Generates a short 8-character hash of the URL."""
    return hashlib.md5(url.encode()).hexdigest()[:8]

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

def sanitize_for_filesystem(text):
    """Sanitizes strings for use as directory/file names."""
    text = text.replace(" ", "_")
    return re.sub(r'[^\w\-]', '', text)
