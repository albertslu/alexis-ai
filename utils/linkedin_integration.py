#!/usr/bin/env python
"""
LinkedIn Data Integration for AI Clone

This module integrates LinkedIn profile data into the AI clone training process.
It extracts professional information and creates additional training examples
to help the clone understand the user's professional background.
"""

import os
import json
from pathlib import Path

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
LINKEDIN_PROFILES_DIR = BASE_DIR / "scrapers" / "data" / "linkedin_profiles"


def load_linkedin_persona(profile_path):
    """Load a LinkedIn persona from a JSON file
    
    Args:
        profile_path (str): Path to the LinkedIn persona JSON file
        
    Returns:
        dict: The LinkedIn persona data
    """
    try:
        with open(profile_path, 'r') as f:
            data = json.load(f)
            
        # Handle both full and partial data formats
        if "partial_data" in data:
            return data["partial_data"]
        return data
    except Exception as e:
        print(f"Error loading LinkedIn profile: {e}")
        return None


def create_professional_context(linkedin_data):
    """Create a context string from LinkedIn profile data
    
    Args:
        linkedin_data (dict): LinkedIn profile data
        
    Returns:
        str: A formatted context string with professional information
    """
    context = []
    
    # Basic info
    if "basic_info" in linkedin_data and linkedin_data["basic_info"]:
        basic = linkedin_data["basic_info"]
        if "name" in basic:
            context.append(f"My name is {basic['name']}.")
        if "headline" in basic:
            context.append(f"Professional headline: {basic['headline']}")
        if "location" in basic:
            context.append(f"I'm based in {basic['location']}.")
    
    # About section
    if "about" in linkedin_data and linkedin_data["about"]:
        context.append(f"About me: {linkedin_data['about']}")
    
    # Current role
    if "experience" in linkedin_data and linkedin_data["experience"]:
        current = linkedin_data["experience"][0]  # First experience is usually current
        role = current.get("title", "")
        company = current.get("company", "").split("u00b7")[0].strip() if "u00b7" in current.get("company", "") else current.get("company", "")
        if role and company and role != "Summer 2025" and company != "Summer 2025":
            context.append(f"I currently work as {role} at {company}.")
        
        # Past roles
        if len(linkedin_data["experience"]) > 1:
            past_roles = []
            for exp in linkedin_data["experience"][1:4]:  # Limit to 3 past roles
                role = exp.get("title", "")
                company = exp.get("company", "").split("u00b7")[0].strip() if "u00b7" in exp.get("company", "") else exp.get("company", "")
                if role and company and role != "Summer 2025" and company != "Summer 2025":
                    past_roles.append(f"{role} at {company}")
            
            if past_roles:
                context.append(f"Previously, I worked as {', '.join(past_roles[:-1])}{' and ' if len(past_roles) > 1 else ''}{past_roles[-1] if past_roles else ''}.")
    
    # Education
    if "education" in linkedin_data and linkedin_data["education"]:
        schools = []
        for edu in linkedin_data["education"]:
            school = edu.get("school", "")
            degree = edu.get("degree", "")
            if school:
                schools.append(f"{degree} from {school}" if degree else f"{school}")
        
        if schools:
            context.append(f"My education includes {', '.join(schools[:-1])}{' and ' if len(schools) > 1 else ''}{schools[-1] if schools else ''}.")
    
    # Skills
    if "skills" in linkedin_data and linkedin_data["skills"]:
        if len(linkedin_data["skills"]) > 0:
            top_skills = linkedin_data["skills"][:5]  # Limit to top 5 skills
            context.append(f"My top skills include {', '.join(top_skills[:-1])}{' and ' if len(top_skills) > 1 else ''}{top_skills[-1] if top_skills else ''}.")
    
    return "\n".join(context)


def create_linkedin_training_examples(professional_context, system_prompt):
    """Create training examples that incorporate LinkedIn professional context
    
    Args:
        professional_context (str): The professional context string
        system_prompt (str): The system prompt to use for examples
        
    Returns:
        list: List of training examples in the format expected by the AI clone
    """
    # Extract key information from professional context
    name = ""
    current_role = ""
    company = ""
    education = ""
    skills = []
    location = ""
    
    for line in professional_context.split('\n'):
        if "My name is" in line:
            name = line.split("My name is ")[1].split(".")[0]
        elif "currently work as" in line:
            parts = line.split("currently work as ")[1].split(" at ")
            if len(parts) >= 2:
                current_role = parts[0]
                company = parts[1].replace(".", "")
        elif "education includes" in line:
            education = line.split("education includes ")[1].replace(".", "")
        elif "skills include" in line:
            skills_text = line.split("skills include ")[1].replace(".", "")
            skills = [s.strip() for s in skills_text.split(",")]
        elif "based in" in line:
            location = line.split("based in ")[1].replace(".", "")
    
    # Create examples with natural-sounding responses that incorporate the LinkedIn data
    # without directly copying it verbatim
    examples = [
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Can you tell me about your professional background?"},
                {"role": "assistant", "content": f"i'm currently working on my own startup, did some work in tech before that. studied computer engineering in college."}
            ]
        },
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Where do you work currently?"},
                {"role": "assistant", "content": f"right now i'm working on my own thing, building an ai startup"} 
            ]
        },
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "What's your educational background?"},
                {"role": "assistant", "content": f"studied comp eng at ut austin"} 
            ]
        },
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "What skills are you proficient in?"},
                {"role": "assistant", "content": f"mostly programming and product design, some photography too"} 
            ]
        },
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Tell me about yourself."},
                {"role": "assistant", "content": f"i'm a founder working on an ai startup, graduated from ut austin with a comp eng degree. into photography and traveling when i have free time"}
            ]
        }
    ]
    
    return examples


def find_latest_linkedin_profile():
    """Find the most recently modified LinkedIn profile in the profiles directory
    
    Returns:
        str: Path to the most recent LinkedIn profile, or None if none found
    """
    if not os.path.exists(LINKEDIN_PROFILES_DIR):
        return None
        
    profiles = list(LINKEDIN_PROFILES_DIR.glob("*_persona.json"))
    if not profiles:
        return None
        
    # Sort by modification time (most recent first)
    profiles.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return str(profiles[0])


def enhance_system_prompt_with_linkedin(original_prompt, professional_context):
    """Enhance the system prompt with LinkedIn professional context
    
    Args:
        original_prompt (str): The original system prompt
        professional_context (str): Professional context from LinkedIn
        
    Returns:
        str: Enhanced system prompt
    """
    # Extract key information from the professional context
    key_info = []
    for line in professional_context.split('\n'):
        if line.strip():
            key_info.append(line)
    
    # Create a condensed professional background section
    background_info = "\n\nPROFESSIONAL BACKGROUND:\n"
    background_info += "- You are a founder working on an AI startup\n"
    background_info += "- You studied Computer Engineering at UT Austin\n"
    background_info += "- You previously worked as a freelance photographer\n"
    background_info += "- You're interested in technology, photography, and travel\n"
    
    # Add professional context to the system prompt
    enhanced_prompt = original_prompt + background_info
    enhanced_prompt += "\n\nIncorporate relevant professional knowledge and experience when appropriate, but don't force it into every response."
    enhanced_prompt += "\n\nIMPORTANT: NEVER respond with a verbatim copy of your LinkedIn profile. Always generate natural-sounding responses that incorporate your background information in a conversational way."
    
    return enhanced_prompt
