import time
import os
from playwright.sync_api import sync_playwright

def save_session():
    with sync_playwright() as p:
        # Launch headed so you can type your password
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("Opening LinkedIn... Please log in manually.")
        page.goto("https://www.linkedin.com/login")
        
        # Wait for you to finish logging in (I'll give you 2 minutes)
        print("Waiting for login... Script will save session once you reach the feed or after 120s.")
        
        # We wait for the 'feed' to appear or a long timeout
        try:
            page.wait_for_url("https://www.linkedin.com/feed/", timeout=120000)
            print("Login detected!")
        except:
            print("Timeout reached or manual login completed.")

        # Save the storage state (cookies, local storage, etc.)
        context.storage_state(path="linkedin_session.json")
        print("✅ Session saved to linkedin_session.json")
        
        browser.close()

if __name__ == "__main__":
    save_session()
