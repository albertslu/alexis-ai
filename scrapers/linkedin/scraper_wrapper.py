#!/usr/bin/env python
"""
LinkedIn Profile Scraper Wrapper

This module provides a unified interface for scraping LinkedIn profiles
using either the original Selenium-based scraper or the Browser-Use scraper.
"""

import os
import sys
import json
import argparse
import asyncio
import re
from pathlib import Path

# Add the parent directory to the path so we can import the scrapers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the scrapers
from scrapers.linkedin.browser_use_scraper import (
    sync_scrape_linkedin_profile as browser_use_scrape,
    get_linkedin_credentials,
    prompt_for_credentials,
    set_browser_use_headless,
    manual_save_profile_data
)

def extract_json_from_text(text):
    """
    Extract JSON data from text using regex patterns
    
    Args:
        text (str): Text containing JSON data
        
    Returns:
        dict: Extracted JSON data or None if not found
    """
    # Try to find JSON data in the text using various patterns
    json_patterns = [
        r'```json\s*(.*?)\s*```',  # JSON in code block
        r'\{[\s\S]*"basic_info"[\s\S]*\}',  # Any JSON containing basic_info
        r'\{[\s\S]*"name"[\s\S]*\}'  # Any JSON containing name
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                json_str = match if '{' in match else match
                data = json.loads(json_str)
                # Verify it's a LinkedIn profile by checking for expected keys
                if "basic_info" in data:
                    return data
            except json.JSONDecodeError:
                continue
    
    return None

def scrape_profile(profile_url, output_path=None, cookies_path=None, 
                   headless=True, timeout=180, debug=False, 
                   login=False, save_credentials=False,
                   no_retries=True):
    """
    Scrape a LinkedIn profile and save the result to a file
    
    Args:
        profile_url (str): URL of the LinkedIn profile to scrape
        output_path (str): Path to save the scraped profile data
        cookies_path (str): Path to the cookies file (kept for compatibility)
        headless (bool): Whether to run the browser in headless mode (kept for compatibility)
        timeout (int): Maximum time in seconds to spend scraping a profile
        debug (bool): Whether to enable verbose output
        login (bool): Whether to prompt for LinkedIn login credentials
        save_credentials (bool): Whether to save LinkedIn credentials for future use
        no_retries (bool): If True, don't retry on failure
        
    Returns:
        dict: Scraped profile data
    """
    # Check for credentials
    credentials = get_linkedin_credentials()
    if login or not credentials:
        credentials = prompt_for_credentials(save=save_credentials)
    
    # Set headless mode for Browser-Use
    set_browser_use_headless(headless)
    
    # Use Browser-Use Cloud API
    print("Using Browser-Use Cloud API for LinkedIn scraping")
    
    try:
        # Run the scraper
        profile_data = browser_use_scrape(
            profile_url,
            cookies_path=cookies_path,
            headless=headless,
            timeout=timeout,
            debug=debug
        )
    
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        return {
            "basic_info": {
                "name": "Unknown",
                "headline": "",
                "location": ""
            },
            "about": "",
            "experience": [],
            "education": [],
            "skills": [],
            "interests": [],
            "access_level": "limited",
            "error": f"Error scraping profile: {str(e)}"
        }
    
    # Save the profile data if requested
    if output_path and profile_data:
        # Try to save using the manual method first
        success = manual_save_profile_data(profile_data, output_path)
        if not success:
            # Fall back to standard method
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(profile_data, f, indent=2)
                print(f"Profile data saved to {output_path}")
            except Exception as e:
                print(f"Error saving profile data: {str(e)}")
                # Last resort - print to a file using os.system
                try:
                    json_str = json.dumps(profile_data, indent=2)
                    with open("temp_profile_data.json", "w") as f:
                        f.write(json_str)
                    os.system(f"cp temp_profile_data.json {output_path}")
                    os.remove("temp_profile_data.json")
                    print(f"Profile data saved to {output_path} using system copy")
                except:
                    print("All attempts to save profile data failed")
    
    return profile_data


# For backwards compatibility
def scrape_linkedin_profile(profile_url, cookies_path=None, headless=True, timeout=180, debug=False, browser_type='chrome', force_original=False, credentials=None):
    """Backwards compatibility function for the original API"""
    return scrape_profile(
        profile_url,
        cookies_path=cookies_path,
        headless=headless,
        timeout=timeout,
        debug=debug
    )


def set_scraper_preference(use_browser_use=True):
    """Dummy function for backwards compatibility"""
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a LinkedIn profile")
    parser.add_argument("profile_url", help="LinkedIn profile URL to scrape")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--cookies", help="Path to cookies file (for original scraper)")
    parser.add_argument("--no-headless", action="store_true", help="Run in visible browser mode")
    parser.add_argument("--debug", action="store_true", help="Show verbose output")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds")
    parser.add_argument("--login", action="store_true", help="Prompt for LinkedIn login credentials")
    parser.add_argument("--save-credentials", action="store_true", help="Save LinkedIn credentials for future use")
    parser.add_argument("--allow-retries", action="store_true", help="Allow retries on failure")
    
    args = parser.parse_args()
    
    # Scrape the profile
    profile_data = scrape_profile(
        args.profile_url,
        output_path=args.output,
        cookies_path=args.cookies,
        headless=not args.no_headless,
        timeout=args.timeout,
        debug=args.debug,
        login=args.login,
        save_credentials=args.save_credentials,
        no_retries=not args.allow_retries
    )
    
    # Print the profile data if no output file was specified
    if not args.output:
        print(json.dumps(profile_data, indent=2))
