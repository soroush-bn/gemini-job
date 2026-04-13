from playwright.sync_api import sync_playwright
import json

def search_datanerd_jobs(role: str, country: str, work_type: str = "any") -> str:
    """Searches datanerd.tech for jobs matching the role and country."""
    # Construct the base URL
    # Format: https://datanerd.tech/jobs?title=Data+Scientist&country=United+States
    formatted_role = role.replace(" ", "+")
    formatted_country = country.replace(" ", "+")
    url = f"https://datanerd.tech/jobs?title={formatted_role}&country={formatted_country}"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            print(f"DEBUG: Searching datanerd.tech: {url}...")
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait and Scroll to load more jobs
            print("DEBUG: Scrolling to load more content...")
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 800)")
                page.wait_for_timeout(1000)
            
            # Additional wait for lazy loading
            page.wait_for_timeout(2000) 
            
            # Check for body text to see if we are being blocked or if the page is empty
            body_text = page.inner_text("body")
            print(f"DEBUG: Body length: {len(body_text)}")
            
            # Extract links
            all_links = page.query_selector_all("a")
            
            job_urls = []
            seen_hrefs = set()
            
            # Keywords that often indicate a job board link
            job_board_keywords = ["indeed.com", "linkedin.com", "workingnomads.com", "apply.workable.com", "lever.co", "greenhouse.io"]
            
            for link in all_links:
                href = link.get_attribute("href")
                if not href:
                    continue
                
                # Normalize and filter
                is_job_link = False
                if href.startswith("/jobs/info/"):
                    full_url = f"https://datanerd.tech{href}"
                    is_job_link = True
                elif any(kw in href for kw in job_board_keywords):
                    full_url = href
                    is_job_link = True
                
                if is_job_link and full_url not in seen_hrefs:
                    seen_hrefs.add(full_url)
                    job_urls.append(full_url)
                    if len(job_urls) >= 15:
                        break
            
            browser.close()
            
            if not job_urls:
                return "No jobs found for the specified criteria."
            
            return json.dumps(job_urls)
            
    except Exception as e:
        return f"Error scraping datanerd.tech: {str(e)}"
