#!/usr/bin/env python
"""
LinkedIn Cookie Refresher

This script helps manage LinkedIn cookies for the scraper.
It checks the status of existing cookies and provides instructions for refreshing them.
It can also launch a browser to help you refresh cookies.
"""

import os
import json
import time
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Import selenium components if available
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium not available. Some features will be disabled.")


def check_cookie_status(cookie_path="cookies.json"):
    """Check the status of LinkedIn cookies
    
    Args:
        cookie_path (str): Path to the cookies.json file
        
    Returns:
        dict: Status information about the cookies
    """
    status = {
        "exists": False,
        "age_hours": None,
        "cookie_count": 0,
        "valid": False,
        "li_at_present": False,
        "message": ""
    }
    
    # Check if file exists
    if not os.path.exists(cookie_path):
        status["message"] = f"Cookie file not found at {cookie_path}"
        return status
    
    status["exists"] = True
    
    # Check cookie age
    mod_time = os.path.getmtime(cookie_path)
    age_seconds = time.time() - mod_time
    status["age_hours"] = age_seconds / 3600
    
    # Format last modified time
    last_modified = datetime.fromtimestamp(mod_time)
    status["last_modified"] = last_modified.strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate expiration time (estimate 2 hours from creation)
    expiration = last_modified + timedelta(hours=2)
    status["estimated_expiration"] = expiration.strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if expired
    status["expired"] = datetime.now() > expiration
    
    # Read cookie file
    try:
        with open(cookie_path, 'r') as f:
            cookies = json.load(f)
            
        status["cookie_count"] = len(cookies)
        
        # Check for critical LinkedIn cookies
        for cookie in cookies:
            if cookie.get("name") == "li_at":
                status["li_at_present"] = True
                break
                
        # Determine if likely valid
        status["valid"] = status["li_at_present"] and not status["expired"]
        
        if status["valid"]:
            status["message"] = "Cookies appear valid"
        elif not status["li_at_present"]:
            status["message"] = "Critical LinkedIn authentication cookie 'li_at' is missing"
        elif status["expired"]:
            status["message"] = "Cookies are likely expired"
            
    except Exception as e:
        status["message"] = f"Error reading cookie file: {e}"
    
    return status

def print_cookie_instructions(cookie_path="cookies.json"):
    """Print instructions for refreshing LinkedIn cookies"""
    print("\nTo refresh your LinkedIn cookies, follow these steps:")
    print("1. Open Chrome and log in to LinkedIn (https://www.linkedin.com)")
    print("2. Install a cookie export extension like 'EditThisCookie' from the Chrome Web Store")
    print("3. Navigate to LinkedIn while logged in")
    print("4. Click the EditThisCookie extension icon")
    print("5. Click 'Export' to copy all cookies to clipboard")
    print(f"6. Open {cookie_path} in a text editor and replace all content with the copied cookies")
    print("7. Save the file and run your scraper again")
    print("\nNote: LinkedIn cookies typically expire after 1-2 hours when used outside the browser")
    print("For more reliable scraping, refresh cookies immediately before running the scraper")
    
    if SELENIUM_AVAILABLE:
        print("\nAlternatively, use the --interactive flag to launch a browser session:")
        print(f"  python refresh_cookies.py --interactive --output {cookie_path}")
        print("This will open a browser window where you can log in to LinkedIn")
        print("After logging in, the script will automatically save your cookies")

def extract_cookies_from_browser(output_path="cookies.json", headless=False, save_session_data=True):
    """Launch a browser session to get fresh LinkedIn cookies with enhanced anti-detection
    
    Args:
        output_path (str): Path to save cookies to
        headless (bool): Whether to run in headless mode (not recommended for LinkedIn)
        save_session_data (bool): Whether to save additional session data to extend cookie lifetime
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not SELENIUM_AVAILABLE:
        print("Error: Selenium is not installed. Cannot extract cookies from browser.")
        print("Install selenium with: pip install selenium")
        return False
    
    if headless:
        print("⚠️ Warning: Headless mode is not recommended for LinkedIn as it's easier to detect.")
        print("Consider using non-headless mode for more reliable results.")
        response = input("Continue with headless mode anyway? (y/n): ").lower()
        if response != 'y':
            headless = False
            print("Switching to non-headless mode...")
        
    print("Launching browser session to refresh LinkedIn cookies...")
    print("You will need to manually log in to LinkedIn in the browser window")
    
    # Configure browser with anti-detection measures
    options = Options()
    if headless:
        options.add_argument('--headless=new')  # Use newer headless mode if requested
        
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
    
    # Launch browser
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
        # Navigate to LinkedIn
        print("Opening LinkedIn login page...")
        driver.get("https://www.linkedin.com/login")
        
        if not headless:
            # Wait for user to log in (detect when they're on the feed page)
            print("\nPlease log in to LinkedIn in the browser window")
            print("The script will automatically continue once you're logged in")
            print("Waiting for login...")
            
            # Wait for either the feed page or the homepage after login
            WebDriverWait(driver, 300).until(
                EC.any_of(
                    EC.url_contains("linkedin.com/feed"),
                    EC.url_matches("linkedin.com/$"),
                    EC.url_contains("linkedin.com/in/"),
                    EC.presence_of_element_located((By.ID, "global-nav"))
                )
            )
        else:
            # In headless mode, we can't wait for user interaction
            print("Error: Headless mode doesn't support interactive login")
            driver.quit()
            return False
            
        # Check if we're logged in by looking for key elements
        if "Sign in" in driver.page_source or "Join now" in driver.page_source:
            print("Error: Not logged in to LinkedIn")
            driver.quit()
            return False
            
        print("Successfully logged in to LinkedIn!")
        
        # Extract cookies
        cookies = driver.get_cookies()
        
        # Create a more comprehensive session data structure
        session_data = {
            'cookies': cookies,
            'timestamp': time.time(),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_agent': driver.execute_script('return navigator.userAgent;'),
            'version': '1.1'  # Version of the session format
        }
        
        if save_session_data:
            # Extract localStorage for additional authentication context
            try:
                local_storage = driver.execute_script("""
                    var items = {};
                    for (var i = 0, len = localStorage.length; i < len; ++i) {
                        var key = localStorage.key(i);
                        var value = localStorage.getItem(key);
                        items[key] = value;
                    }
                    return items;
                """)
                session_data['local_storage'] = local_storage
                
                # Extract sessionStorage
                session_storage = driver.execute_script("""
                    var items = {};
                    for (var i = 0, len = sessionStorage.length; i < len; ++i) {
                        var key = sessionStorage.key(i);
                        var value = sessionStorage.getItem(key);
                        items[key] = value;
                    }
                    return items;
                """)
                session_data['session_storage'] = session_storage
                print("✅ Enhanced session data captured (may extend cookie lifetime)")
            except Exception as e:
                print(f"Warning: Could not extract browser storage data: {e}")
        
        # Save session data to file
        with open(output_path, 'w') as f:
            json.dump(session_data, f, indent=2)
            
        print(f"Saved enhanced session with {len(cookies)} cookies to {output_path}")
        print(f"Session creation time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Estimated expiration: {(datetime.now() + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Verify we have the critical li_at cookie
        li_at_present = any(cookie.get("name") == "li_at" for cookie in cookies)
        if li_at_present:
            print("✅ Successfully captured LinkedIn authentication cookies")
        else:
            print("⚠️ Warning: Critical 'li_at' cookie not found. Authentication may fail.")
            
        return True
        
    except Exception as e:
        print(f"Error extracting cookies: {e}")
        return False
    finally:
        # Close browser
        driver.quit()

def main():
    """Main function to check cookie status and provide guidance"""
    parser = argparse.ArgumentParser(description="LinkedIn Cookie Manager")
    parser.add_argument("--cookies", default="cookies.json", help="Path to cookies.json file")
    parser.add_argument("--output", help="Output path for cookies (defaults to --cookies value)")
    parser.add_argument("--interactive", action="store_true", help="Launch browser for interactive cookie refresh")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (not recommended)")
    
    args = parser.parse_args()
    
    # Set output path to cookies path if not specified
    if not args.output:
        args.output = args.cookies
        
    print("LinkedIn Cookie Status Checker")
    print("============================")
    
    # If interactive mode, launch browser to get fresh cookies
    if args.interactive:
        if extract_cookies_from_browser(args.output, args.headless):
            print("\nCookies have been refreshed successfully!")
            print(f"You can now use these cookies with the LinkedIn scraper:")
            print(f"  python scraper.py https://www.linkedin.com/in/username/ --cookies {args.output}")
            return
        else:
            print("\nFailed to refresh cookies interactively.")
            print_cookie_instructions(args.cookies)
            return
    
    # Find the cookies.json file if not specified
    if args.cookies == "cookies.json":
        script_dir = Path(__file__).parent.absolute()
        default_path = script_dir / "cookies.json"
        
        if os.path.exists(default_path):
            cookie_path = default_path
        else:
            # Look for cookies.json in current directory
            current_dir = Path.cwd() / "cookies.json"
            if os.path.exists(current_dir):
                cookie_path = current_dir
            else:
                cookie_path = default_path  # Use default even if it doesn't exist
        args.cookies = str(cookie_path)
    
    print(f"Checking cookies at: {args.cookies}")
    status = check_cookie_status(args.cookies)
    
    if not status["exists"]:
        print("❌ No cookies.json file found!")
        print_cookie_instructions(args.cookies)
        print("\nYou can create cookies with the --interactive flag:")
        print(f"  python refresh_cookies.py --interactive --output {args.cookies}")
        return
    
    print(f"\nLast modified: {status['last_modified']}")
    print(f"Age: {status['age_hours']:.1f} hours")
    print(f"Cookie count: {status['cookie_count']}")
    print(f"Critical auth cookie present: {'✅' if status['li_at_present'] else '❌'}")
    print(f"Estimated expiration: {status['estimated_expiration']}")
    print(f"Status: {'✅ Valid' if status['valid'] else '❌ Invalid/Expired'}")
    print(f"Message: {status['message']}")
    
    if not status["valid"]:
        print("\n⚠️ Your LinkedIn cookies need to be refreshed!")
        print("\nYou can refresh cookies with the --interactive flag:")
        print(f"  python refresh_cookies.py --interactive --output {args.cookies}")
        print_cookie_instructions(args.cookies)
    else:
        remaining_time = datetime.strptime(status["estimated_expiration"], "%Y-%m-%d %H:%M:%S") - datetime.now()
        remaining_minutes = remaining_time.total_seconds() / 60
        print(f"\n✅ Cookies appear valid for approximately {remaining_minutes:.0f} more minutes")
        print("Run your scraper soon before they expire!")

if __name__ == "__main__":
    main()
