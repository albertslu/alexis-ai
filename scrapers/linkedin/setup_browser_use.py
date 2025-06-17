#!/usr/bin/env python
"""
Setup Browser-Use for LinkedIn Scraping

This script installs the necessary dependencies for using Browser-Use
as a replacement for the cookie-based LinkedIn scraper.
"""

import subprocess
import sys
import os
from pathlib import Path

def install_browser_use():
    """Install Browser-Use and its dependencies"""
    print("Setting up Browser-Use for LinkedIn scraping...")
    
    # Get the requirements file path
    requirements_path = Path(__file__).parent / "requirements_browser_use.txt"
    
    if not requirements_path.exists():
        print(f"Error: Requirements file not found at {requirements_path}")
        return False
    
    try:
        # Install the dependencies
        print(f"Installing dependencies from {requirements_path}...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_path)
        ])
        
        # Install Playwright browsers
        print("Installing Playwright browsers...")
        subprocess.check_call([
            sys.executable, "-m", "playwright", "install", "chromium"
        ])
        
        print("\nBrowser-Use setup complete!")
        print("You can now use the LinkedIn scraper without needing to refresh cookies.")
        print("\nTo use Browser-Use for scraping, run:")
        print("python -m scrapers.linkedin.scraper_wrapper <profile_url> --output <output_path>")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = install_browser_use()
    sys.exit(0 if success else 1)
