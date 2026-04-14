import os
import re
import time
import json
from playwright.sync_api import sync_playwright
from config import JOBS_EVALUATED_DIR, TRACKER_FILE_PATH
from utils.messenger import pipeline_messenger

def find_local_job_folder(url):
    """Find the local folder for a job based on the URL in job_description.txt"""
    if not os.path.exists(JOBS_EVALUATED_DIR):
        return None
    
    for folder in os.listdir(JOBS_EVALUATED_DIR):
        folder_path = os.path.join(JOBS_EVALUATED_DIR, folder)
        jd_file = os.path.join(folder_path, "job_description.txt")
        if os.path.exists(jd_file):
            with open(jd_file, "r", encoding="utf-8") as f:
                if url in f.read():
                    return folder_path
    return None

def get_tailored_files(folder_path):
    """Find the PDF CV and Cover Letter in the folder."""
    files = {"cv": None, "cl": None}
    for file in os.listdir(folder_path):
        if file.endswith(".pdf") and "CV" in file:
            files["cv"] = os.path.abspath(os.path.join(folder_path, file))
        if file.endswith(".pdf") and "Cover_Letter" in file:
            files["cl"] = os.path.abspath(os.path.join(folder_path, file))
        # Fallback for .txt cover letter if pdf doesn't exist
        if not files["cl"] and "coverletter" in file.lower() and file.endswith(".txt"):
            files["cl"] = os.path.abspath(os.path.join(folder_path, file))
    return files

def run_automated_upload(url):
    """Main function to navigate and upload files."""
    folder_path = find_local_job_folder(url)
    if not folder_path:
        print(f"Error: No tailored folder found for URL: {url}")
        return

    tailored_files = get_tailored_files(folder_path)
    if not tailored_files["cv"]:
        print(f"Error: No CV PDF found in {folder_path}")
        return

    print(f"Starting automated upload for: {os.path.basename(folder_path)}")
    
    with sync_playwright() as p:
        # Launch browser in headed mode
        browser = p.chromium.launch(headless=False)
        
        # Load session if it exists
        session_file = "linkedin_session.json"
        if os.path.exists(session_file):
            print(f"Loading session from {session_file}...")
            context = browser.new_context(storage_state=session_file)
        else:
            print("No saved session found. Running in clean mode.")
            context = browser.new_context()
            
        page = context.new_page()
        
        print(f"Navigating to: {url}")
        page.goto(url)
        
        # Wait for user to navigate to the actual application form if the URL is just a JD
        print("Please navigate to the application form page if not already there.")
        print("The script will now scan for upload buttons...")
        
        # Give some time for the page to load or user to click 'Apply'
        time.sleep(5)

        # 1. Look for Resume/CV Upload
        resume_selectors = [
            "input[type='file']",
            "input[name*='resume']",
            "input[name*='cv']",
            "input[id*='resume']",
            "input[id*='cv']",
            "input[aria-label*='resume']"
        ]
        
        # 2. Look for Cover Letter Upload
        cl_selectors = [
            "input[name*='cover']",
            "input[id*='cover']",
            "input[aria-label*='cover']"
        ]

        # Try to find and upload Resume
        found_resume = False
        inputs = page.query_selector_all("input[type='file']")
        for input_el in inputs:
            # Check context around the input
            parent_text = input_el.evaluate("el => el.parentElement.innerText").lower()
            name = (input_el.get_attribute("name") or "").lower()
            id_val = (input_el.get_attribute("id") or "").lower()
            
            context_text = f"{parent_text} {name} {id_val}"
            
            if "resume" in context_text or "cv" in context_text or "curriculum" in context_text:
                print(f"Found Resume Upload: {id_val}")
                input_el.set_input_files(tailored_files["cv"])
                found_resume = True
                time.sleep(1)
            
            elif "cover" in context_text and tailored_files["cl"]:
                print(f"Found Cover Letter Upload: {id_val}")
                input_el.set_input_files(tailored_files["cl"])
                time.sleep(1)

        if not found_resume:
            print("Could not automatically detect the resume upload field. Please upload manually.")

        print("\nUpload attempts complete. The browser will stay open for 60 seconds for you to finish the form.")
        time.sleep(60)
        browser.close()

if __name__ == "__main__":
    target_url = input("Enter the Job URL to apply for: ")
    run_automated_upload(target_url)
