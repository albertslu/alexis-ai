# LinkedIn Scraper with Browser-Use Integration

This directory contains tools for scraping LinkedIn profiles to enhance your AI clone with professional context.

## Overview

The LinkedIn scraper now supports two different backends:

1. **Original Selenium-based Scraper**: Requires manual cookie management (refresh every 4 hours)
2. **Browser-Use Scraper**: No cookie management required, more reliable and deployment-friendly

The system will automatically use Browser-Use if it's installed, or fall back to the original scraper.

## Setup

### Option 1: Browser-Use (Recommended)

To set up the Browser-Use scraper (recommended for deployment):

```bash
# Install Browser-Use and dependencies
python setup_browser_use.py
```

This will install:
- browser-use
- langchain-openai
- python-dotenv
- Playwright browsers

### Option 2: Original Scraper

If you prefer to use the original scraper:

```bash
# Save LinkedIn cookies (needs to be refreshed every ~4 hours)
python save_cookies.py
```

## Usage

The scraper can be used through the unified interface:

```python
from scrapers.linkedin.scraper_wrapper import scrape_linkedin_profile

# Scrape a profile (automatically uses Browser-Use if available)
profile_data = scrape_linkedin_profile(
    profile_url="https://www.linkedin.com/in/username/",
    cookies_path="cookies.json",  # Only needed for original scraper
    headless=True
)

# Force the use of the original scraper
profile_data = scrape_linkedin_profile(
    profile_url="https://www.linkedin.com/in/username/",
    cookies_path="cookies.json",
    force_original=True
)
```

## Command Line Usage

```bash
# Scrape a profile using the preferred scraper (Browser-Use if available)
python scraper_wrapper.py https://www.linkedin.com/in/username/ --output profile_data.json

# Force the use of the original scraper
python scraper_wrapper.py https://www.linkedin.com/in/username/ --force-original

# Create a persona from a LinkedIn profile
python example.py https://www.linkedin.com/in/username/
```

## Deployment Considerations

For deployment:

1. Use Browser-Use to avoid cookie management issues
2. Set up proper environment variables for OpenAI API access
3. Make sure Playwright browsers are installed on the deployment server

## Files

- `browser_use_scraper.py`: Browser-Use implementation
- `scraper.py`: Original Selenium-based scraper
- `scraper_wrapper.py`: Unified interface for both scrapers
- `example.py`: Example of creating a persona from a LinkedIn profile
- `save_cookies.py`: Tool for saving LinkedIn cookies (original scraper only)
- `setup_browser_use.py`: Setup script for Browser-Use
- `requirements_browser_use.txt`: Dependencies for Browser-Use
