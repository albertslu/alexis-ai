#!/usr/bin/env python
"""
LinkedIn Scraper Example

This script demonstrates how to use the LinkedIn scraper to extract profile information
and convert it into a persona for the AI clone.
"""

import os
import json
import time
from pathlib import Path
from scraper_wrapper import scrape_linkedin_profile


def create_persona_from_linkedin(profile_url, cookies_path=None, headless=True, timeout=120):
    """Create a persona document from a LinkedIn profile
    
    Args:
        profile_url (str): URL of the LinkedIn profile to scrape
        cookies_path (str): Path to the cookies.json file for authentication (only used by original scraper)
        headless (bool): Whether to run the browser in headless mode
        timeout (int): Maximum time in seconds to spend scraping a profile
        
    Returns:
        dict: Persona data extracted from LinkedIn profile
    """
    # Scrape the profile
    print(f"Scraping LinkedIn profile: {profile_url}")
    
    # Check if we're using the original scraper that needs cookies
    using_original = False
    try:
        import browser_use
        print("Using Browser-Use for LinkedIn scraping (no cookies required)")
    except ImportError:
        using_original = True
    
    if using_original and cookies_path:
        # Verify cookies path exists
        if not os.path.exists(cookies_path):
            print(f"Error: Cookie file not found at {cookies_path}")
            print("Please make sure your cookies.json file exists and is up to date")
            print(f"Run the refresh_cookies.py script to generate a new cookies.json file:")
            print(f"  python refresh_cookies.py --interactive --output {cookies_path}")
            return None
            
        # Check cookie age
        cookie_age = time.time() - os.path.getmtime(cookies_path)
        cookie_age_hours = cookie_age / 3600
        if cookie_age_hours > 1:
            print(f"Warning: Cookie file is {cookie_age_hours:.1f} hours old")
            print("LinkedIn cookies typically expire after 1-2 hours when used outside the browser")
            print("\nTry refreshing your cookies with the refresh_cookies.py script:")
            print(f"  python refresh_cookies.py --interactive --output {cookies_path}")
        else:
            print(f"Cookie file is {cookie_age_hours:.1f} hours old (should be valid)")
    
    # Scrape profile with specified timeout
    profile_data = scrape_linkedin_profile(profile_url, cookies_path, headless=headless, timeout=timeout)
    
    if profile_data is None or ("error" in profile_data and "partial_data" not in profile_data):
        if profile_data and "error" in profile_data:
            print(f"Error: {profile_data['error']}")
        return None
        
    # If we have partial data due to an error, use it anyway
    if "partial_data" in profile_data:
        print("Using partial profile data due to timeout or error")
        profile_data = profile_data["partial_data"]
    
    # Convert to persona format
    persona = {
        "name": profile_data["basic_info"].get("name", "Unknown"),
        "headline": profile_data["basic_info"].get("headline", ""),
        "location": profile_data["basic_info"].get("location", ""),
        "bio": profile_data.get("about", ""),
        "current_role": None,
        "past_roles": [],
        "education": [],
        "skills": profile_data.get("skills", []),
        "interests": profile_data.get("interests", [])
    }
    
    # Process experience
    if profile_data["experience"]:
        # First experience is usually current
        current = profile_data["experience"][0]
        persona["current_role"] = {
            "title": current.get("title", ""),
            "company": current.get("company", ""),
            "duration": current.get("duration", "")
        }
        
        # Rest are past roles
        for exp in profile_data["experience"][1:]:
            persona["past_roles"].append({
                "title": exp.get("title", ""),
                "company": exp.get("company", ""),
                "duration": exp.get("duration", "")
            })
    
    # Process education
    for edu in profile_data["education"]:
        persona["education"].append({
            "school": edu.get("school", ""),
            "degree": edu.get("degree", "")
        })
    
    return persona


def save_persona(persona, output_path):
    """Save the persona to a JSON file"""
    with open(output_path, 'w') as f:
        json.dump(persona, f, indent=2)
    print(f"Persona saved to {output_path}")


if __name__ == "__main__":
    import argparse
    import re
    
    parser = argparse.ArgumentParser(description="Create a persona from a LinkedIn profile")
    parser.add_argument("profile_url", help="LinkedIn profile URL to scrape")
    
    # Default to the cookies.json in the root directory
    default_cookies = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
    parser.add_argument("--cookies", default=default_cookies, help="Path to cookies.json file (for original scraper)")
    parser.add_argument("--no-headless", action="store_true", help="Run in visible browser mode (not headless)")
    parser.add_argument("--debug", action="store_true", help="Show debug information")
    parser.add_argument("--output", help="Output file path for persona (default: auto-generated)")
    parser.add_argument("--force-original", action="store_true", help="Force the use of the original scraper")
    
    args = parser.parse_args()
    
    # Determine headless mode based on arguments
    headless = not args.no_headless
    
    # Set timeout - longer for visible browser mode to allow for manual intervention if needed
    timeout = 180 if not headless else 120
    
    # Print debug info if requested
    if args.debug:
        print(f"Using cookies from: {args.cookies}")
        print(f"Headless mode: {headless}")
        print(f"Timeout: {timeout} seconds")
        
    # Create persona
    persona = create_persona_from_linkedin(args.profile_url, args.cookies, headless=headless, timeout=timeout)
    
    if persona:
        # Extract profile username from URL for naming the file
        profile_name = "unknown"
        url_match = re.search(r'linkedin\.com/in/([\w-]+)', args.profile_url)
        if url_match:
            profile_name = url_match.group(1)
        
        # Create profiles directory if it doesn't exist
        profiles_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "data/linkedin_profiles")
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)
        
        # Set output path (use provided path or generate one)
        output_path = args.output if args.output else os.path.join(profiles_dir, f"{profile_name}_persona.json")
        
        # Save the persona
        save_persona(persona, output_path)
        print(f"\nPersona created successfully and saved to {output_path}!")
        print("You can now use this persona to enhance your AI clone.")
    else:
        print("\nFailed to create persona.")
