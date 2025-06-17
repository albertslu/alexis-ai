#!/usr/bin/env python
"""
LinkedIn Profile Scraper using Browser-Use Cloud API

This module extracts public information from LinkedIn profiles using Browser-Use Cloud API,
which provides better detection avoidance and doesn't require any local dependencies or installation.
"""

import json
import os
import re
import asyncio
import httpx
from dotenv import load_dotenv
import logging
import time

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get the API key from environment variables
BROWSER_USE_API_KEY = os.environ.get("BROWSER_USE_API_KEY")
if not BROWSER_USE_API_KEY:
    logger.warning("BROWSER_USE_API_KEY not found in environment variables")

class LinkedInBrowserUseScraper:
    """LinkedIn profile scraper using Browser-Use Cloud API with AI-powered extraction"""
    
    def __init__(self, model="gpt-4o", verbose=False):
        """
        Initialize the LinkedIn scraper
        
        Args:
            model (str): LLM model to use for extraction (used by the cloud API)
            verbose (bool): Whether to enable additional output
        """
        self.model = model
        self.verbose = verbose
        
        if not BROWSER_USE_API_KEY:
            raise ValueError("BROWSER_USE_API_KEY environment variable is required. Please set it before using the scraper.")
        
        self.api_base_url = "https://api.browser-use.com/api/v1"
        
    async def scrape_profile(self, profile_url):
        """
        Scrape a LinkedIn profile using the Browser Use Cloud API
        
        Args:
            profile_url (str): URL of the LinkedIn profile to scrape
            
        Returns:
            dict: Scraped profile data
        """
        try:
            # Format the LinkedIn URL
            profile_url = self._format_linkedin_url(profile_url)
            
            # Get LinkedIn credentials
            linkedin_credentials = get_linkedin_credentials()
            
            # Create the task description
            task_description = self._create_task_description(profile_url, linkedin_credentials)
            
            # Prepare the API request payload
            payload = {
                "task": task_description,
                "model": self.model
            }
            
            # If we have credentials, add them to the payload
            if linkedin_credentials:
                payload["linkedin_credentials"] = linkedin_credentials
                logger.info("Using LinkedIn credentials from environment variables")
            
            # Make the API request
            async with httpx.AsyncClient(timeout=30) as client:
                headers = {
                    "Authorization": f"Bearer {BROWSER_USE_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                # Create the task
                logger.info(f"Sending request to {self.api_base_url}/run-task")
                response = await client.post(
                    f"{self.api_base_url}/run-task",
                    headers=headers,
                    json=payload
                )
                
                # Check if the request was successful
                if response.status_code == 200:
                    # Parse the response
                    result = response.json()
                    logger.info(f"API Response: {result}")
                    
                    # Check if we got a task ID
                    task_id = result.get('id')
                    
                    if task_id:
                        # Check task status and retrieve result
                        task_result = await self._get_task_result(task_id, profile_url)
                        if task_result:
                            profile_data = self._process_api_result(task_result, profile_url)
                        else:
                            profile_data = self._create_basic_profile(task_id, profile_url)
                    else:
                        profile_data = self._process_api_result(result, profile_url)
                    
                    return profile_data
                else:
                    error_msg = f"API request failed: {response.status_code} {response.text}"
                    logger.error(error_msg)
                    return self._create_error_response(profile_url, error_msg)
        except Exception as e:
            error_msg = f"Error scraping profile: {str(e)}"
            logger.error(error_msg)
            return self._create_error_response(profile_url, error_msg)
    
    async def _get_task_result(self, task_id, profile_url, max_wait_time=300, check_interval=5):
        """
        Wait for a task to complete and retrieve the result
        
        Args:
            task_id (str): The task ID
            profile_url (str): URL of the LinkedIn profile
            max_wait_time (int): Maximum time to wait in seconds
            check_interval (int): Time between status checks in seconds
            
        Returns:
            dict: Task result or None if timed out
        """
        start_time = time.time()
        
        # Keep checking until we get a result or time out
        while time.time() - start_time < max_wait_time:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    headers = {
                        "Authorization": f"Bearer {BROWSER_USE_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    # Check task status
                    status_url = f"{self.api_base_url}/task/{task_id}/status"
                    logger.info(f"Checking task status at: {status_url}")
                    status_response = await client.get(status_url, headers=headers)
                    
                    if status_response.status_code == 200:
                        status_text = status_response.text.strip('"')
                        logger.info(f"Task status: {status_text}")
                        
                        # If the task is finished, get the result
                        if status_text == "finished":
                            logger.info(f"Task {task_id} is finished, retrieving result")
                            
                            # Get the task result
                            result_url = f"{self.api_base_url}/task/{task_id}"
                            logger.info(f"Getting result from: {result_url}")
                            result_response = await client.get(result_url, headers=headers)
                            
                            if result_response.status_code == 200:
                                logger.info(f"Got result with status code: {result_response.status_code}")
                                
                                try:
                                    # Try to parse as JSON
                                    result_data = result_response.json()
                                    logger.info(f"Successfully parsed result as JSON")
                                    return result_data
                                except json.JSONDecodeError:
                                    # If not JSON, return the raw text
                                    logger.info(f"Result is not JSON, returning raw text")
                                    return {"output": result_response.text}
                            else:
                                logger.error(f"Failed to get result: {result_response.status_code}")
                            
                            # If we get here, we couldn't get the result
                            logger.info(f"Creating basic profile for task {task_id}")
                            return self._create_basic_profile(task_id, profile_url)
                        
                        # If the task failed, return None
                        if status_text == "failed":
                            logger.error(f"Task {task_id} failed")
                            return None
                    else:
                        logger.error(f"Error checking task status: {status_response.status_code}")
                
                # Wait before checking again
                await asyncio.sleep(check_interval)
            
            except Exception as e:
                logger.error(f"Error checking task status: {str(e)}")
                await asyncio.sleep(check_interval)
        
        # If we get here, we timed out
        logger.error(f"Timed out waiting for task {task_id} to complete")
        return None
    
    def _extract_profile_from_text(self, text):
        """
        Try to extract LinkedIn profile data from text
        
        Args:
            text (str): Text that might contain profile data
            
        Returns:
            dict: Extracted profile data or None if not found
        """
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*({\s*".*?})\s*```', text, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(1)
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Try to find any JSON object in the text
        json_match = re.search(r'({[\s\S]*?})', text)
        if json_match:
            try:
                json_str = json_match.group(1)
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _create_basic_profile(self, task_id, profile_url):
        """
        Create a basic profile when task result retrieval fails
        
        Args:
            task_id (str): The task ID
            profile_url (str): URL of the LinkedIn profile
            
        Returns:
            dict: Basic profile structure
        """
        # Extract username from URL for basic profile info
        username = profile_url.split("/")[-1]
        name = username.replace("-", " ").title() if username else "Unknown"
        
        return {
            "basic_info": {
                "name": name,
                "headline": "LinkedIn Profile",
                "location": ""
            },
            "about": "Profile extraction completed via Browser Use Cloud API",
            "experience": [],
            "education": [],
            "skills": [],
            "access_level": "limited",
            "task_id": task_id,
            "note": "Task completed but result retrieval failed"
        }
    
    def _format_linkedin_url(self, profile_url):
        """
        Format the LinkedIn URL properly to ensure Browser Use API can handle it
        
        Handles various URL formats users might copy from browsers:
        - Partial URL: "linkedin.com/in/albertlu"
        - URL without www: "https://linkedin.com/in/albertlu"
        - Full URL: "https://www.linkedin.com/in/albertlu"
        
        Args:
            profile_url (str): URL copied from browser for LinkedIn profile
            
        Returns:
            str: Properly formatted LinkedIn URL
        """
        # Remove any trailing slashes and whitespace
        profile_url = profile_url.strip().rstrip('/')
        
        # Handle partial URLs like "linkedin.com/in/username"
        if profile_url.startswith("linkedin.com"):
            return f"https://www.{profile_url}"
        
        # Handle URLs without www like "https://linkedin.com/in/username"
        if profile_url.startswith("https://linkedin.com"):
            parts = profile_url.split("linkedin.com")
            return f"https://www.linkedin.com{parts[1]}"
            
        # Handle URLs without https like "www.linkedin.com/in/username"
        if profile_url.startswith("www.linkedin.com"):
            return f"https://{profile_url}"
            
        # If it's already a complete URL, just return it
        if profile_url.startswith("https://www.linkedin.com"):
            return profile_url
        
        # Default fallback - if it doesn't match known patterns, return as is
        return profile_url
    
    def _create_task_description(self, profile_url, credentials=None):
        """
        Create the task description for the Browser-Use Cloud API
        
        Args:
            profile_url (str): URL of the LinkedIn profile to scrape
            credentials (dict): Optional LinkedIn credentials
            
        Returns:
            str: Task description for the Browser-Use agent
        """
        task_description = "FIRST, "
        
        # Add login instructions if credentials are provided
        if credentials and credentials.get('username') and credentials.get('password'):
            task_description += f"""
            log in to LinkedIn using these credentials:
            1. Navigate to https://www.linkedin.com/login
            2. Enter the email or username: {credentials['username']}
            3. Enter the password: {credentials['password']}
            4. Click the Sign In button
            5. Wait for the login to complete (this may take several seconds)
            6. If you encounter any security verification, please take a screenshot and report it
            7. Once logged in, navigate to the profile URL: {profile_url}
            """
        else:
            task_description += f"""
            Navigate to the profile URL: {profile_url}
            """
        
        # Add the extraction instructions
        task_description += f"""
        SECOND, extract ONLY the information that is immediately visible on the profile:
        1. Basic info: name, headline, location
        2. Experience: For visible positions, extract title, company name, and duration
        3. Education: For visible entries, extract school name, degree, and dates
        4. Any skills that are immediately visible
        
        IMPORTANT: DO NOT click any "see more" or "show more" buttons. Only extract what is immediately visible.
        IMPORTANT: DO NOT try to expand any sections or click any tabs.
        IMPORTANT: DO NOT try to extract connections, followers, or interests - this information is not needed.
        IMPORTANT: If you can't see certain information, just leave those fields empty.
        
        Format the output as a valid JSON object with these exact keys:
        {{
          "basic_info": {{
            "name": "...",
            "headline": "...",
            "location": "..."
          }},
          "about": "...",
          "experience": [
            {{
              "title": "...",
              "company": "...",
              "duration": "..."
            }}
          ],
          "education": [
            {{
              "school": "...",
              "degree": "...",
              "dates": "..."
            }}
          ],
          "skills": ["..."],
          "access_level": "full" or "limited"
        }}
        
        Set "access_level" to "full" if you were able to access the complete profile, or "limited" if you encountered restrictions.
        
        IMPORTANT: The JSON must be properly formatted and must use the exact keys shown above.
        IMPORTANT: Return ONLY the JSON object, nothing else.
        """
        
        return task_description
    
    def _process_api_result(self, result, profile_url):
        """
        Process the API result and extract profile data
        
        Args:
            result (dict): API result
            profile_url (str): URL of the LinkedIn profile
            
        Returns:
            dict: Processed profile data
        """
        try:
            logger.info(f"Received task_id: {result.get('id', 'unknown')}")
            
            # Check if the result contains profile data
            if isinstance(result, dict):
                # If the result already has basic_info, it might be a profile
                if 'basic_info' in result:
                    return result
                
                # If the result has an output field, it might contain profile data
                if 'output' in result:
                    # Try to extract profile data from the output
                    profile_data = self._extract_profile_from_text(result['output'])
                    if profile_data:
                        return profile_data
                
                # If the result has a result field, it might contain profile data
                if 'result' in result:
                    if isinstance(result['result'], dict):
                        # If the result already has basic_info, it might be a profile
                        if 'basic_info' in result['result']:
                            return result['result']
                    
                    # Try to extract profile data from the result
                    profile_data = self._extract_profile_from_text(str(result['result']))
                    if profile_data:
                        return profile_data
            
            # If we couldn't extract profile data, create a basic profile
            task_id = result.get('id', 'unknown')
            return self._create_basic_profile(task_id, profile_url)
            
        except Exception as e:
            error_msg = f"Unexpected error processing API result: {str(e)}"
            logger.error(error_msg)
            return self._create_error_response(profile_url, error_msg)
    
    def _create_error_response(self, profile_url, error_message):
        """
        Create an error response when scraping fails
        
        Args:
            profile_url (str): URL of the LinkedIn profile
            error_message (str): Error message
            
        Returns:
            dict: Error response with minimal profile data
        """
        # Extract username from URL for a basic profile name
        username = profile_url.split("/")[-1]
        name = username.replace("-", " ").title() if username else "Unknown"
        
        return {
            "basic_info": {
                "name": name,
                "headline": "",
                "location": ""
            },
            "about": "",
            "experience": [],
            "education": [],
            "skills": [],
            "access_level": "limited",
            "error": error_message
        }

def get_linkedin_credentials():
    """
    Get LinkedIn credentials from environment variables
    
    Returns:
        dict: Dictionary with username and password or None if not found
    """
    username = os.environ.get("LINKEDIN_USERNAME")
    password = os.environ.get("LINKEDIN_PASSWORD")
    
    if username and password:
        return {"username": username, "password": password}
    
    return None

def prompt_for_credentials(save=False):
    """
    Stub function for backward compatibility
    Returns credentials from environment variables
    
    Args:
        save (bool): Not used, kept for compatibility
        
    Returns:
        dict: LinkedIn credentials
    """
    credentials = get_linkedin_credentials()
    if not credentials:
        logger.warning("LinkedIn credentials not found in environment variables")
        # Return empty credentials as fallback
        return {"username": "", "password": ""}
    return credentials

def set_browser_use_headless(headless=True):
    """
    Stub function for backward compatibility
    
    Args:
        headless (bool): Not used with Cloud API
    """
    # This function is no longer needed with the Cloud API
    pass

async def scrape_linkedin_profile(profile_url, cookies_path=None, headless=True, timeout=180, debug=False, browser_type='chrome'):
    """
    Convenience function to scrape a LinkedIn profile using Browser-Use Cloud API
    
    Args:
        profile_url (str): URL of the LinkedIn profile to scrape
        cookies_path (str): Not used with Cloud API, kept for compatibility
        headless (bool): Not used with Cloud API, kept for compatibility
        timeout (int): Maximum time in seconds to spend scraping a profile
        debug (bool): Whether to enable verbose output
        browser_type (str): Not used with Cloud API, kept for compatibility
        
    Returns:
        dict: Extracted profile information
    """
    try:
        scraper = LinkedInBrowserUseScraper(verbose=debug)
        credentials = get_linkedin_credentials()
        
        # Run the scraper asynchronously
        profile_data = await scraper.scrape_profile(
            profile_url=profile_url
        )
        
        return profile_data
    except Exception as e:
        logger.error(f"Error in scrape_linkedin_profile: {str(e)}")
        raise

def sync_scrape_linkedin_profile(profile_url, cookies_path=None, headless=True, timeout=180, debug=False, browser_type='chrome'):
    """
    Synchronous wrapper for scrape_linkedin_profile
    
    This function has the same signature as the original scraper for compatibility.
    
    Args:
        profile_url (str): URL of the LinkedIn profile to scrape
        cookies_path (str): Not used with Cloud API, kept for compatibility
        headless (bool): Not used with Cloud API, kept for compatibility
        timeout (int): Maximum time in seconds to spend scraping a profile
        debug (bool): Whether to enable verbose output
        browser_type (str): Not used with Cloud API, kept for compatibility
        
    Returns:
        dict: Extracted profile information
    """
    # Create an event loop if there isn't one already
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Create the scraper
    scraper = LinkedInBrowserUseScraper(verbose=debug)
    
    # Run the scraper asynchronously
    profile_data = loop.run_until_complete(
        scraper.scrape_profile(profile_url=profile_url)
    )
    
    return profile_data

def manual_save_profile_data(profile_data, output_path):
    """
    Manually save profile data to a file, ensuring it's properly written
    
    Args:
        profile_data (dict): The profile data to save
        output_path (str): Path to save the data to
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write data to the file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Profile data saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving profile data: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape LinkedIn profiles using Browser-Use Cloud API")
    parser.add_argument("profile_url", help="URL of the LinkedIn profile to scrape")
    parser.add_argument("--output", "-o", help="Path to save the extracted profile data")
    parser.add_argument("--timeout", "-t", type=int, default=180, help="Timeout in seconds")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    print(f"Scraping LinkedIn profile: {args.profile_url}")
    
    # Scrape the profile
    profile_data = sync_scrape_linkedin_profile(
        profile_url=args.profile_url,
        timeout=args.timeout,
        debug=args.debug
    )
    
    # Save the profile data if output path is provided
    if args.output and profile_data:
        manual_save_profile_data(profile_data, args.output)
        print(f"Profile data saved to {args.output}")
    elif profile_data:
        print(json.dumps(profile_data, indent=2))
    else:
        print("Failed to extract profile data")
