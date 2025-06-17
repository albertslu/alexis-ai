#!/usr/bin/env python
"""
Add LinkedIn Profile Data to AI Clone

This script allows users to manually add LinkedIn profile data to their AI clone.
It extracts professional information from a LinkedIn profile and adds it to the
training data for the AI clone.
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import LinkedIn integration utilities
from utils.linkedin_integration import (
    find_latest_linkedin_profile,
    load_linkedin_persona,
    create_professional_context,
    enhance_system_prompt_with_linkedin
)

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TRAINING_DATA_PATH = DATA_DIR / "training_data.json"
USER_PROFILE_PATH = DATA_DIR / "user_profile.json"
LINKEDIN_PROFILES_DIR = BASE_DIR / "scrapers" / "data" / "linkedin_profiles"
SYSTEM_PROMPT_PATH = DATA_DIR / "system_prompt.txt"


def list_available_profiles():
    """List all available LinkedIn profiles"""
    if not os.path.exists(LINKEDIN_PROFILES_DIR):
        print(f"LinkedIn profiles directory not found: {LINKEDIN_PROFILES_DIR}")
        return []
        
    profiles = list(LINKEDIN_PROFILES_DIR.glob("*_persona.json"))
    if not profiles:
        print("No LinkedIn profiles found.")
        return []
        
    print("Available LinkedIn profiles:")
    for i, profile in enumerate(profiles, 1):
        print(f"{i}. {profile.name}")
        
    return profiles


def update_system_prompt(professional_context):
    """Update the system prompt with LinkedIn professional context
    
    Args:
        professional_context (str): Professional context from LinkedIn
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create system prompt path if it doesn't exist
        os.makedirs(os.path.dirname(SYSTEM_PROMPT_PATH), exist_ok=True)
        
        # Read existing system prompt if it exists
        existing_prompt = ""
        if os.path.exists(SYSTEM_PROMPT_PATH):
            with open(SYSTEM_PROMPT_PATH, 'r') as f:
                existing_prompt = f.read()
        
        # If no existing prompt, create a default one
        if not existing_prompt:
            existing_prompt = """You are an AI clone that responds to messages as if you were the user.

You should generate NEW responses to messages as if YOU were the user responding to someone else.

For example:
- If someone asks a question, respond as if you were the user answering that question.
- If someone greets you, respond as the user would typically greet someone.
- If someone shares information, respond how the user would typically react to that information.

Your goal is to create original responses in the user's voice and communication style.
Match their typical sentence structures, vocabulary choices, and expression styles."""
        
        # Enhance the system prompt with professional context
        enhanced_prompt = enhance_system_prompt_with_linkedin(existing_prompt, professional_context)
        
        # Save the enhanced system prompt
        with open(SYSTEM_PROMPT_PATH, 'w') as f:
            f.write(enhanced_prompt)
            
        print(f"System prompt updated with LinkedIn professional context")
        print(f"Saved to: {SYSTEM_PROMPT_PATH}")
        return True
    except Exception as e:
        print(f"Error updating system prompt: {e}")
        return False


def update_training_data(professional_context):
    """Update the training data with LinkedIn professional context
    
    Args:
        professional_context (str): Professional context from LinkedIn
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create training data path if it doesn't exist
        os.makedirs(os.path.dirname(TRAINING_DATA_PATH), exist_ok=True)
        
        # Read existing training data if it exists
        training_data = {
            'answers': {},
            'conversations': [],
            'trained': False,
            'last_updated': None,
            'linkedin_integrated': False
        }
        
        if os.path.exists(TRAINING_DATA_PATH):
            with open(TRAINING_DATA_PATH, 'r') as f:
                training_data = json.load(f)
        
        # Add a flag to indicate LinkedIn data has been integrated
        training_data['linkedin_integrated'] = True
        training_data['linkedin_context'] = professional_context
        
        # Save the updated training data
        with open(TRAINING_DATA_PATH, 'w') as f:
            json.dump(training_data, f, indent=2)
            
        print(f"Training data updated with LinkedIn integration flag")
        return True
    except Exception as e:
        print(f"Error updating training data: {e}")
        return False


def update_user_profile(professional_context):
    """Update the user profile with LinkedIn professional context
    
    Args:
        professional_context (str): Professional context from LinkedIn
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create user profile path if it doesn't exist
        os.makedirs(os.path.dirname(USER_PROFILE_PATH), exist_ok=True)
        
        # Read existing user profile if it exists
        user_profile = {
            'style_characteristics': {},
            'vocabulary': [],
            'emoji_usage': {},
            'common_phrases': [],
            'punctuation_style': {},
            'professional_info': {}
        }
        
        if os.path.exists(USER_PROFILE_PATH):
            with open(USER_PROFILE_PATH, 'r') as f:
                user_profile = json.load(f)
        
        # Add professional context to user profile
        user_profile['professional_info']['linkedin_context'] = professional_context
        user_profile['professional_info']['last_updated'] = str(Path(find_latest_linkedin_profile()).name)
        
        # Save the updated user profile
        with open(USER_PROFILE_PATH, 'w') as f:
            json.dump(user_profile, f, indent=2)
            
        print(f"User profile updated with LinkedIn professional context")
        return True
    except Exception as e:
        print(f"Error updating user profile: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Add LinkedIn profile data to AI clone")
    parser.add_argument("--profile", help="LinkedIn profile JSON file to use")
    parser.add_argument("--list", action="store_true", help="List available LinkedIn profiles")
    parser.add_argument("--force", action="store_true", help="Force update even if LinkedIn data is already integrated")
    
    args = parser.parse_args()
    
    # List available profiles if requested
    if args.list:
        profiles = list_available_profiles()
        return
    
    # Check if LinkedIn data is already integrated
    if os.path.exists(TRAINING_DATA_PATH) and not args.force:
        try:
            with open(TRAINING_DATA_PATH, 'r') as f:
                training_data = json.load(f)
                if training_data.get('linkedin_integrated', False):
                    print("LinkedIn data is already integrated with your AI clone.")
                    print("Use --force to update anyway.")
                    return
        except Exception:
            pass  # Continue if there's an error reading the file
    
    # Find the LinkedIn profile to use
    profile_path = args.profile
    if not profile_path:
        # Try to find the most recent profile
        profile_path = find_latest_linkedin_profile()
        if not profile_path:
            print("No LinkedIn profiles found. Please run the LinkedIn scraper first.")
            print("Example: python scrapers/linkedin/scraper.py https://www.linkedin.com/in/username/ --cookies cookies.json --save-to-profiles")
            return
    
    print(f"Using LinkedIn profile: {os.path.basename(profile_path)}")
    
    # Load the LinkedIn profile data
    linkedin_data = load_linkedin_persona(profile_path)
    if not linkedin_data:
        print(f"Failed to load LinkedIn data from {profile_path}")
        return
    
    # Create professional context from LinkedIn data
    professional_context = create_professional_context(linkedin_data)
    
    print("\nExtracted Professional Context:")
    print("==================================")
    print(professional_context)
    print("==================================")
    
    # Update system prompt with LinkedIn professional context
    update_system_prompt(professional_context)
    
    # Update training data with LinkedIn integration flag
    update_training_data(professional_context)
    
    # Update user profile with LinkedIn professional context
    update_user_profile(professional_context)
    
    print("\nLinkedIn profile data has been successfully integrated with your AI clone!")
    print("\nNext Steps:")
    print("1. Start a new training session to incorporate this professional information:")
    print("   - Visit the web interface and start a conversation")
    print("   - After 10 messages, fine-tuning will automatically begin")
    print("2. Or manually trigger fine-tuning with your new LinkedIn data:")
    print("   curl -X POST http://localhost:5002/api/start-fine-tuning")


if __name__ == "__main__":
    main()
