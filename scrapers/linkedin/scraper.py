#!/usr/bin/env python
"""
LinkedIn Profile Scraper

This module extracts public information from LinkedIn profiles using Selenium
with a pre-authenticated session via cookies.
"""

import json
import time
import os
import random
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


class LinkedInScraper:
    """LinkedIn profile scraper using Selenium with cookie-based authentication"""
    
    def __init__(self, cookies_path=None, headless=True, browser_options=None, browser_type='chrome'):
        """
        Initialize the LinkedIn scraper
        
        Args:
            cookies_path (str): Path to the cookies.json file for authentication
            headless (bool): Whether to run the browser in headless mode
            browser_options: Custom browser options to use (optional)
            browser_type (str): Type of browser to use ('chrome' or 'firefox')
        """
        self.cookies_path = cookies_path
        self.headless = headless
        self.driver = None
        self.browser_options = browser_options
        self.browser_type = browser_type.lower()  # Normalize to lowercase
        self.cookie_max_age = 3600  # Maximum age of cookies in seconds (1 hour)
        self.page_load_timeout = 20  # Maximum time to wait for page load in seconds
        self.element_timeout = 5  # Maximum time to wait for elements in seconds
        
    def start_browser(self):
        """Start a new browser session with advanced stealth optimizations to avoid detection"""
        # Create browser-specific options based on browser type
        if self.browser_type == 'firefox':
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
            import shutil
            
            # Use provided options or create new Firefox options
            if self.browser_options and isinstance(self.browser_options, FirefoxOptions):
                options = self.browser_options
            else:
                options = FirefoxOptions()
                
                # Only use headless mode if explicitly requested
                if self.headless:
                    options.add_argument('--headless')
                
                # Create a Firefox profile directory if it doesn't exist
                user_home = os.path.expanduser('~')
                firefox_profile_dir = os.path.join(user_home, '.linkedin_firefox_profile')
                os.makedirs(firefox_profile_dir, exist_ok=True)
                
                # Create a Firefox profile
                firefox_profile = FirefoxProfile()
                
                # Set preferences for privacy and performance
                firefox_profile.set_preference("dom.webdriver.enabled", False)
                firefox_profile.set_preference("useAutomationExtension", False)
                firefox_profile.set_preference("privacy.trackingprotection.enabled", True)
                firefox_profile.set_preference("network.cookie.cookieBehavior", 0)  # Accept all cookies
                firefox_profile.set_preference("permissions.default.image", 1)  # Load images
                firefox_profile.set_preference("dom.ipc.plugins.enabled.npswf32.dll", False)
                firefox_profile.set_preference("media.navigator.enabled", False)
                firefox_profile.set_preference("geo.enabled", False)
                
                # Set a realistic user agent (recent MacOS Firefox)
                firefox_profile.set_preference("general.useragent.override", 
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0")
                
                # Apply the profile to options
                options.profile = firefox_profile
                
            # Create Firefox driver
            try:
                print("Starting Firefox browser...")
                self.driver = webdriver.Firefox(options=options)
                
                # Set page load timeout
                self.driver.set_page_load_timeout(self.page_load_timeout)
                
                # Set window size
                self.driver.set_window_size(1280, 800)
                
                # Use a shorter implicit wait time
                self.driver.implicitly_wait(3)
                
                # Execute JS to modify navigator properties
                self.driver.execute_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                print("Firefox browser started successfully")
            except Exception as e:
                print(f"Error starting Firefox: {e}")
                print("Falling back to Chrome...")
                self.browser_type = 'chrome'  # Fall back to Chrome
        
        # Chrome browser setup
        if self.browser_type == 'chrome':
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            
            # Use provided options or create new Chrome options
            if self.browser_options and isinstance(self.browser_options, Options):
                options = self.browser_options
            else:
                options = Options()
                
                # Only use headless mode if explicitly requested, as it's easier to detect
                if self.headless:
                    options.add_argument('--headless=new')  # Use newer headless mode
                    
                # CRITICAL: Use user data directory to leverage existing browser profile
                # This significantly improves loading speed and reduces detection
                user_home = os.path.expanduser('~')
                chrome_data_dir = os.path.join(user_home, '.linkedin_chrome_profile')
                os.makedirs(chrome_data_dir, exist_ok=True)
                options.add_argument(f'--user-data-dir={chrome_data_dir}')
                
                # Advanced anti-detection measures
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option('excludeSwitches', ['enable-automation'])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Disable automation-controlled banner
                options.add_argument('--disable-infobars')
                
                # Enhanced browser settings for performance and stealth
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-notifications')
                options.add_argument('--disable-popup-blocking')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-default-apps')
                
                # Performance optimizations
                options.add_argument('--disable-gpu')  # Reduces GPU usage
                options.add_argument('--dns-prefetch-disable')  # Reduces network fingerprinting
                
                # Use a realistic window size instead of maximized (less suspicious)
                options.add_argument('--window-size=1280,800')
                
                # Set a more realistic user agent (recent MacOS Chrome)
                options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
                
                # Enable JavaScript and cookies
                options.add_experimental_option('prefs', {
                    'profile.default_content_setting_values': {
                        'cookies': 1,  # Allow cookies
                        'javascript': 1,  # Allow JavaScript
                        'geolocation': 2,  # Block geolocation
                        'notifications': 2  # Block notifications
                    },
                    'profile.password_manager_enabled': False,
                    'credentials_enable_service': False
                })
        
        # Create the driver with enhanced error handling
        try:
            self.driver = webdriver.Chrome(options=options)
            
            # Set page load timeout to prevent hanging
            self.driver.set_page_load_timeout(self.page_load_timeout)
            
            # Execute CDP commands to avoid detection
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "platform": "macOS"
            })
            
            # Additional CDP commands to enhance stealth
            # Disable webdriver flag
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Overwrite the 'plugins' property to use a custom getter
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    
                    // Overwrite the 'languages' property to use a custom getter
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en', 'es']
                    });
                    
                    // Modify the permission state
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                '''
            })
            
            # Use a shorter implicit wait time to appear more human-like
            self.driver.implicitly_wait(3)  # Reduced from 10 seconds
        except Exception as e:
            print(f"Error initializing browser: {e}")
            raise
        
    def load_cookies(self):
        """Load cookies from file to maintain LinkedIn session with advanced anti-detection measures"""
        if not self.cookies_path or not os.path.exists(self.cookies_path):
            print("No cookies file found. You'll need to create one with save_cookies.py")
            return False
            
        # Enhanced multi-site navigation pattern to appear more natural
        # Optimized anti-detection pattern (faster, like commercial services)
        print("Implementing optimized anti-detection pattern...")
        
        # Use a minimal approach that's still effective at avoiding detection
        # Commercial services like ismyceoafraud.com likely use similar techniques
        
        # Set a convincing referrer to make it look like we came from a search engine
        # This is more efficient than actually visiting the search engine
        referrers = [
            "https://www.google.com/search?q=linkedin+profile", 
            "https://www.bing.com/search?q=linkedin+login",
            "https://duckduckgo.com/?q=linkedin"
        ]
        
        # Set a random referrer using CDP (Chrome) or directly (Firefox)
        if self.browser_type == 'chrome' and hasattr(self.driver, 'execute_cdp_cmd'):
            # Use CDP to set referrer for Chrome
            self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                'headers': {
                    'Referer': random.choice(referrers)
                }
            })
        
        # Go directly to LinkedIn with minimal delay
        print("Going directly to LinkedIn...")
        self.driver.get("https://www.linkedin.com")
        
        # Brief random delay (much shorter than before)
        time.sleep(random.uniform(0.5, 1.0))  # Just enough delay to seem human-like
        
        # Implement optimized human-like behavior simulation (faster, like commercial services)
        try:
            # Execute minimal but effective anti-detection measures
            self.driver.execute_script("""
                // Simplified mouse movement and scrolling - optimized for speed
                // Just enough to avoid basic bot detection
                
                // Simple mouse movement simulation
                const simpleMouseMovement = () => {
                    // Create and dispatch a few mouse events at random positions
                    for (let i = 0; i < 3; i++) {
                        const x = Math.floor(Math.random() * window.innerWidth);
                        const y = Math.floor(Math.random() * window.innerHeight);
                        
                        const event = new MouseEvent('mousemove', {
                            'view': window,
                            'bubbles': true,
                            'cancelable': true,
                            'clientX': x,
                            'clientY': y
                        });
                        document.dispatchEvent(event);
                    }
                };
                
                // Quick scroll simulation
                const quickScroll = () => {
                    // Single smooth scroll down
                    window.scrollBy({
                        top: 300 + Math.floor(Math.random() * 200),
                        behavior: 'smooth'
                    });
                };
                
                // Execute minimal interactions - just enough to avoid detection
                simpleMouseMovement();
                quickScroll();
            """)
            time.sleep(0.3)  # Minimal delay - just enough for JavaScript to execute
        except Exception as e:
            print(f"Human behavior simulation failed, continuing anyway: {e}")
        
        # Clear any existing cookies first - no delay needed
        self.driver.delete_all_cookies()
        
        # Check if cookie file exists with improved error handling
        if not os.path.exists(self.cookies_path):
            print(f"❌ Cookie file not found at {self.cookies_path}")
            print("\nTo create a new cookies.json file, run one of these commands:")
            print(f"  python {os.path.join(os.path.dirname(__file__), 'save_cookies.py')} --output {self.cookies_path}")
            print(f"  python {os.path.join(os.path.dirname(__file__), 'refresh_cookies.py')} --interactive --output {self.cookies_path}")
            print("\nOr follow these manual steps:")
            print("1. Open Chrome and log in to LinkedIn")
            print("2. Use a browser extension like 'EditThisCookie' to export cookies")
            print("3. Save the cookies to cookies.json")
            return False
            
        # Enhanced cookie validation with more detailed warnings
        cookie_age = time.time() - os.path.getmtime(self.cookies_path)
        cookie_age_hours = cookie_age / 3600
        cookie_age_minutes = cookie_age / 60
        
        if cookie_age_hours > 2:
            print(f"⚠️ WARNING: Cookie file is {cookie_age_hours:.1f} hours old (HIGH RISK)")
            print("LinkedIn cookies typically expire after 1-2 hours when used for scraping")
            print("Consider refreshing your cookies before proceeding")
            refresh_response = input("Would you like to refresh cookies now? (y/n): ").lower()
            if refresh_response == 'y':
                try:
                    # Import refresh_cookies dynamically to avoid circular imports
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(
                        "refresh_cookies", 
                        os.path.join(os.path.dirname(__file__), "refresh_cookies.py")
                    )
                    refresh_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(refresh_module)
                    
                    # Call the extract_cookies_from_browser function
                    print("\nLaunching browser to refresh cookies...")
                    if refresh_module.extract_cookies_from_browser(self.cookies_path, headless=False):
                        print("Cookies refreshed successfully!")
                        # Reload the browser with new cookies
                        self.driver.quit()
                        self.start_browser()
                        # Start the cookie loading process again from the beginning
                        return self.load_cookies()
                    else:
                        print("Failed to refresh cookies. Continuing with existing cookies...")
                except Exception as e:
                    print(f"Error refreshing cookies: {e}")
                    print("Continuing with existing cookies...")
        elif cookie_age_hours > 1:
            print(f"⚠️ WARNING: Cookie file is {cookie_age_hours:.1f} hours old (MEDIUM RISK)")
        elif cookie_age_minutes > 30:
            print(f"ℹ️ Cookie file is {cookie_age_minutes:.1f} minutes old (LOW RISK)")
        else:
            print(f"✅ Cookie file is fresh ({cookie_age_minutes:.1f} minutes old)")
            
        # Load cookies from file with improved error handling and validation
        try:
            with open(self.cookies_path, 'r') as f:
                try:
                    data = json.load(f)
                    
                    # Check if this is the new enhanced session format or old format
                    if isinstance(data, dict) and 'cookies' in data and 'version' in data:
                        print(f"Detected enhanced session data format v{data['version']}")
                        cookies = data['cookies']
                        
                        # Extract session creation time if available
                        if 'created_at' in data:
                            print(f"Session created: {data['created_at']}")
                            
                        # Set user agent from saved session if available
                        if 'user_agent' in data:
                            try:
                                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                                    "userAgent": data['user_agent']
                                })
                                print("Applied session-specific user agent")
                            except Exception as e:
                                print(f"Could not set user agent: {e}")
                    else:
                        # Legacy format - just a list of cookies
                        cookies = data
                        print("Using legacy cookie format")
                except json.JSONDecodeError as e:
                    print(f"❌ Error: Cookie file is not valid JSON: {e}")
                    print("Please recreate your cookies file using save_cookies.py")
                    return False
                
            if not cookies or not isinstance(cookies, list):
                print("❌ Error: Cookie file has invalid format (empty or not a list)")
                print("Please recreate your cookies file using save_cookies.py")
                return False
                
            # Validate critical LinkedIn cookies are present
            critical_cookies = ['li_at', 'JSESSIONID']
            found_critical = [c for c in critical_cookies if any(cookie.get('name') == c for cookie in cookies)]
            
            if not found_critical:
                print("❌ Error: No critical LinkedIn authentication cookies found")
                print("Please recreate your cookies file using save_cookies.py")
                return False
            elif len(found_critical) < len(critical_cookies):
                missing = set(critical_cookies) - set(found_critical)
                print(f"⚠️ Warning: Missing some important cookies: {', '.join(missing)}")
                print("Authentication may fail or have limited functionality")
                
            # Add cookies to browser with improved error handling
            cookie_count = 0
            for cookie in cookies:
                # Some cookies can cause issues, so try each one separately
                try:
                    # Ensure domain is set correctly for LinkedIn cookies
                    if 'domain' not in cookie or not cookie['domain']:
                        cookie['domain'] = '.linkedin.com'
                    self.driver.add_cookie(cookie)
                    cookie_count += 1
                except Exception as e:
                    # Only print errors for important cookies
                    if cookie.get('name') in critical_cookies:
                        print(f"Error adding critical cookie {cookie.get('name')}: {e}")
                    
            print(f"✅ Added {cookie_count} cookies from {self.cookies_path}")
                    
            # Restore localStorage and sessionStorage if available in enhanced session format
            if isinstance(data, dict) and 'local_storage' in data and 'session_storage' in data:
                try:
                    # Restore localStorage
                    if data['local_storage']:
                        local_storage_script = """
                        for (const [key, value] of Object.entries(arguments[0])) {
                            localStorage.setItem(key, value);
                        }
                        return Object.keys(arguments[0]).length;
                        """
                        items_restored = self.driver.execute_script(local_storage_script, data['local_storage'])
                        print(f"✅ Restored {items_restored} localStorage items")
                        
                    # Restore sessionStorage
                    if data['session_storage']:
                        session_storage_script = """
                        for (const [key, value] of Object.entries(arguments[0])) {
                            sessionStorage.setItem(key, value);
                        }
                        return Object.keys(arguments[0]).length;
                        """
                        items_restored = self.driver.execute_script(session_storage_script, data['session_storage'])
                        print(f"✅ Restored {items_restored} sessionStorage items")
                        print("Enhanced session data applied (extends cookie lifetime)")
                except Exception as e:
                    print(f"Warning: Could not restore browser storage: {e}")
            
            # Refresh page to apply cookies with random delay to appear more human-like
            print("Refreshing page to apply cookies...")
            self.driver.refresh()
            time.sleep(random.uniform(2.0, 3.0))  # Slightly reduced wait time
            
            # Advanced multi-factor authentication verification
            # This uses multiple strategies to determine if we're properly logged in
            print("Verifying authentication status...")
            
            # Strategy 1: Check for login/signup indicators (negative signals)
            login_indicators = [
                "Sign in", "Join now", "Sign in with Google", "New to LinkedIn?", 
                "Join LinkedIn", "Email or phone", "Forgot password", "Sign in to LinkedIn"
            ]
            
            # Strategy 2: Check for member indicators (positive signals)
            member_indicators = [
                "feed-identity-module", "identity-headline", "identity-name", "profile-rail",
                "global-nav-me", "mynetwork", "messaging", "notifications", "premium-upsell-button",
                "groups-entity", "jobs-home", "feed-tab-icon", "nav-settings__dropdown"
            ]
            
            # Strategy 3: Check for premium indicators (strong positive signals)
            premium_indicators = [
                "premium-upsell", "premium-badge", "premium-icon", "sales-nav", "recruiter-nav"
            ]
            
            # Get page source and URL for analysis
            page_text = self.driver.page_source.lower()
            current_url = self.driver.current_url.lower()
            
            # Perform multi-strategy authentication check
            login_detected = any(indicator.lower() in page_text for indicator in login_indicators)
            member_detected = any(indicator.lower() in page_text for indicator in member_indicators)
            premium_detected = any(indicator.lower() in page_text for indicator in premium_indicators)
            feed_url_detected = "feed" in current_url or "mynetwork" in current_url
            
            # Calculate authentication confidence score (0-100)
            auth_score = 0
            if not login_detected: auth_score += 30  # No login indicators is good
            if member_detected: auth_score += 40    # Member indicators are strong positive
            if premium_detected: auth_score += 10    # Premium indicators are bonus
            if feed_url_detected: auth_score += 20   # Being on feed/network pages is good
            
            # Log authentication details for debugging
            print(f"Authentication confidence score: {auth_score}/100")
            print(f"- Login indicators detected: {login_detected}")
            print(f"- Member indicators detected: {member_detected}")
            print(f"- Premium indicators detected: {premium_detected}")
            print(f"- Feed/network URL detected: {feed_url_detected}")
            
            # Decision logic based on authentication score
            if auth_score >= 70:
                print("✅ Authentication successful - cookies are valid")
            elif auth_score >= 40:
                print("⚠️ Authentication partially successful - limited functionality may be available")
                print("Some LinkedIn features may not work correctly")
            else:
                print("❌ Authentication failed - cookies are invalid or expired")
                print("\nPlease update your cookies using one of these methods:")
                print(f"1. Run: python {os.path.join(os.path.dirname(__file__), 'refresh_cookies.py')} --interactive")
                print("2. Or manually update cookies using a browser extension like 'EditThisCookie'")
                
                # Save screenshot for debugging with timestamp
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_dir = os.path.join(os.path.dirname(self.cookies_path), "debug_screenshots")
                    os.makedirs(screenshot_dir, exist_ok=True)
                    screenshot_path = os.path.join(screenshot_dir, f"login_screen_{timestamp}.png")
                    self.driver.save_screenshot(screenshot_path)
                    print(f"Saved login screen screenshot to {screenshot_path}")
                except Exception as e:
                    print(f"Failed to save screenshot: {e}")
                    
                # Attempt to navigate to homepage as a last resort
                try:
                    print("Attempting to navigate to LinkedIn homepage as a last resort...")
                    self.driver.get("https://www.linkedin.com/")
                    time.sleep(3)
                    
                    # Quick re-check for authentication
                    if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                        print("✅ Successfully authenticated after homepage redirect!")
                        return True
                except Exception as e:
                    print(f"Homepage navigation failed: {e}")
                    
                return False
                
            print("Authentication successful - cookies appear valid")
        except Exception as e:
            print(f"Error loading cookies: {e}")
            return False
            
        return True
        
    def scrape_profile(self, profile_url, timeout=20, debug=False):
        """Scrape a LinkedIn profile and extract relevant information
        
        Args:
            profile_url (str): URL of the LinkedIn profile to scrape
            timeout (int): Maximum time in seconds to spend scraping a profile (reduced from 120s to 30s)
            debug (bool): Whether to enable additional debug output and screenshots
            
        Returns:
            dict: Extracted profile information
        """
        if not self.driver:
            self.start_browser()
            if not self.load_cookies():
                return {"error": "Authentication failed"}
                
        # Set a timeout to prevent scraping from taking too long - reduced from 120s to 30s
        start_time = time.time()
        
        try:
            # Simplified authentication check with faster timing
            print("Visiting LinkedIn homepage...")
            try:
                self.driver.get("https://www.linkedin.com/")
                time.sleep(1)  # Reduced wait time even further
            except TimeoutException:
                print("LinkedIn homepage timed out, proceeding anyway...")
                
            # Quick authentication check
            if "Sign in" in self.driver.page_source or "Join now" in self.driver.page_source:
                print("Warning: Not properly authenticated on LinkedIn homepage")
                # Try refreshing cookies by visiting the login page again
                try:
                    self.driver.get("https://www.linkedin.com/login")
                    time.sleep(1)  # Reduced wait time
                    # Check if authentication worked
                    if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                        print("Successfully authenticated after visiting login page")
                except Exception as e:
                    print(f"Error during authentication refresh: {e}")
            
            # Navigate to the profile with a more human-like approach and retry mechanism
            print(f"Navigating to {profile_url}")
            self.driver.set_page_load_timeout(15)  # Reasonable timeout
            
            # Implement retry mechanism for profile navigation
            max_retries = 3
            retry_count = 0
            navigation_successful = False
            
            while retry_count < max_retries and not navigation_successful:
                try:
                    # Direct navigation to profile URL
                    self.driver.get(profile_url)
                    navigation_successful = True
                    print(f"Successfully navigated to profile on attempt {retry_count + 1}")
                except Exception as e:
                    retry_count += 1
                    print(f"Navigation attempt {retry_count} failed: {e}")
                    if retry_count < max_retries:
                        print(f"Retrying in {retry_count * 2} seconds...")
                        time.sleep(retry_count * 2)  # Exponential backoff
                        # Try refreshing the browser state
                        try:
                            self.driver.get("https://www.linkedin.com")
                            time.sleep(1)
                        except:
                            pass
                    else:
                        print("Max retries reached. Continuing with best effort...")
            
            # If all navigation attempts failed, try one last approach
            if not navigation_successful:
                try:
                    print("Attempting alternative navigation method...")
                    # Try using JavaScript for navigation as a last resort
                    self.driver.execute_script(f"window.location.href = '{profile_url}';")
                    time.sleep(3)  # Wait for JS navigation
                except Exception as e:
                    print(f"Alternative navigation also failed: {e}")
            
            # Minimal delay - just enough to let the page start loading
            time.sleep(0.3)
            
            # Only take screenshot in debug mode to save time
            if debug:
                try:
                    pre_scroll_screenshot = os.path.join(os.path.dirname(self.cookies_path), "pre_scroll.png")
                    self.driver.save_screenshot(pre_scroll_screenshot)
                    print(f"Saved pre-scroll screenshot to {pre_scroll_screenshot}")
                except Exception as e:
                    print(f"Failed to save pre-scroll screenshot: {e}")
            
            # Optimized scrolling - much faster but still effective
            print("Fast scrolling to load content...")
            try:
                # Single efficient scroll command to load most of the content at once
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
                time.sleep(0.2)
                
                # One more scroll to reach the bottom in a single efficient movement
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.2)  # Brief pause to let content load
            except Exception as e:
                print(f"Error during scrolling: {e}")
                
                # Simple login wall check
                if "Sign in" in self.driver.page_source and "Join now" in self.driver.page_source:
                    print("Login wall detected - authentication failed")
                    try:
                        screenshot_path = os.path.join(os.path.dirname(self.cookies_path), "login_wall.png")
                        self.driver.save_screenshot(screenshot_path)
                    except Exception as e:
                        print(f"Failed to save screenshot: {e}")
                    return {"error": "Login required to view this profile"}
                    
                # Simple page not found check
                if "this page doesn't exist" in self.driver.page_source.lower():
                    print("Error: LinkedIn says 'This page doesn't exist'")
                    return {"error": "Profile not found - page doesn't exist"}
                
            except TimeoutException:
                print("Profile page load timed out, but continuing anyway...")
                # Quick refresh attempt
                try:
                    self.driver.refresh()
                    time.sleep(3)  # Brief wait after refresh
                except Exception as e:
                    print(f"Error during page refresh: {e}")
            
            # Initialize profile data dictionary
            profile_data = {
                "basic_info": {},
                "about": "",
                "experience": [],
                "education": [],
                "skills": [],
                "interests": []
            }
            
            # Fast, minimal scrolling to trigger lazy loading
            print("Quick scrolling to load profile content...")
            try:
                # Single scroll to trigger lazy loading
                self.driver.execute_script("window.scrollTo(0, 300);")
                time.sleep(0.2)
                
                # Quick scroll to bottom to ensure all content loads
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.3)
                
                # Back to top for extraction
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.2)
            except Exception as e:
                print(f"Error during scrolling: {e}, continuing anyway")
            
            print("Starting profile extraction...")
            
            # Extract basic info with improved selectors and error handling
            print("Extracting basic profile info...")
            
            # Elements should already be visible from our previous scroll to top
            # No need for additional scrolling or waiting here
            
            try:
                
                # Name extraction with updated selectors for 2025 LinkedIn
                name_selectors = [
                    '//h1[contains(@class, "text-heading-xlarge")]',
                    '//h1[contains(@class, "ember-view")]',
                    '//h1',
                    '//div[contains(@class, "pv-text-details__left-panel")]/div[1]',
                    '//div[contains(@class, "display-flex")]/h1',
                    '//div[contains(@class, "profile-info")]/h1',
                    '//div[contains(@class, "profile-header")]//h1',
                    '//*[contains(@class, "profile-info")]//*[contains(@class, "name")]'
                ]
                
                # Take an initial screenshot immediately after page load
                try:
                    initial_screenshot_path = os.path.join(os.path.dirname(self.cookies_path), "profile_initial.png")
                    self.driver.save_screenshot(initial_screenshot_path)
                    print(f"Saved initial screenshot to {initial_screenshot_path}")
                except Exception as e:
                    print(f"Failed to save initial screenshot: {e}")
                    
                # Perform faster scrolling to ensure content is loaded
                print("Performing quick scrolling to trigger content loading...")
                try:
                    # Faster scrolling with shorter pauses
                    for scroll_position in [300, 600, 900, 1200, 600, 300]:
                        self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                        time.sleep(0.2)  # Shorter pause
                    
                    # Take screenshot after scrolling
                    screenshot_path = os.path.join(os.path.dirname(self.cookies_path), "profile_screenshot.png")
                    self.driver.save_screenshot(screenshot_path)
                    print(f"Saved profile screenshot to {screenshot_path}")
                except Exception as e:
                    print(f"Failed to save screenshot: {e}")
                
                for selector in name_selectors:
                    try:
                        name = self.driver.find_element(By.XPATH, selector).text
                        if name and len(name.strip()) > 1:
                            profile_data["basic_info"]["name"] = name.strip()
                            break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                        
                if "name" not in profile_data["basic_info"] or not profile_data["basic_info"]["name"]:
                    profile_data["basic_info"]["name"] = "Not found"
                
                # Headline extraction with updated selectors for 2025 LinkedIn
                headline_selectors = [
                    '//div[contains(@class, "text-body-medium") and not(contains(@class, "visually-hidden"))]',
                    '//div[contains(@class, "pv-text-details__left-panel")]/div[2]',
                    '//div[contains(@class, "ph5")]/div[2]',
                    '//div[contains(@class, "display-flex")]/div[contains(@class, "text-body")]',
                    '//div[contains(@class, "profile-info")]/div[contains(@class, "headline")]',
                    '//*[contains(@class, "profile-info")]//*[contains(@class, "headline")]',
                    '//*[contains(@class, "pv-top-card")]//*[contains(@class, "text-body-medium")]',
                    '//div[@aria-label="Profile information"]/div[2]',
                    '//div[contains(@class, "profile-header")]/div[2]'
                ]
                
                # Print page source for debugging
                print("Analyzing page structure...")
                page_text = self.driver.page_source.lower()
                if "headline" in page_text:
                    print("Page contains 'headline' text")
                if "experience" in page_text:
                    print("Page contains 'experience' text")
                if "education" in page_text:
                    print("Page contains 'education' text")
                
                for selector in headline_selectors:
                    try:
                        headline = self.driver.find_element(By.XPATH, selector).text
                        if headline and len(headline.strip()) > 1:
                            profile_data["basic_info"]["headline"] = headline.strip()
                            break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                        
                if "headline" not in profile_data["basic_info"] or not profile_data["basic_info"]["headline"]:
                    profile_data["basic_info"]["headline"] = "Not found"
                
                # Location extraction with multiple selectors
                location_selectors = [
                    '//span[contains(@class, "text-body-small")][contains(@class, "inline")]',
                    '//div[contains(@class, "pv-text-details__left-panel")]/span[1]',
                    '//div[contains(@class, "pb2")]/span[1]',
                    '//span[contains(@class, "text-body-small") and contains(text(), "Austin")]'
                ]
                
                for selector in location_selectors:
                    try:
                        location = self.driver.find_element(By.XPATH, selector).text
                        if location and len(location.strip()) > 1:
                            profile_data["basic_info"]["location"] = location.strip()
                            break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
                        
                if "location" not in profile_data["basic_info"] or not profile_data["basic_info"]["location"]:
                    profile_data["basic_info"]["location"] = "Not found"
            except Exception as e:
                print(f"Error extracting basic info: {e}")
                
            # Extract About section with improved selectors
            print("Extracting about section...")
            try:
                # Try multiple selectors for the About section
                about_selectors = [
                    '//div[contains(@class, "display-flex")][./span[text()="About"]]/following-sibling::div',
                    '//section[.//span[text()="About"]]//div[contains(@class, "display-flex")]/span[1]',
                    '//section[contains(@class, "summary")]//p',
                    '//div[contains(@class, "inline-show-more-text")]'
                ]
                
                for selector in about_selectors:
                    try:
                        about_section = self.driver.find_element(By.XPATH, selector)
                        about_text = about_section.text.strip()
                        if about_text and len(about_text) > 5:
                            profile_data["about"] = about_text
                            break
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
            except Exception:
                profile_data["about"] = ""
            
            # Check if we've exceeded the timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                print(f"Timeout exceeded ({elapsed_time:.1f}s), returning partial data...")
                return {"partial_data": profile_data}
                
            # Extract Experience - improved approach with better selectors and error handling
            try:
                print("Extracting work experience...")
                
                # Add a small random delay before extraction to appear more human-like
                time.sleep(random.uniform(0.5, 1.2))
                
                # Try multiple selectors for experience section with better error handling
                experience_selectors = [
                    '//section[.//span[text()="Experience"]]',
                    '//section[contains(@class, "experience")]',
                    '//div[contains(@id, "experience")]',
                    '//div[contains(@class, "pvs-list")][.//*[contains(text(), "Experience")]]'
                ]
                
                experience_section = None
                for selector in experience_selectors:
                    try:
                        # Use a slightly longer wait time for better reliability
                        experience_section = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if experience_section:
                            print(f"Found experience section with selector: {selector}")
                            break
                    except (NoSuchElementException, TimeoutException):
                        continue
                
                if experience_section:
                    # Try multiple selectors for experience items
                    item_selectors = [
                        './/ul/li',
                        './/div[contains(@class, "pvs-entity")]',
                        './/div[contains(@class, "display-flex")][.//*[contains(@class, "t-bold")]]'
                    ]
                    
                    experience_items = []
                    for selector in item_selectors:
                        items = experience_section.find_elements(By.XPATH, selector)
                        if items:
                            print(f"Found {len(items)} experience items with selector: {selector}")
                            experience_items = items[:3]  # Get up to 3 most recent experiences
                            break
                    
                    # Process experience items with improved text extraction
                    for item in experience_items:
                        experience = {}
                        
                        # Try to extract structured data first
                        try:
                            # Title - try multiple selectors
                            title_selectors = [
                                './/span[contains(@class, "t-bold")]',
                                './/span[contains(@class, "mr1")][contains(@class, "t-bold")]',
                                './/div[contains(@class, "display-flex")]/span[1]'
                            ]
                            
                            for title_selector in title_selectors:
                                try:
                                    title_elem = item.find_element(By.XPATH, title_selector)
                                    if title_elem and title_elem.text.strip():
                                        experience["title"] = title_elem.text.strip()
                                        break
                                except NoSuchElementException:
                                    continue
                            
                            # Company - try multiple selectors
                            company_selectors = [
                                './/span[contains(@class, "t-14")][contains(@class, "t-normal")]',
                                './/span[contains(@class, "t-14")][.//*[contains(@aria-hidden, "true")]]',
                                './/div[contains(@class, "display-flex")]/span[2]'
                            ]
                            
                            for company_selector in company_selectors:
                                try:
                                    company_elem = item.find_element(By.XPATH, company_selector)
                                    if company_elem and company_elem.text.strip():
                                        experience["company"] = company_elem.text.strip()
                                        break
                                except NoSuchElementException:
                                    continue
                            
                            # Duration - try multiple selectors
                            duration_selectors = [
                                './/span[contains(@class, "t-14")][contains(@class, "t-normal")][contains(@class, "t-black--light")]',
                                './/span[contains(text(), "Present")]/..',
                                './/span[contains(text(), "yr")]/..'
                            ]
                            
                            for duration_selector in duration_selectors:
                                try:
                                    duration_elem = item.find_element(By.XPATH, duration_selector)
                                    if duration_elem and duration_elem.text.strip():
                                        experience["duration"] = duration_elem.text.strip()
                                        break
                                except NoSuchElementException:
                                    continue
                        except Exception as inner_e:
                            print(f"Error extracting structured experience data: {inner_e}")
                        
                        # Fallback to text parsing if structured extraction failed
                        if not experience.get("title") or not experience.get("company"):
                            # Get all text from the item at once
                            item_text = item.text.split('\n')
                            
                            # Extract title (usually first line)
                            if not experience.get("title") and len(item_text) > 0:
                                experience["title"] = item_text[0].strip()
                            
                            # Extract company (usually second line)
                            if not experience.get("company") and len(item_text) > 1:
                                experience["company"] = item_text[1].strip()
                            
                            # Extract duration (usually third line)
                            if not experience.get("duration") and len(item_text) > 2:
                                experience["duration"] = item_text[2].strip()
                        
                        # Set default values if still missing
                        if not experience.get("title"):
                            experience["title"] = "Not found"
                        if not experience.get("company"):
                            experience["company"] = "Not found"
                        if not experience.get("duration"):
                            experience["duration"] = "Not found"
                        
                        profile_data["experience"].append(experience)
                else:
                    print("Experience section not found using any selector")
                    
                    # Fallback: Look for experience keywords in page source
                    if "experience" in self.driver.page_source.lower():
                        # Try to extract any job titles from the page
                        common_titles = ["Engineer", "Developer", "Manager", "Director", "Analyst", "Designer"]
                        page_text = self.driver.page_source.lower()
                        
                        for title in common_titles:
                            if title.lower() in page_text:
                                profile_data["experience"].append({
                                    "title": title,
                                    "company": "Unknown",
                                    "duration": "Unknown"
                                })
                                break
            except Exception as e:
                print(f"Error extracting experience: {e}")
            
            # Check if we've exceeded the timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                print(f"Timeout exceeded ({elapsed_time:.1f}s), returning partial data...")
                return {"partial_data": profile_data}
                
            # Extract Education - improved approach with better selectors and error handling
            try:
                print("Extracting education history...")
                
                # Add a small random delay before extraction to appear more human-like
                time.sleep(random.uniform(0.3, 0.9))
                
                # Try multiple selectors for education section with better error handling
                education_selectors = [
                    '//section[.//span[text()="Education"]]',
                    '//section[contains(@class, "education")]',
                    '//div[contains(@id, "education")]',
                    '//div[contains(@class, "pvs-list")][.//*[contains(text(), "Education")]]'
                ]
                
                education_section = None
                for selector in education_selectors:
                    try:
                        # Use a slightly longer wait time for better reliability
                        education_section = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if education_section:
                            print(f"Found education section with selector: {selector}")
                            break
                    except (NoSuchElementException, TimeoutException):
                        continue
                
                if education_section:
                    # Try multiple selectors for education items
                    item_selectors = [
                        './/ul/li',
                        './/div[contains(@class, "pvs-entity")]',
                        './/div[contains(@class, "display-flex")][.//*[contains(@class, "t-bold")]]'
                    ]
                    
                    education_items = []
                    for selector in item_selectors:
                        items = education_section.find_elements(By.XPATH, selector)
                        if items:
                            print(f"Found {len(items)} education items with selector: {selector}")
                            education_items = items[:3]  # Get up to 3 most recent education entries
                            break
                    
                    # Process education items with improved text extraction
                    for item in education_items:
                        education = {}
                        
                        # Try to extract structured data first
                        try:
                            # School - try multiple selectors
                            school_selectors = [
                                './/span[contains(@class, "t-bold")]',
                                './/span[contains(@class, "mr1")][contains(@class, "t-bold")]',
                                './/div[contains(@class, "display-flex")]/span[1]'
                            ]
                            
                            for school_selector in school_selectors:
                                try:
                                    school_elem = item.find_element(By.XPATH, school_selector)
                                    if school_elem and school_elem.text.strip():
                                        education["school"] = school_elem.text.strip()
                                        break
                                except NoSuchElementException:
                                    continue
                            
                            # Degree - try multiple selectors
                            degree_selectors = [
                                './/span[contains(@class, "t-14")][contains(@class, "t-normal")]',
                                './/span[contains(@class, "t-14")][contains(text(), "Bachelor")]',
                                './/span[contains(@class, "t-14")][contains(text(), "Master")]',
                                './/div[contains(@class, "display-flex")]/span[2]'
                            ]
                            
                            for degree_selector in degree_selectors:
                                try:
                                    degree_elem = item.find_element(By.XPATH, degree_selector)
                                    if degree_elem and degree_elem.text.strip():
                                        education["degree"] = degree_elem.text.strip()
                                        break
                                except NoSuchElementException:
                                    continue
                            
                            # Dates - try multiple selectors
                            date_selectors = [
                                './/span[contains(@class, "t-14")][contains(@class, "t-normal")][contains(@class, "t-black--light")]',
                                './/span[contains(text(), "20")]/..'  # Years typically contain 20xx
                            ]
                            
                            for date_selector in date_selectors:
                                try:
                                    date_elem = item.find_element(By.XPATH, date_selector)
                                    if date_elem and date_elem.text.strip():
                                        education["dates"] = date_elem.text.strip()
                                        break
                                except NoSuchElementException:
                                    continue
                        except Exception as inner_e:
                            print(f"Error extracting structured education data: {inner_e}")
                        
                        # Fallback to text parsing if structured extraction failed
                        if not education.get("school") or not education.get("degree"):
                            # Get all text from the item at once
                            item_text = item.text.split('\n')
                            
                            # Extract school (usually first line)
                            if not education.get("school") and len(item_text) > 0:
                                education["school"] = item_text[0].strip()
                            
                            # Extract degree (usually second line)
                            if not education.get("degree") and len(item_text) > 1:
                                education["degree"] = item_text[1].strip()
                            
                            # Extract dates (usually third line)
                            if not education.get("dates") and len(item_text) > 2:
                                education["dates"] = item_text[2].strip()
                        
                        # Set default values if still missing
                        if not education.get("school"):
                            education["school"] = "Not found"
                        if not education.get("degree"):
                            education["degree"] = "Not found"
                        
                        profile_data["education"].append(education)
                else:
                    print("Education section not found using any selector")
                    
                    # Fallback: Look for education keywords in page source
                    if "education" in self.driver.page_source.lower():
                        # Try to extract any common degrees from the page
                        common_degrees = ["Bachelor", "Master", "MBA", "PhD", "BS", "MS", "BA", "Computer Science"]
                        page_text = self.driver.page_source.lower()
                        
                        for degree in common_degrees:
                            if degree.lower() in page_text:
                                profile_data["education"].append({
                                    "school": "Unknown University",
                                    "degree": degree
                                })
                                break
            except Exception as e:
                print(f"Error extracting education: {e}")
            
            # Extract Skills - comprehensive approach with multiple fallback strategies
            try:
                # Check if we've exceeded 80% of the timeout before starting skills extraction
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout * 0.8:
                    print(f"Skipping skills extraction due to time constraints ({elapsed_time:.1f}s)")
                    return profile_data
                    
                print("Extracting skills...")
                skills_start_time = time.time()
                
                # Add a small random delay to simulate human behavior
                time.sleep(random.uniform(0.2, 0.7))
                
                # Try to scroll to skills section for better visibility
                try:
                    # Try to find skills heading to scroll to it
                    skills_heading = self.driver.find_element(By.XPATH, '//span[text()="Skills"]')
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", skills_heading)
                    time.sleep(random.uniform(0.5, 1.0))  # Wait for any lazy-loaded content
                except Exception:
                    # If we can't find the skills heading, just scroll down a bit more
                    self.driver.execute_script("window.scrollBy(0, 500);")
                    time.sleep(random.uniform(0.3, 0.8))
                
                # Try multiple approaches to find skills
                # Strategy 1: Look for the Skills section with multiple selector patterns
                skills_section_selectors = [
                    '//section[.//span[text()="Skills"]]',
                    '//section[contains(@class, "skills")]',
                    '//div[contains(@id, "skills")]',
                    '//div[contains(@class, "pvs-list")][.//*[contains(text(), "Skills")]]'
                ]
                
                skills_section = None
                for selector in skills_section_selectors:
                    try:
                        skills_section = WebDriverWait(self.driver, 2).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if skills_section:
                            print(f"Found skills section with selector: {selector}")
                            break
                    except (NoSuchElementException, TimeoutException):
                        continue
                
                if skills_section:
                    # Try multiple selectors for skill items within the skills section
                    skill_selectors = [
                        './/span[contains(@class, "t-bold")]',
                        './/span[contains(@class, "display-block")]',
                        './/div[contains(@class, "display-flex")]/span[1]',
                        './/li//span[not(contains(text(), "Show"))]',
                        './/span[contains(@class, "pvs-entity__path-node")]'
                    ]
                    
                    for selector in skill_selectors:
                        try:
                            skill_items = skills_section.find_elements(By.XPATH, selector)
                            if skill_items:
                                print(f"Found {len(skill_items)} skills with selector: {selector}")
                                for skill in skill_items:
                                    skill_text = skill.text.strip()
                                    if skill_text and len(skill_text) > 1 and skill_text not in profile_data["skills"]:
                                        profile_data["skills"].append(skill_text)
                                
                                # If we found skills, no need to try other selectors
                                if profile_data["skills"]:
                                    break
                        except Exception as inner_e:
                            print(f"Error with skill selector {selector}: {inner_e}")
                            continue
                
                # Strategy 2: If we still don't have skills, try looking for skill endorsements throughout the page
                if not profile_data["skills"] or len(profile_data["skills"]) < 3:
                    try:
                        print("Looking for skill endorsements throughout the page...")
                        # Look for skill tags throughout the profile with more comprehensive selectors
                        skill_tag_selectors = [
                            '//li[contains(@class, "skill")]//span',
                            '//div[contains(@class, "endorsement")]//span',
                            '//div[contains(@class, "pvs-entity__path-node")]//span',
                            # Common programming languages and technologies
                            '//div[contains(text(), "Python")]',
                            '//div[contains(text(), "JavaScript")]',
                            '//div[contains(text(), "Java")]',
                            '//div[contains(text(), "C++")]',
                            '//div[contains(text(), "SQL")]',
                            '//div[contains(text(), "React")]',
                            '//div[contains(text(), "Node.js")]',
                            '//div[contains(text(), "Git")]',
                            '//div[contains(text(), "Machine Learning")]',
                            '//div[contains(text(), "Data Science")]',
                            '//div[contains(text(), "AWS")]',
                            '//div[contains(text(), "Cloud")]'
                        ]
                        
                        for selector in skill_tag_selectors:
                            try:
                                tags = self.driver.find_elements(By.XPATH, selector)
                                for tag in tags:
                                    skill_text = tag.text.strip()
                                    if skill_text and len(skill_text) > 1 and skill_text not in profile_data["skills"]:
                                        profile_data["skills"].append(skill_text)
                            except Exception:
                                continue
                    except Exception as e:
                        print(f"Error finding skill endorsements: {e}")
                
                # Strategy 3: As a last resort, look for skill keywords in the page source
                if not profile_data["skills"] or len(profile_data["skills"]) < 3:
                    print("Extracting skills from page source...")
                    # Expanded list of common skills across various industries
                    common_skills = [
                        "Python", "JavaScript", "Java", "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin", "Go",
                        "SQL", "NoSQL", "MongoDB", "PostgreSQL", "MySQL", "Oracle", "Redis",
                        "React", "Angular", "Vue.js", "Node.js", "Express", "Django", "Flask", "Spring", "ASP.NET",
                        "Git", "Docker", "Kubernetes", "CI/CD", "Jenkins", "AWS", "Azure", "GCP", "Terraform",
                        "Machine Learning", "Deep Learning", "Data Science", "AI", "NLP", "Computer Vision",
                        "Project Management", "Agile", "Scrum", "Kanban", "Leadership", "Communication",
                        "Marketing", "SEO", "SEM", "Content Strategy", "Social Media", "Analytics",
                        "UX/UI", "Design", "Figma", "Adobe", "Photoshop", "Illustrator", "InDesign"
                    ]
                    
                    page_source = self.driver.page_source.lower()
                    for skill in common_skills:
                        if skill.lower() in page_source and skill not in profile_data["skills"]:
                            profile_data["skills"].append(skill)
                            # Limit to 10 skills from page source to avoid false positives
                            if len(profile_data["skills"]) >= 10:
                                break
            except NoSuchElementException:
                pass
            
            # Final check for timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                print(f"Timeout exceeded ({elapsed_time:.1f}s), returning partial data...")
                # Add the partial data to a dedicated field
                return {
                    "partial_data": profile_data,
                    "error": f"Timeout after {elapsed_time:.1f}s"
                }
                
            print(f"Profile extraction completed in {elapsed_time:.1f} seconds")
            return profile_data
            
        except Exception as e:
            print(f"Error scraping profile: {e}")
            # Return partial data even on error if we have some
            if profile_data and ("basic_info" in profile_data and profile_data["basic_info"]):
                print("Returning partial data despite error")
                return {
                    "partial_data": profile_data,
                    "error": str(e)
                }
            return {"error": str(e)}
        
    def close(self):
        """Close the browser and clean up"""
        if self.driver:
            self.driver.quit()
            self.driver = None


def scrape_linkedin_profile(profile_url, cookies_path, headless=True, timeout=60, debug=False, browser_type='chrome'):
    """Convenience function to scrape a LinkedIn profile
    
    Args:
        profile_url (str): URL of the LinkedIn profile to scrape
        cookies_path (str): Path to the cookies.json file for authentication
        headless (bool): Whether to run the browser in headless mode
        timeout (int): Maximum time in seconds to spend scraping a profile
        debug (bool): Whether to enable additional debug output and screenshots
        browser_type (str): Type of browser to use ('chrome' or 'firefox')
        
    Returns:
        dict: Extracted profile information
    """
    # Check if cookies file exists and is recent
    if not os.path.exists(cookies_path):
        print(f"Error: Cookie file not found at {cookies_path}")
        print("Please create a cookies.json file by logging into LinkedIn and exporting cookies")
        return {"error": "Cookie file not found"}
        
    # Check cookie freshness
    cookie_age = time.time() - os.path.getmtime(cookies_path)
    cookie_age_hours = cookie_age / 3600
    if cookie_age_hours > 1:
        print(f"Warning: Cookie file is {cookie_age_hours:.1f} hours old")
        print("LinkedIn cookies typically expire after 1-2 hours when used outside the browser")
        print("\nTry using the refresh_cookies.py script to update your cookies:")
        print("  python refresh_cookies.py --output ../../cookies.json")
        print("\nAlternatively, manually export cookies from your browser:")
        print(f"1. Log in to LinkedIn in {browser_type.capitalize()}")
        print("2. Install a cookie manager extension")
        print("3. Export cookies to JSON format")
        print("4. Save to cookies.json")
    else:
        print(f"Cookie file is {cookie_age_hours:.1f} hours old (should be valid)")
        
    # Initialize scraper and extract profile
    print(f"Starting LinkedIn scraper with {browser_type} browser, timeout={timeout}s, headless={headless}, debug={debug}")
    start_time = time.time()
    
    # Create scraper with the specified browser type
    scraper = LinkedInScraper(cookies_path=cookies_path, headless=headless, browser_type=browser_type)
    try:
        profile_data = scraper.scrape_profile(profile_url, timeout=timeout, debug=debug)
        elapsed_time = time.time() - start_time
        print(f"Total scraping time: {elapsed_time:.1f} seconds")
        
        if debug:
            # Save the raw profile data to a debug file
            debug_dir = os.path.dirname(cookies_path)
            debug_file = os.path.join(debug_dir, f"linkedin_debug_{browser_type}.json")
            with open(debug_file, 'w') as f:
                json.dump(profile_data, f, indent=2)
            print(f"Saved debug data to {debug_file}")
            
        return profile_data
    except Exception as e:
        print(f"Error scraping profile with {browser_type} browser: {e}")
        return {"error": str(e)}
    finally:
        scraper.close()


if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Scrape LinkedIn profile data")
    parser.add_argument("profile_url", help="LinkedIn profile URL to scrape", nargs='?', default=None)
    parser.add_argument("--cookies", default="cookies.json", help="Path to cookies.json file")
    parser.add_argument("--output", help="Output file path (JSON)")
    parser.add_argument("--no-headless", action="store_true", help="Run in visible browser mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds")
    parser.add_argument("--check-cookies", action="store_true", help="Only check if cookies are valid")
    parser.add_argument("--save-to-profiles", action="store_true", help="Save to data/linkedin_profiles folder")
    
    args = parser.parse_args()
    
    # If only checking cookies, just verify they're valid
    if args.check_cookies:
        print(f"Checking cookies in {args.cookies}...")
        scraper = LinkedInScraper(cookies_path=args.cookies, headless=not args.no_headless)
        scraper.start_browser()
        is_valid = scraper.load_cookies()
        scraper.close()
        if is_valid:
            print("✅ Cookies are valid and authentication successful")
            sys.exit(0)
        else:
            print("❌ Cookies are invalid or expired")
            sys.exit(1)
    
    # Ensure profile_url is provided for scraping
    if not args.profile_url:
        parser.error("profile_url is required unless --check-cookies is specified")
    
    # Otherwise, proceed with profile scraping
    profile_data = scrape_linkedin_profile(
        args.profile_url, 
        args.cookies, 
        headless=not args.no_headless,
        timeout=args.timeout,
        debug=args.debug
    )
    
    # Extract username from profile URL for default filename
    username = args.profile_url.strip('/').split('/')[-1].split('?')[0]
    
    if args.save_to_profiles:
        # Create profiles directory if it doesn't exist
        profiles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'linkedin_profiles')
        os.makedirs(profiles_dir, exist_ok=True)
        
        # Save to profiles directory with username_persona.json format
        output_path = os.path.join(profiles_dir, f"{username}_persona.json")
        with open(output_path, 'w') as f:
            json.dump(profile_data, f, indent=2)
        print(f"Profile data saved to {output_path}")
    elif args.output:
        with open(args.output, 'w') as f:
            json.dump(profile_data, f, indent=2)
        print(f"Profile data saved to {args.output}")
    else:
        print(json.dumps(profile_data, indent=2))
