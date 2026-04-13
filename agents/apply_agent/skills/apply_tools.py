import os
import re
import json
import time
from playwright.sync_api import sync_playwright
from config import TRACKER_FILE_PATH
from utils.messenger import pipeline_messenger

import base64

def fill_application_form(url: str, user_info: dict, cv_path: str, cover_letter_path: str = None):
    """Automates form filling on a job application page using Playwright."""
    pipeline_messenger.send("log", f"Opening application form: {url}")
    pipeline_messenger.send("agent_activity", {"stage": "Apply Agent", "activity": f"Filling form at: {url}"})
    
    try:
        with sync_playwright() as p:
            # We must use headless=False so the user can see and approve
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            def take_screenshot(label="Update"):
                try:
                    screenshot = page.screenshot(type='jpeg', quality=50)
                    encoded = base64.b64encode(screenshot).decode('utf-8')
                    pipeline_messenger.send("screenshot", {"data": encoded})
                    pipeline_messenger.send("log", f"Form Activity: {label}")
                except: pass

            take_screenshot("Initial Load")

            # Helper to find and fill fields
            def fill_field(selectors, value, field_name="Field"):
                if not value: return False
                for sel in selectors:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            el.focus()
                            el.fill(value)
                            take_screenshot(f"Filled {field_name}")
                            return True
                    except: pass
                return False

            # Name fields
            fill_field(['input[name*="first_name"]', 'input[placeholder*="First Name"]'], user_info.get("first_name", ""), "First Name")
            fill_field(['input[name*="last_name"]', 'input[placeholder*="Last Name"]'], user_info.get("last_name", ""), "Last Name")
            
            # Contact fields
            fill_field(['input[type="email"]', 'input[name*="email"]'], user_info.get("email", ""), "Email")
            fill_field(['input[type="tel"]', 'input[name*="phone"]'], user_info.get("phone", ""), "Phone")
            
            # File Uploads (CV)
            if cv_path and os.path.exists(cv_path):
                try:
                    file_input = page.query_selector('input[type="file"][name*="resume"], input[type="file"][name*="cv"]')
                    if file_input:
                        file_input.set_input_files(cv_path)
                        take_screenshot("Uploaded CV")
                except: pass

            # File Uploads (Cover Letter)
            if cover_letter_path and os.path.exists(cover_letter_path):
                try:
                    file_input = page.query_selector('input[type="file"][name*="cover_letter"], input[type="file"][name*="coverletter"]')
                    if file_input:
                        file_input.set_input_files(cover_letter_path)
                except: pass

            pipeline_messenger.send("log", "Form partially filled. PLEASE REVIEW THE BROWSER.")
            pipeline_messenger.send("agent_activity", {"stage": "Apply Agent", "activity": "Form filled where possible. PLEASE REVIEW THE BROWSER AND CLICK SUBMIT manually."})
            
            # Wait for browser to be closed by user or timeout
            # We'll keep the browser open for up to 10 minutes
            timeout = time.time() + 600
            while time.time() < timeout:
                try:
                    if not browser.is_connected() or not page or page.is_closed():
                        break
                except: break
                time.sleep(2)
            
            try: browser.close()
            except: pass
            return "Form filling session complete."
            
    except Exception as e:
        return f"Error during form filling: {str(e)}"

def get_ready_jobs():
    """Parses the job_tracker.md to find jobs with status 'ready to submit'."""
    if not os.path.exists(TRACKER_FILE_PATH):
        return []
    
    jobs = []
    with open(TRACKER_FILE_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            if "|" in line and "---" not in line and "Job Name" not in line:
                # Use robust split
                parts = [p.strip() for p in line.split("|")]
                # Table format: | EMPTY | Job Name | Company | Role | Date | Deadline | Status | Path | EMPTY |
                if len(parts) >= 8:
                    status = parts[6].lower()
                    if "ready" in status:
                        path_raw = parts[7]
                        path_match = re.search(r'\[.*\]\((.*)\)', path_raw)
                        folder_path = path_match.group(1) if path_match else path_raw
                        
                        abs_path = os.path.join(os.path.dirname(TRACKER_FILE_PATH), folder_path)
                        abs_path = os.path.normpath(abs_path)
                        
                        jobs.append({
                            "job_name": parts[1],
                            "company": parts[2],
                            "role": parts[3],
                            "status": parts[6],
                            "path": abs_path
                        })
    return jobs

def update_tracker_status(company: str, new_status: str):
    """Updates the status of a specific job in the Markdown tracker."""
    if not os.path.exists(TRACKER_FILE_PATH):
        return f"Error: Tracker file {TRACKER_FILE_PATH} not found."
    
    updated_lines = []
    found = False
    with open(TRACKER_FILE_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            if company.lower() in line.lower() and "|" in line:
                parts = line.split("|")
                if len(parts) >= 8:
                    parts[6] = f" {new_status} "
                    line = "|".join(parts)
                    found = True
            updated_lines.append(line)
    
    if found:
        with open(TRACKER_FILE_PATH, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)
        return f"Success: Tracker status updated to '{new_status}' for {company}."
    return f"Error: Job at {company} not found in tracker."
