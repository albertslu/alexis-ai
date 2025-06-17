#!/usr/bin/env python3

"""
Enhance Personal Information for AI Clone

This script enhances the personal_info.json file by extracting information from:
1. LinkedIn profile data
2. Message history
3. Email data

It helps improve the factual knowledge of the AI clone about the user.
"""

import os
import re
import json
import argparse
from datetime import datetime
import email
import mailbox
import sqlite3
from pathlib import Path
from fuzzywuzzy import fuzz
import openai
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure OpenAI client - using the latest version of the library
# Create a completely clean client with minimal parameters
http_client = httpx.Client()

# Initialize the OpenAI client with only the required parameters
openai_client = openai.OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    http_client=http_client
)

# Default paths
DEFAULT_LINKEDIN_PROFILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "scrapers/data/linkedin_profiles/albertlu_persona.json")
DEFAULT_PERSONAL_INFO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    "data/personal_info.json")
DEFAULT_CHAT_HISTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   "data/chat_history.json")
DEFAULT_EMAIL_DIR = os.path.expanduser("~/Library/Mail")
DEFAULT_EMAIL_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 "data/email_data.json")

def load_linkedin_persona(profile_path):
    """
    Load LinkedIn profile data from JSON file
    
    Args:
        profile_path: Path to LinkedIn profile JSON
        
    Returns:
        dict: LinkedIn profile data
    """
    try:
        with open(profile_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading LinkedIn profile: {e}")
        return None

def load_chat_history(chat_history_path=DEFAULT_CHAT_HISTORY):
    """
    Load chat history from JSON file
    
    Args:
        chat_history_path: Path to chat history JSON
        
    Returns:
        list: List of messages
    """
    try:
        with open(chat_history_path, 'r') as f:
            chat_data = json.load(f)
            
        # Extract messages from conversations
        messages = []
        if "conversations" in chat_data:
            for conversation in chat_data["conversations"]:
                if "messages" in conversation:
                    messages.extend(conversation["messages"])
        
        return messages
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []

def load_personal_info(personal_info_path=DEFAULT_PERSONAL_INFO_PATH):
    """
    Load personal info from JSON file
    
    Args:
        personal_info_path: Path to personal info JSON
        
    Returns:
        dict: Personal info data
    """
    try:
        with open(personal_info_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading personal info: {e}")
        return {"name": "Albert Lu", "personal_facts": [], "last_updated": datetime.now().isoformat()}

def save_personal_info(personal_info, personal_info_path=DEFAULT_PERSONAL_INFO_PATH):
    """
    Save personal info to JSON file
    
    Args:
        personal_info: Personal info data
        personal_info_path: Path to personal info JSON
        
    Returns:
        bool: Success status
    """
    try:
        # Update last_updated timestamp
        personal_info["last_updated"] = datetime.now().isoformat()
        
        with open(personal_info_path, 'w') as f:
            json.dump(personal_info, f, indent=2)
            
        print(f"Saved personal info to {personal_info_path}")
        return True
    except Exception as e:
        print(f"Error saving personal info: {e}")
        return False

def extract_facts_from_messages(messages, max_messages=1000):
    """
    Extract potential facts from message history
    
    Note: This function is kept for backward compatibility.
    Consider using extract_facts_from_messages_with_llm instead.
    
    Args:
        messages: List of message dictionaries or raw message data
        max_messages: Maximum number of messages to process
        
    Returns:
        dict: Extracted facts by category
    """
    print("Warning: Using legacy extract_facts_from_messages function.")
    print("Consider using extract_facts_from_messages_with_llm for better results.")
    
    # Initialize empty facts dictionary
    extracted_facts = {
        "work": [],
        "education": [],
        "skills": [],
        "interests": [],
        "location": [],
        "communication_style": [],
        "plans": [],
        "projects": [],
        "preferences": [],
        "social_connections": []
    }
    
    # This function is kept for backward compatibility
    # The implementation has been simplified and most hardcoded patterns removed
    # For better results, use extract_facts_from_messages_with_llm
    
    return extracted_facts

def extract_facts_from_emails(max_emails=100):
    """
    Extract facts from sent emails using the email_data.json file
    
    Note: This function is kept for backward compatibility.
    Consider using extract_facts_from_emails_with_llm instead.
    
    Args:
        max_emails: Maximum number of emails to process
        
    Returns:
        dict: Extracted facts by category
    """
    print("WARNING: extract_facts_from_emails() is deprecated. Use extract_facts_from_emails_with_llm() instead.")
    print(f"Extracting facts from up to {max_emails} sent emails...")
    
    # Initialize categories with empty lists
    categories = {
        "education": [],
        "work": [],
        "interests": [],
        "location": [],
        "skills": [],
        "communication_style": []
    }
    
    # Load email data from the existing email_data.json file
    email_data_path = DEFAULT_EMAIL_DATA
    
    if os.path.exists(email_data_path):
        try:
            with open(email_data_path, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
                
            print(f"Found {len(email_data)} emails in email_data.json")
            
            # Process only sent emails
            sent_emails = []
            for email in email_data:
                if email.get('from', '').lower() == os.getenv("USER_EMAIL", "").lower():
                    sent_emails.append(email)
            
            sent_emails = sent_emails[:max_emails]  # Limit to max_emails
            
            print(f"Processing {len(sent_emails)} sent emails")
            print("This function is deprecated. No facts will be extracted.")
            print("Please use extract_facts_from_emails_with_llm() instead.")
                
        except Exception as e:
            print(f"Error processing email_data.json: {e}")
    else:
        print(f"Email data file not found at {email_data_path}")
    
    return categories

def process_email_content(content, extracted_facts, categories, fact_patterns):
    """
    Process email content to extract facts
    
    Note: This function is kept for backward compatibility.
    It is no longer used in the main extraction flow.
    
    Args:
        content: Email content
        extracted_facts: Dictionary to store extracted facts
        categories: Categories and keywords for classification
        fact_patterns: Patterns to identify facts
    """
    # This function is kept for backward compatibility
    # but is no longer actively used
    pass

def deduplicate_facts(facts):
    """
    Remove duplicate facts and similar facts
    
    Args:
        facts: Dictionary of facts by category
        
    Returns:
        dict: Deduplicated facts
    """
    deduplicated_facts = {}
    
    for category, fact_list in facts.items():
        # Sort facts by length (longer facts first)
        sorted_facts = sorted(fact_list, key=len, reverse=True)
        
        # Remove duplicates and similar facts
        unique_facts = []
        for fact in sorted_facts:
            # Clean the fact
            cleaned_fact = fact.strip()
            
            # Skip if fact is too short
            if len(cleaned_fact) < 5:
                continue
            
            # Check if this fact is similar to any existing fact
            is_similar = False
            for existing_fact in unique_facts:
                # If the fact is contained within an existing fact, skip it
                if cleaned_fact.lower() in existing_fact.lower():
                    is_similar = True
                    break
                
                # If the fact is very similar to an existing fact, skip it
                similarity = calculate_similarity(cleaned_fact.lower(), existing_fact.lower())
                if similarity > 0.8:  # 80% similarity threshold
                    is_similar = True
                    break
            
            if not is_similar:
                unique_facts.append(cleaned_fact)
        
        if unique_facts:
            deduplicated_facts[category] = unique_facts
    
    return deduplicated_facts

def calculate_similarity(str1, str2):
    """
    Calculate similarity between two strings
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        float: Similarity score (0-1)
    """
    # Simple similarity calculation based on common words
    words1 = set(str1.split())
    words2 = set(str2.split())
    
    common_words = words1.intersection(words2)
    
    if not words1 or not words2:
        return 0
    
    return len(common_words) / max(len(words1), len(words2))

def clean_linkedin_facts(facts):
    """
    Clean LinkedIn facts to ensure they're in a consistent format
    
    Args:
        facts: Dictionary of facts by category
        
    Returns:
        dict: Cleaned facts
    """
    cleaned_facts = {}
    
    for category, fact_list in facts.items():
        cleaned_list = []
        for fact in fact_list:
            # Remove newlines and duplicate information
            cleaned_fact = fact.split("\n")[0] if "\n" in fact else fact
            
            # Skip very short facts
            if len(cleaned_fact.split()) < 3:
                continue
                
            # Clean up formatting
            cleaned_fact = cleaned_fact.strip()
            
            # Add to cleaned list if not already present
            if cleaned_fact and cleaned_fact not in cleaned_list:
                cleaned_list.append(cleaned_fact)
        
        if cleaned_list:
            cleaned_facts[category] = cleaned_list
    
    return cleaned_facts

def extract_facts_from_linkedin(profile_path=DEFAULT_LINKEDIN_PROFILE):
    """
    Extract facts from LinkedIn profile
    
    Args:
        profile_path: Path to LinkedIn profile JSON
        
    Returns:
        dict: Extracted facts by category
    """
    print(f"Extracting facts from LinkedIn profile: {profile_path}")
    
    # Load LinkedIn profile
    linkedin_data = load_linkedin_persona(profile_path)
    if not linkedin_data:
        print("Failed to load LinkedIn profile data")
        return {}
    
    # Extract facts by category
    facts = {
        "education": [],
        "work": [],
        "professional": [],
        "location": []
    }
    
    # Basic info
    if "basic_info" in linkedin_data:
        basic_info = linkedin_data["basic_info"]
        if "name" in basic_info:
            facts["professional"].append(f"Full name is {basic_info['name']}")
        if "headline" in basic_info:
            facts["professional"].append(f"{basic_info['headline']}")
        if "location" in basic_info:
            facts["location"].append(f"Based in {basic_info['location']}")
    
    # Education
    if "education" in linkedin_data:
        for edu in linkedin_data["education"]:
            school = edu.get("school", "")
            degree = edu.get("degree", "").split("\n")[0] if edu.get("degree") else ""
            dates = edu.get("dates", "").split("\n")[0] if edu.get("dates") else ""
            
            if school and degree:
                facts["education"].append(f"Studied {degree} at {school}")
            if school and dates:
                facts["education"].append(f"Attended {school} during {dates}")
    
    # Experience
    if "experience" in linkedin_data:
        for exp in linkedin_data["experience"]:
            title = exp.get("title", "")
            company = exp.get("company", "").split("\n")[0] if exp.get("company") else ""
            duration = exp.get("duration", "").split("\n")[0] if exp.get("duration") else ""
            
            if title and company:
                facts["work"].append(f"{title} at {company}")
            if title and company and duration:
                facts["work"].append(f"{title} at {company} for {duration}")
    
    # Clean the facts
    facts = clean_linkedin_facts(facts)
    
    # Count facts
    fact_count = sum(len(facts_list) for facts_list in facts.values())
    print(f"Extracted {fact_count} facts from LinkedIn profile")
    
    return facts

def merge_facts_with_personal_info(new_facts, personal_info_path=DEFAULT_PERSONAL_INFO_PATH):
    """
    Merge new facts with existing personal info
    
    Args:
        new_facts: Dictionary of new facts by category
        personal_info_path: Path to personal info JSON
        
    Returns:
        dict: Updated personal info
    """
    print(f"Merging facts with personal info at {personal_info_path}")
    
    # Load existing personal info
    personal_info = load_personal_info(personal_info_path)
    
    # Initialize personal_facts if not present
    if "personal_facts" not in personal_info:
        personal_info["personal_facts"] = []
    
    # Track how many new facts were added
    new_fact_count = 0
    
    # Merge new facts with existing facts
    for category, facts in new_facts.items():
        # Find existing category in personal_facts
        category_found = False
        for fact_category in personal_info["personal_facts"]:
            if fact_category.get("category") == category:
                # Category exists, add new facts
                existing_facts = set(fact_category.get("facts", []))
                for fact in facts:
                    if fact not in existing_facts:
                        fact_category["facts"].append(fact)
                        new_fact_count += 1
                category_found = True
                break
        
        if not category_found and facts:
            # Category doesn't exist, add it
            personal_info["personal_facts"].append({
                "category": category,
                "facts": facts
            })
            new_fact_count += len(facts)
    
    # Deduplicate facts in personal_info
    deduplicated_personal_facts = []
    for fact_category in personal_info["personal_facts"]:
        category = fact_category.get("category")
        facts = fact_category.get("facts", [])
        
        # Deduplicate facts within this category
        deduplicated_facts = deduplicate_facts({category: facts})
        
        if category in deduplicated_facts and deduplicated_facts[category]:
            deduplicated_personal_facts.append({
                "category": category,
                "facts": deduplicated_facts[category]
            })
    
    # Update personal_facts with deduplicated facts
    personal_info["personal_facts"] = deduplicated_personal_facts
    
    print(f"Added {new_fact_count} new facts to personal info")
    
    return personal_info

def extract_facts_from_messages_with_llm(messages, max_messages=1000):
    """
    Extract personal information from messages using an LLM
    
    Args:
        messages: List of message dictionaries or raw message data
        max_messages: Maximum number of messages to process
        
    Returns:
        dict: Extracted personal information by category
    """
    print(f"Extracting personal information from up to {max_messages} messages using LLM...")
    
    # Check if messages is a list of dictionaries or a string (raw JSON)
    if isinstance(messages, str):
        try:
            # Try to parse the string as JSON
            messages = json.loads(messages)
        except:
            print("Error parsing messages as JSON")
            return {}
    
    # Handle different message formats
    processed_messages = []
    
    # Check if we have a list of messages or a dictionary with a messages key
    if isinstance(messages, dict) and 'messages' in messages:
        messages = messages['messages']
    
    # Handle iMessage format where messages are grouped by contact
    if isinstance(messages, list) and len(messages) > 0 and isinstance(messages[0], dict) and 'contact' in messages[0] and 'messages' in messages[0]:
        print("Detected iMessage format with messages grouped by contact")
        for contact_group in messages:
            contact_messages = contact_group.get('messages', [])
            for message in contact_messages:
                if 'is_from_me' in message and 'text' in message:
                    processed_messages.append({
                        'sender': 'user' if message.get('is_from_me') else 'other',
                        'text': message.get('text', ''),
                        'timestamp': message.get('timestamp', '')
                    })
    else:
        # Process each message based on its format
        for message in messages:
            if isinstance(message, dict):
                # Standard format with sender and text
                if 'sender' in message and 'text' in message:
                    processed_messages.append({
                        'sender': message['sender'],
                        'text': message['text'],
                        'timestamp': message.get('timestamp', '')
                    })
                # iMessage format
                elif 'is_from_me' in message and 'text' in message:
                    processed_messages.append({
                        'sender': 'user' if message.get('is_from_me') else 'other',
                        'text': message['text'],
                        'timestamp': message.get('timestamp', '')
                    })
                # Another possible format
                elif 'from_me' in message and 'message' in message:
                    processed_messages.append({
                        'sender': 'user' if message.get('from_me') else 'other',
                        'text': message['message'],
                        'timestamp': message.get('timestamp', '')
                    })
    
    # Process the most recent messages first
    recent_messages = processed_messages[-max_messages:] if len(processed_messages) > max_messages else processed_messages
    
    print(f"Processing {len(recent_messages)} messages")
    
    # Filter to only include messages sent by the user
    user_messages = [msg for msg in recent_messages if msg.get('sender') == 'user']
    
    print(f"Found {len(user_messages)} messages sent by the user")
    
    # Define the categories we want to extract
    categories = {
        "plans": [],
        "projects": [],
        "interests": [],
        "preferences": [],
        "social_connections": []
    }
    
    # Process messages in batches to avoid exceeding token limits
    batch_size = 10
    message_batches = [user_messages[i:i + batch_size] for i in range(0, len(user_messages), batch_size)]
    
    for batch_index, message_batch in enumerate(message_batches):
        if batch_index % 5 == 0:
            print(f"Processing batch {batch_index + 1}/{len(message_batches)}...")
        
        # Format messages for the LLM
        messages_text = "\n\n".join([f"Message: {msg.get('text')}" for msg in message_batch])
        
        # Create the prompt for the LLM
        prompt = f"""
        You are an AI assistant tasked with extracting personal information from a user's messages.
        
        Extract information that falls into these categories:
        1. Plans: Future activities, events, trips, or goals the user mentions. Only include REAL plans, not hypothetical ones or jokes.
        2. Projects: Work, startups, apps, or other initiatives the user is working on. Focus on ACTUAL projects, not gaming or fictional references.
        3. Interests: Hobbies, activities, sports, or topics the user enjoys
        4. Preferences: Things the user likes, dislikes, or has opinions about. Only include GENUINE preferences, not jokes or sarcasm.
        5. Social Connections: Information about the user's relationships, friends, family, or social network
        
        Here are the messages:
        
        {messages_text}
        
        Extract ONLY factual information about the user themselves. Do not include hypotheticals, jokes, or information about other people.
        Filter out low-quality information such as:
        - Very short or incomplete statements
        - Casual expressions like "lol", "haha", etc.
        - Statements that are questions or directed at others
        - URLs or email addresses
        - Statements that don't contain meaningful personal information
        - Fictional references
        - Jokes or sarcastic statements
        
        Format your response as a JSON object with these categories as keys and lists of extracted facts as values.
        If no information is found for a category, return an empty list for that category.
        
        IMPORTANT: Your response must be a valid JSON object that can be parsed with json.loads().
        Format it exactly like this example:
        {{"plans": ["Plan 1", "Plan 2"], "projects": ["Project 1"], "interests": [], "preferences": ["Preference 1"], "social_connections": []}}
        """
        
        try:
            # Call the OpenAI API using the new client syntax
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # Use the latest GPT-4o model for better accuracy
                messages=[
                    {"role": "system", "content": "You extract personal information from messages and format it as valid JSON. Be very careful to distinguish between real facts and jokes/hypotheticals/gaming references."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for more factual responses
                max_tokens=1000
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            
            # Parse the JSON response
            try:
                # Clean the content to ensure it's valid JSON
                # Remove any markdown formatting or extra text
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                extracted_info = json.loads(content)
                
                # Add the extracted information to our categories
                for category, facts in extracted_info.items():
                    if category in categories and isinstance(facts, list):
                        categories[category].extend(facts)
                
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON response from LLM for batch {batch_index + 1}: {e}")
                print(f"Raw response: {content[:100]}...")
                
        except Exception as e:
            print(f"Error calling OpenAI API for batch {batch_index + 1}: {e}")
    
    # Remove duplicates
    for category in categories:
        categories[category] = list(set(categories[category]))
    
    print(f"Extracted {sum(len(facts) for facts in categories.values())} personal information items across all categories")
    
    return categories

def extract_facts_from_emails_with_llm(max_emails=100):
    """
    Extract facts from sent emails using the email_data.json file and LLM
    
    Args:
        max_emails: Maximum number of emails to process
        
    Returns:
        dict: Extracted facts by category
    """
    print(f"Extracting personal information from up to {max_emails} emails using LLM...")
    
    # Initialize categories
    categories = {
        "work": [],
        "education": [],
        "skills": [],
        "interests": [],
        "location": [],
        "communication_style": [],
        "plans": [],
        "projects": [],
        "preferences": [],
        "social_connections": []
    }
    
    # Check if email_data.json exists
    if not os.path.exists(DEFAULT_EMAIL_DATA):
        print(f"Email data file not found: {DEFAULT_EMAIL_DATA}")
        return categories
    
    try:
        # Load email data
        with open(DEFAULT_EMAIL_DATA, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        # Get sent emails
        sent_emails = []
        for email_item in email_data:
            if email_item.get('from', '').lower() == os.getenv("USER_EMAIL", "").lower():
                sent_emails.append(email_item)
        
        # Limit to max_emails
        sent_emails = sent_emails[:max_emails]
        
        print(f"Processing {len(sent_emails)} sent emails")
        
        # Process emails in batches to avoid exceeding token limits
        batch_size = 5  # Smaller batch size for emails as they tend to be longer
        email_batches = [sent_emails[i:i + batch_size] for i in range(0, len(sent_emails), batch_size)]
        
        for batch_index, email_batch in enumerate(email_batches):
            if batch_index % 2 == 0:
                print(f"Processing email batch {batch_index + 1}/{len(email_batches)}...")
            
            # Format emails for the LLM
            emails_text = "\n\n".join([
                f"Email Subject: {email_item.get('subject', 'No Subject')}\n"
                f"Email Content: {email_item.get('body', '')}"
                for email_item in email_batch
            ])
            
            # Create the prompt for the LLM
            prompt = f"""
            You are an AI assistant tasked with extracting personal information from a user's sent emails.
            
            Extract information that falls into these categories:
            1. Work: Professional information, job details, company information
            2. Education: Schools, degrees, courses, academic achievements
            3. Skills: Technical abilities, professional competencies
            4. Interests: Hobbies, activities, topics the user enjoys
            5. Location: Where the user lives or has lived
            6. Communication Style: How the user writes and communicates
            7. Plans: Future activities, events, trips, or goals the user mentions. Only include REAL plans, not hypothetical ones.
            8. Projects: Work, startups, apps, or other initiatives the user is working on. Focus on ACTUAL projects.
            9. Preferences: Things the user likes, dislikes, or has opinions about. Only include GENUINE preferences.
            10. Social Connections: Information about the user's relationships, colleagues, network
            
            Here are the emails the user has sent:
            
            {emails_text}
            
            Extract ONLY factual information about the user themselves. Do not include hypotheticals, jokes, or information about other people unless it directly relates to the user's social connections.
            Filter out low-quality information such as:
            - Very short or incomplete statements
            - Casual expressions like "lol", "haha", etc.
            - Statements that don't contain meaningful personal information
            - References to fictional scenarios
            - Jokes or sarcastic statements
            
            Format your response as a JSON object with these categories as keys and lists of extracted facts as values.
            If no information is found for a category, return an empty list for that category.
            
            IMPORTANT: Your response must be a valid JSON object that can be parsed with json.loads().
            Format it exactly like this example:
            {{"work": ["Work fact 1", "Work fact 2"], "education": ["Education fact 1"], "skills": [], "interests": ["Interest 1"], "location": [], "communication_style": [], "plans": [], "projects": [], "preferences": [], "social_connections": []}}
            """
            
            try:
                # Call the OpenAI API using the new client syntax
                response = openai_client.chat.completions.create(
                    model="gpt-4o",  # Use the latest GPT-4o model for better accuracy
                    messages=[
                        {"role": "system", "content": "You extract personal information from emails and format it as valid JSON. Be very careful to distinguish between real facts and hypotheticals."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,  # Low temperature for more factual responses
                    max_tokens=1000
                )
                
                # Extract the response content
                content = response.choices[0].message.content
                
                # Parse the JSON response
                try:
                    # Clean the content to ensure it's valid JSON
                    # Remove any markdown formatting or extra text
                    content = content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    extracted_info = json.loads(content)
                    
                    # Add the extracted information to our categories
                    for category, facts in extracted_info.items():
                        if category in categories and isinstance(facts, list):
                            categories[category].extend(facts)
                    
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON response from LLM for email batch {batch_index + 1}: {e}")
                    print(f"Raw response: {content[:100]}...")
                    
            except Exception as e:
                print(f"Error calling OpenAI API for email batch {batch_index + 1}: {e}")
        
        # Remove duplicates
        for category in categories:
            categories[category] = list(set(categories[category]))
        
        print(f"Extracted {sum(len(facts) for facts in categories.values())} personal information items from emails across all categories")
        
    except Exception as e:
        print(f"Error extracting facts from emails: {e}")
    
    return categories

def enhance_personal_info(linkedin_profile_path=None, max_messages=1000, max_emails=100, use_llm=True):
    """
    Enhance personal info with facts from LinkedIn profile, messages, and emails
    
    Args:
        linkedin_profile_path: Path to LinkedIn profile JSON
        max_messages: Maximum number of messages to process
        max_emails: Maximum number of emails to process
        use_llm: Whether to use LLM for fact extraction
    """
    print("Starting personal info enhancement process...")
    
    # Extract facts from LinkedIn profile
    linkedin_facts = {}
    if linkedin_profile_path:
        print(f"Extracting facts from LinkedIn profile: {linkedin_profile_path}")
        linkedin_facts = extract_facts_from_linkedin(linkedin_profile_path)
    
    # Extract facts from messages
    message_facts = {}
    try:
        # Try to load the most recent iMessage data first
        imessage_data_path = os.path.join(os.path.dirname(DEFAULT_PERSONAL_INFO_PATH), "imessage_raw_20250318_122605.json")
        if os.path.exists(imessage_data_path):
            print(f"Loading iMessage data from {imessage_data_path}")
            with open(imessage_data_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            if use_llm:
                message_facts = extract_facts_from_messages_with_llm(messages, max_messages)
            else:
                message_facts = extract_facts_from_messages(messages, max_messages)
        else:
            # Fall back to regular chat history
            print(f"Loading message history from {DEFAULT_CHAT_HISTORY}")
            with open(DEFAULT_CHAT_HISTORY, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            if use_llm:
                message_facts = extract_facts_from_messages_with_llm(messages, max_messages)
            else:
                message_facts = extract_facts_from_messages(messages, max_messages)
    except Exception as e:
        print(f"Error extracting facts from messages: {e}")
    
    # Extract facts from emails
    email_facts = {}
    try:
        if use_llm:
            email_facts = extract_facts_from_emails_with_llm(max_emails)
        else:
            email_facts = extract_facts_from_emails(max_emails)
    except Exception as e:
        print(f"Error extracting facts from emails: {e}")
    
    # Merge facts
    all_facts = {}
    for facts in [linkedin_facts, message_facts, email_facts]:
        for category, fact_list in facts.items():
            if category not in all_facts:
                all_facts[category] = []
            all_facts[category].extend(fact_list)
    
    # Deduplicate facts (no need to filter since LLM does the filtering)
    deduped_facts = deduplicate_facts(all_facts)
    
    # Load existing personal info
    print(f"Merging facts with personal info at {DEFAULT_PERSONAL_INFO_PATH}")
    personal_info = load_personal_info()
    
    # Update personal info with new facts
    facts_added = 0
    for category, fact_list in deduped_facts.items():
        # Find or create category in personal_facts
        category_found = False
        for category_obj in personal_info.get('personal_facts', []):
            if category_obj.get('category') == category:
                # Add new facts to existing category
                existing_facts = set(category_obj.get('facts', []))
                for fact in fact_list:
                    if fact not in existing_facts:
                        category_obj['facts'].append(fact)
                        facts_added += 1
                category_found = True
                break
        
        if not category_found and fact_list:
            # Create new category
            personal_info.setdefault('personal_facts', []).append({
                'category': category,
                'facts': fact_list
            })
            facts_added += len(fact_list)
    
    # Update last_updated timestamp
    personal_info['last_updated'] = datetime.now().isoformat()
    
    # Save updated personal info
    save_personal_info(personal_info)
    print(f"Added {facts_added} new facts to personal info")
    print("Personal info enhancement completed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhance personal info for AI Clone")
    parser.add_argument("--linkedin", help="Path to LinkedIn profile JSON", default=DEFAULT_LINKEDIN_PROFILE)
    parser.add_argument("--max-messages", type=int, help="Maximum number of messages to process", default=1000)
    parser.add_argument("--max-emails", type=int, help="Maximum number of emails to process", default=100)
    parser.add_argument("--clean", action="store_true", help="Start with a clean personal info file")
    parser.add_argument("--no-llm", action="store_true", help="Don't use LLM for fact extraction")
    
    args = parser.parse_args()
    
    # Start with a clean personal info file if requested
    if args.clean:
        print("Starting with a clean personal info file...")
        personal_info = {
            "name": "Albert Lu",
            "personal_facts": []
        }
        save_personal_info(personal_info)
    
    # Enhance personal info
    enhance_personal_info(
        linkedin_profile_path=args.linkedin,
        max_messages=args.max_messages,
        max_emails=args.max_emails,
        use_llm=not args.no_llm
    )
