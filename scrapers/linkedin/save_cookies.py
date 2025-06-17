#!/usr/bin/env python
"""
Save LinkedIn Cookies

This script helps you save your LinkedIn cookies to a file for use with the scraper.
You'll need to manually log in to LinkedIn when the browser opens.
"""

import json
import time
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def save_linkedin_cookies(output_path="cookies.json"):
    """Open a browser with advanced anti-detection measures, let the user log in to LinkedIn, and save the cookies"""
    print("\n=== LinkedIn Cookie Saver with Anti-Detection ===")
    print("\n1. A browser window will open with anti-detection measures enabled")
    print("2. Log in to your LinkedIn account")
    print("3. Once logged in, the cookies will be saved automatically")
    print("4. The browser will close when complete\n")
    print("Note: These cookies will typically expire after 1-2 hours when used for scraping\n")
    
    input("Press Enter to continue...")
    
    # Initialize browser with anti-detection measures
    options = Options()
    
    # Anti-detection measures
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Basic browser settings
    options.add_argument('--start-maximized')
    options.add_argument('--disable-notifications')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Set a realistic user agent
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    # Apply additional anti-detection measures
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "platform": "macOS"
    })
    
    # Execute JS to modify navigator properties to avoid detection
    driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    try:
        # Go to LinkedIn
        driver.get("https://www.linkedin.com/")
        
        # Wait for user to log in
        print("\nPlease log in to LinkedIn in the browser window...")
        
        # Wait until we detect the user is logged in
        logged_in = False
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while not logged_in and (time.time() - start_time) < max_wait_time:
            # Check if we're logged in by looking for feed or profile elements
            if ("feed" in driver.current_url or 
                "mynetwork" in driver.current_url or 
                "messaging" in driver.current_url or
                "Sign in" not in driver.page_source):
                logged_in = True
            else:
                time.sleep(2)
        
        if not logged_in:
            print("\nTimeout: Could not detect successful login.")
            return False
        
        # Get cookies
        cookies = driver.get_cookies()
        
        # Save cookies to file
        with open(output_path, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"\nSuccess! Cookies saved to {output_path}")
        print("You can now use these cookies with the LinkedIn scraper.")
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        return False
        
    finally:
        # Close browser
        driver.quit()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Save LinkedIn cookies for scraping")
    parser.add_argument("--output", default="cookies.json", help="Output file path for cookies")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    save_linkedin_cookies(args.output)
