#!/usr/bin/env python
"""
LinkedIn Prompt Utility

This module provides functions to prompt users for their LinkedIn profile
and integrate that data into the AI clone training process.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.linkedin.scraper_wrapper import scrape_linkedin_profile
from utils.linkedin_integration import create_professional_context


def prompt_for_linkedin(username=None):
    """
    Prompt the user for their LinkedIn profile URL and scrape it if provided.
    
    Args:
        username (str, optional): Username to personalize the prompt
        
    Returns:
        dict: LinkedIn profile data if successfully scraped, None otherwise
    """
    print("\n" + "=" * 80)
    print(f"🔍 Enhance Your AI Clone with LinkedIn Data")
    print("=" * 80)
    
    if username:
        print(f"\nHi {username}! To create a more accurate AI clone, we can use your LinkedIn profile.")
    else:
        print(f"\nTo create a more accurate AI clone, we can use your LinkedIn profile.")
        
    print("This will help your AI clone better understand your professional background.")
    print("Your AI clone will be able to answer questions about your work experience,")
    print("education, and skills in your own communication style.")
    
    print("\nWould you like to provide your LinkedIn profile? (yes/no)")
    response = input("> ").strip().lower()
    
    if response not in ["yes", "y"]:
        print("No problem! Your AI clone will be trained using only your conversation data.")
        return None
    
    print("\nPlease enter your LinkedIn profile URL:")
    print("Example: https://www.linkedin.com/in/your-profile-name/")
    linkedin_url = input("> ").strip()
    
    if not linkedin_url or not linkedin_url.startswith("https://www.linkedin.com/in/"):
        print("Invalid LinkedIn URL. Continuing without LinkedIn data.")
        return None
    
    # Check if we need cookies (using original scraper) or if we can use Browser-Use
    try:
        import browser_use
        print("\nUsing Browser-Use for LinkedIn scraping (no cookies required)")
        cookies_path = None
    except ImportError:
        # Check if cookies are available
        base_dir = Path(__file__).resolve().parent.parent
        cookies_path = base_dir / "scrapers" / "linkedin" / "cookies.json"
        
        if not cookies_path.exists():
            print("\nLinkedIn requires authentication cookies to scrape profiles.")
            print("Would you like to log in to LinkedIn now to create these cookies? (yes/no)")
            login_response = input("> ").strip().lower()
            
            if login_response in ["yes", "y"]:
                try:
                    from scrapers.linkedin.save_cookies import save_linkedin_cookies
                    cookies_path = save_linkedin_cookies()
                    if not cookies_path:
                        print("Failed to save LinkedIn cookies. Continuing without LinkedIn data.")
                        return None
                except Exception as e:
                    print(f"Error saving LinkedIn cookies: {e}")
                    print("Continuing without LinkedIn data.")
                    return None
            else:
                print("Continuing without LinkedIn data.")
                return None
    
    print("\nScraping your LinkedIn profile... (this may take a minute)")
    try:
        profile_data = scrape_linkedin_profile(linkedin_url, cookies_path)
        
        if not profile_data or not profile_data.get("basic_info", {}).get("name"):
            print("Failed to scrape LinkedIn profile. Continuing without LinkedIn data.")
            return None
        
        # Save the profile data
        profiles_dir = base_dir / "scrapers" / "data" / "linkedin_profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a filename based on the profile URL
        profile_name = linkedin_url.rstrip('/').split('/')[-1]
        profile_path = profiles_dir / f"{profile_name}_persona.json"
        
        with open(profile_path, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        print(f"\nSuccessfully scraped LinkedIn profile for {profile_data['basic_info'].get('name')}!")
        print(f"Profile data saved to {profile_path}")
        
        # Create professional context
        professional_context = create_professional_context(profile_data)
        print("\nExtracted professional context:")
        print("-" * 40)
        print(professional_context[:500] + "..." if len(professional_context) > 500 else professional_context)
        print("-" * 40)
        
        return profile_data
        
    except Exception as e:
        print(f"Error scraping LinkedIn profile: {e}")
        print("Continuing without LinkedIn data.")
        return None


if __name__ == "__main__":
    # Test the prompt
    profile_data = prompt_for_linkedin()
    if profile_data:
        print("LinkedIn profile data retrieved successfully.")
    else:
        print("No LinkedIn profile data retrieved.")
