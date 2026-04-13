import json
import base64
import os
import re
from playwright.sync_api import sync_playwright
from utils.messenger import pipeline_messenger
from config import TRACKER_FILE_PATH

def get_existing_urls():
    """Reads the job tracker and returns a set of already processed URLs."""
    urls = set()
    if not os.path.exists(TRACKER_FILE_PATH):
        return urls
    
    try:
        with open(TRACKER_FILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
            # Extract URLs from common job board patterns or stored paths
            # This is a bit complex as we store evaluation folder paths, 
            # but we can also store the original URL in the folder name or a sidecar file.
            # For now, let's look for evaluations that exist.
            # Better approach: check the names of folders in jobs_evaluated
            eval_dir = os.path.join(os.path.dirname(os.path.dirname(TRACKER_FILE_PATH)), "jobs_evaluated")
            if os.path.exists(eval_dir):
                for folder in os.listdir(eval_dir):
                    # We can't easily map folder names back to URLs without a database,
                    # but we can check if the folder exists.
                    pass
            
            # Since we don't store the original URL in the tracker table yet, 
            # I will add a step to check if the job evaluation folder already exists
            # based on company and role later in the pipeline.
            # FOR NOW: Let's extract URLs from the tracker file text if any are there.
            found_urls = re.findall(r'https?://[^\s|)\n]+', content)
            urls.update(found_urls)
    except: pass
    return urls

def search_datanerd_jobs(role: str, country: str, work_type: str = "any") -> str:
    """Searches datanerd.tech for jobs using Playwright.
    Targets the .space-y-3 container for scrolling and skips duplicates."""
    existing_urls = get_existing_urls()
    formatted_role = role.replace(" ", "+")
    formatted_country = country.replace(" ", "+")
    url = f"https://datanerd.tech/jobs?title={formatted_role}&country={formatted_country}"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()
            
            pipeline_messenger.send("log", f"Navigating to {url}...")
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Take initial screenshot
            screenshot = page.screenshot(type='jpeg', quality=50)
            encoded = base64.b64encode(screenshot).decode('utf-8')
            pipeline_messenger.send("screenshot", {"data": encoded})

            # Target the left scrollable div
            # The user specified class 'space-y-3'
            scroll_container_selector = ".space-y-3"
            
            pipeline_messenger.send("log", "Scrolling the job list container...")
            
            for i in range(5):
                # Attempt to scroll the specific container
                try:
                    page.evaluate(f"""
                        (selector) => {{
                            const el = document.querySelector(selector);
                            if (el) el.scrollBy(0, 800);
                        }}
                    """, scroll_container_selector)
                except:
                    # Fallback to general scroll if container not found
                    page.mouse.wheel(0, 800)
                
                page.wait_for_timeout(1000)
                
                # Update screenshot
                screenshot = page.screenshot(type='jpeg', quality=30)
                encoded = base64.b64encode(screenshot).decode('utf-8')
                pipeline_messenger.send("screenshot", {"data": encoded})
                pipeline_messenger.send("log", f"Scroll pass {i+1} complete.")

            # Extract links
            links = page.query_selector_all("a")
            job_urls = []
            seen_hrefs = set()
            
            job_board_keywords = ["indeed.com", "linkedin.com", "workingnomads.com", "apply.workable.com", "lever.co", "greenhouse.io"]
            
            for link in links:
                href = link.get_attribute("href")
                if not href: continue
                
                full_url = href
                if href.startswith("/"):
                    full_url = f"https://datanerd.tech{href}"
                
                # 1. Skip if already seen in this session
                if full_url in seen_hrefs: continue
                
                # 2. Skip if already in Tracker
                if full_url in existing_urls:
                    pipeline_messenger.send("log", f"Skipping already tracked job: {full_url}")
                    continue

                is_job_link = False
                if "/jobs/info/" in full_url:
                    is_job_link = True
                elif any(kw in full_url for kw in job_board_keywords):
                    is_job_link = True
                
                if is_job_link:
                    seen_hrefs.add(full_url)
                    job_urls.append(full_url)
                    if len(job_urls) >= 15:
                        break
            
            browser.close()
            
            if not job_urls:
                return "No new jobs found."
            
            pipeline_messenger.send("log", f"Found {len(job_urls)} NEW job links.")
            return json.dumps(job_urls)
            
    except Exception as e:
        error_msg = f"Error scraping datanerd.tech: {str(e)}"
        pipeline_messenger.send("log", error_msg)
        return error_msg
