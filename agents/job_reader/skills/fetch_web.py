from playwright.sync_api import sync_playwright
import trafilatura

def fetch_web_content(url: str) -> str:
    """Fetches text content using a headless browser (Chromium) to bypass scraping protection."""
    try:
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Go to the URL and wait for the page to load
            print(f"DEBUG: Navigating to {url}...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            if response is None or response.status != 200:
                status = response.status if response else "No Response"
                browser.close()
                return f"Error: Could not access {url}. Status code: {status}. The site might be blocking headless browsers."
            
            # Allow dynamic content to load (optional, adjust as needed)
            page.wait_for_timeout(2000)
            
            # Get the rendered HTML
            rendered_html = page.content()
            browser.close()
            
            # Use trafilatura to extract clean text from the rendered HTML
            text = trafilatura.extract(rendered_html)
            
            if text is None:
                return f"Error: Could not extract clean text content from the rendered page at {url}."
            
            return text
            
    except Exception as e:
        return f"Error fetching URL with Playwright: {str(e)}"