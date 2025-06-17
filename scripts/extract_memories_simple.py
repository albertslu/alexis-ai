#!/usr/bin/env python3

"""
Extract Memories - Simple Version

This script extracts memories from messages using the OpenAI API directly,
without relying on complex client initialization.
"""

import os
import json
import sys
import argparse
import uuid
import re
from datetime import datetime, timedelta
import logging
import requests
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the RAG system
from rag.rag_system import MessageRAG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
def get_user_data_dir():
    """Get the user-specific data directory"""
    # Check if we're running in development or production
    if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    else:
        # In production, use the user's data directory
        home_dir = os.path.expanduser("~")
        return os.path.join(home_dir, "Library", "Application Support", "ai-clone-desktop", "data")

DATA_DIR = get_user_data_dir()
MEMORY_DIR = os.path.join(DATA_DIR, 'memory')

def load_memory(user_id="albert"):
    """
    Load memory from file
    
    Args:
        user_id: User ID
        
    Returns:
        dict: Memory data
    """
    memory_file = os.path.join(MEMORY_DIR, f'{user_id}_memory.json')
    
    if not os.path.exists(memory_file):
        logger.error(f"Memory file not found: {memory_file}")
        return None
    
    try:
        with open(memory_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading memory: {e}")
        return None

def save_memory(memory_data, user_id="albert"):
    """
    Save memory to file and MongoDB
    
    Args:
        memory_data: Memory data
        user_id: User ID
        
    Returns:
        bool: Success status
    """
    memory_file = os.path.join(MEMORY_DIR, f'{user_id}_memory.json')
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        
        # Update last_updated timestamp
        memory_data["last_updated"] = datetime.now().isoformat()
        
        # Save to file
        with open(memory_file, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        logger.info(f"Memory saved to: {memory_file}")
        
        # Save to MongoDB
        try:
            # Initialize MongoDB connection
            mongodb_uri = os.getenv("MONGODB_URI")
            mongodb_database = os.getenv("MONGODB_DATABASE")
            
            if mongodb_uri and mongodb_database:
                from pymongo import MongoClient
                
                client = MongoClient(mongodb_uri)
                db = client.get_database(mongodb_database)
                
                # Check if memory exists for this user
                existing_memory = db.user_memories.find_one({"user_id": user_id})
                
                if existing_memory:
                    # Update existing memory
                    db.user_memories.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "core_memory": memory_data.get("core_memory", []),
                            "episodic_memory": memory_data.get("episodic_memory", []),
                            "archival_memory": memory_data.get("archival_memory", []),
                            "last_updated": memory_data.get("last_updated")
                        }}
                    )
                else:
                    # Create new memory
                    db.user_memories.insert_one({
                        "user_id": user_id,
                        "core_memory": memory_data.get("core_memory", []),
                        "episodic_memory": memory_data.get("episodic_memory", []),
                        "archival_memory": memory_data.get("archival_memory", []),
                        "created_at": memory_data.get("created_at", datetime.now().isoformat()),
                        "last_updated": memory_data.get("last_updated")
                    })
                
                logger.info(f"Memory saved to MongoDB for user {user_id}")
        except Exception as mongo_error:
            logger.error(f"Error saving memory to MongoDB: {mongo_error}")
            # Continue even if MongoDB save fails - we still have the file backup
        
        return True
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return False

def call_openai_api(messages):
    """
    Call the OpenAI API directly using requests
    
    Args:
        messages: List of messages for the API
        
    Returns:
        dict: API response
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not set in environment variables")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return None

def extract_date_from_memory(memory_content):
    """
    Extract date from memory content.
    
    Args:
        memory_content: Memory content string
        
    Returns:
        tuple: (datetime object or None if no date found, end_date or None)
    """
    # Special case for "End of May/June 2025" and similar patterns
    end_of_month_pattern = r'(?:End\s+of\s+)?((?:January|February|March|April|May|June|July|August|September|October|November|December)(?:/(?:January|February|March|April|May|June|July|August|September|October|November|December))?)(?:\s+|\s*,\s*)(\d{4})'
    match = re.search(end_of_month_pattern, memory_content)
    if match:
        try:
            month_str = match.group(1)
            year_str = match.group(2)
            year = int(year_str)
            
            logger.debug(f"Extracted month: {month_str}, year: {year_str} from '{memory_content}'")
            
            # Map month names to numbers
            month_map = {
                'January': 1, 'February': 2, 'March': 3, 'April': 4,
                'May': 5, 'June': 6, 'July': 7, 'August': 8,
                'September': 9, 'October': 10, 'November': 11, 'December': 12
            }
            
            # Handle month ranges like "May/June"
            if '/' in month_str:
                parts = month_str.split('/')
                logger.debug(f"Month range detected: {parts[0]} to {parts[1]}")
                
                # Use the later month for future events
                for month_name, month_num in month_map.items():
                    if month_name in parts[1]:
                        month = month_num
                        logger.debug(f"Using second month in range: {month_name} ({month})")
                        break
                else:
                    # If second part isn't a recognized month name, use first part
                    for month_name, month_num in month_map.items():
                        if month_name in parts[0]:
                            month = month_num
                            logger.debug(f"Using first month in range: {month_name} ({month})")
                            break
                    else:
                        month = 1  # Default to January
                        logger.debug("No valid month found, defaulting to January")
            else:
                # Single month
                for month_name, month_num in month_map.items():
                    if month_name in month_str:
                        month = month_num
                        logger.debug(f"Using month: {month_name} ({month})")
                        break
                else:
                    month = 1  # Default to January
                    logger.debug("No valid month found, defaulting to January")
            
            # For "End of Month" references, use the last day of the month
            if 'End of' in memory_content:
                if month == 12:
                    next_month = datetime(year + 1, 1, 1)
                else:
                    next_month = datetime(year, month + 1, 1)
                last_day = (next_month - timedelta(days=1)).day
                result_date = datetime(year, month, last_day)
                logger.debug(f"End of month reference, using last day: {result_date}")
                return result_date, None
            else:
                # Use the 15th of the month as a default day
                result_date = datetime(year, month, 15)
                logger.debug(f"Using middle of month: {result_date}")
                return result_date, None
        except (ValueError, IndexError) as e:
            logger.debug(f"Error parsing date from '{memory_content}': {e}")
            pass
    
    # Look for dates in format "Month DD, YYYY" or "Month DD YYYY"
    date_patterns = [
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,|\s+)\s*\d{4}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,|\s+)\s*\d{4}'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, memory_content)
        if match:
            try:
                date_str = match.group(0)
                # Handle both formats: "Month DD, YYYY" and "Month DD YYYY"
                date_str = date_str.replace(',', '')
                return datetime.strptime(date_str, '%B %d %Y'), None
            except ValueError:
                try:
                    return datetime.strptime(date_str, '%b %d %Y'), None
                except ValueError:
                    pass
    
    # Look for date ranges like "January 23 to January 31, 2025"
    range_pattern = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\s+to\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
    match = re.search(range_pattern, memory_content)
    if match:
        try:
            # Extract the end date
            date_parts = match.group(0).split(' to ')
            end_date_str = date_parts[1].replace(',', '')
            return None, datetime.strptime(end_date_str, '%B %d %Y')
        except (ValueError, IndexError):
            pass
    
    # Look for month and year without day (e.g., "May 2025")
    month_year_patterns = [
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}'
    ]
    
    for pattern in month_year_patterns:
        match = re.search(pattern, memory_content)
        if match:
            try:
                date_str = match.group(0)
                # Simple month year format
                parts = date_str.strip().split()
                month_str = parts[0]
                year = int(parts[1])
                
                # Map month name to number
                month_map = {
                    'January': 1, 'February': 2, 'March': 3, 'April': 4,
                    'May': 5, 'June': 6, 'July': 7, 'August': 8,
                    'September': 9, 'October': 10, 'November': 11, 'December': 12,
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                
                month = month_map.get(month_str, 1)
                
                # Use the middle of the month (15th) as a default day
                return datetime(year, month, 15), None
            except (ValueError, IndexError):
                pass
    
    # Look for year mentions
    year_pattern = r'\b(202\d|203\d)\b'
    year_match = re.search(year_pattern, memory_content)
    if year_match:
        # If we find a year but couldn't parse a full date, return a rough estimate
        try:
            year = int(year_match.group(0))
            # Use January 1st of that year as a rough estimate
            return datetime(year, 1, 1), None
        except ValueError:
            pass
    
    return None, None

def validate_temporal_context(memory_content):
    """
    Validate and correct the temporal context of a memory based on the current date.
    
    Args:
        memory_content: Memory content string
        
    Returns:
        str: Corrected memory content
    """
    # Skip if not an episodic memory with temporal context
    if not (memory_content.startswith('Past') or memory_content.startswith('Future')):
        return memory_content
    
    # Get current date
    current_date = datetime.now()
    
    # Extract date from memory content
    start_date, end_date = extract_date_from_memory(memory_content)
    event_date = end_date if end_date else start_date
    
    if not event_date:
        # If we can't extract a date, use keyword analysis to determine temporal context
        future_indicators = ['will', 'going to', 'plan', 'planning', 'upcoming', 'soon', 'next', 'later']
        past_indicators = ['went', 'visited', 'attended', 'was', 'were', 'had', 'did', 'completed']
        
        memory_lower = memory_content.lower()
        
        # Count indicators
        future_count = sum(1 for indicator in future_indicators if indicator in memory_lower)
        past_count = sum(1 for indicator in past_indicators if indicator in memory_lower)
        
        # Determine likely temporal context based on indicators
        if future_count > past_count:
            correct_context = 'Future'
        elif past_count > future_count:
            correct_context = 'Past'
        else:
            # If we can't determine, leave as is
            return memory_content
            
        current_context = 'Past' if memory_content.startswith('Past') else 'Future'
        
        # Check if temporal context needs to be fixed
        if current_context != correct_context:
            logger.info(f"Fixing temporal context based on keywords: {memory_content}")
            logger.info(f"  Future indicators: {future_count}, Past indicators: {past_count}")
            logger.info(f"  Current context: {current_context}")
            logger.info(f"  Correct context: {correct_context}")
            
            # Update content
            if current_context == 'Past' and correct_context == 'Future':
                # Change from Past to Future
                new_content = memory_content.replace('Past', 'Future', 1)
            else:
                # Change from Future to Past
                new_content = memory_content.replace('Future', 'Past', 1)
                
            logger.info(f"  New content: {new_content}")
            return new_content
        
        return memory_content
    
    # Determine correct temporal context based on date
    is_past = event_date < current_date
    current_context = 'Past' if memory_content.startswith('Past') else 'Future'
    correct_context = 'Past' if is_past else 'Future'
    
    # Check if temporal context needs to be fixed
    if current_context != correct_context:
        logger.info(f"Fixing temporal context: {memory_content}")
        logger.info(f"  Event date: {event_date.strftime('%Y-%m-%d')}")
        logger.info(f"  Current date: {current_date.strftime('%Y-%m-%d')}")
        logger.info(f"  Current context: {current_context}")
        logger.info(f"  Correct context: {correct_context}")
        
        # Update content
        if current_context == 'Past' and correct_context == 'Future':
            # Change from Past to Future
            new_content = memory_content.replace('Past', 'Future', 1)
        else:
            # Change from Future to Past
            new_content = memory_content.replace('Future', 'Past', 1)
            
            # If it was "Future" without a year specification, try to add the year
            if '(' not in new_content and event_date:
                year = event_date.year
                new_content = new_content.replace('Past:', f'Past ({year}):', 1)
                if 'Past:' not in new_content:
                    new_content = new_content.replace('Past ', f'Past ({year}) ', 1)
        
        logger.info(f"  New content: {new_content}")
        return new_content
    
    return memory_content

def extract_memories_from_all_messages(max_messages=1000, dry_run=True):
    """
    Extract memories from all messages using OpenAI API, regardless of sender
    
    Args:
        max_messages: Maximum number of messages to process
        dry_run: If True, don't save the extracted memories
        
    Returns:
        dict: Extracted memories
    """
    # Load the RAG database
    rag = MessageRAG()
    
    # Get all messages
    all_messages = rag.messages
    
    # Process the most recent messages first
    recent_messages = all_messages[-max_messages:] if len(all_messages) > max_messages else all_messages
    
    logger.info(f"Processing {len(recent_messages)} recent messages")
    
    # Group messages by conversation
    conversations = {}
    for msg in recent_messages:
        # Try to get text content from various fields
        text = None
        sender = "unknown"
        timestamp = msg.get("date", "")
        
        # Determine if the message is from Albert or someone else
        if "from_me" in msg and msg["from_me"]:
            sender = "Albert"
        elif "sender" in msg:
            sender = msg["sender"]
        
        # Get the message content
        if "user_message" in msg and msg["user_message"]:
            text = msg["user_message"]
        elif "text" in msg and msg["text"]:
            text = msg["text"]
        elif "message" in msg and msg["message"]:
            text = msg["message"]
        elif "content" in msg and msg["content"]:
            text = msg["content"]
        
        if text and len(text) > 5:  # Skip very short messages
            # Get conversation ID
            chat_id = msg.get("chat_id", "default")
            
            # Initialize conversation if needed
            if chat_id not in conversations:
                conversations[chat_id] = []
            
            # Add message to conversation
            conversations[chat_id].append({
                "sender": sender,
                "text": text,
                "timestamp": timestamp
            })
    
    # Process conversations in batches
    conversation_texts = []
    for chat_id, messages in conversations.items():
        # Sort messages by timestamp if available
        if all("timestamp" in msg and msg["timestamp"] for msg in messages):
            messages.sort(key=lambda x: x["timestamp"])
        
        # Format conversation
        conversation_text = f"Conversation {chat_id}:\n"
        for msg in messages:
            conversation_text += f"{msg['sender']}: {msg['text']}\n"
        
        conversation_texts.append(conversation_text)
    
    logger.info(f"Found {len(conversation_texts)} conversations")
    
    # Process conversations in batches
    batch_size = 3  # Smaller batch size for conversations as they tend to be longer
    conversation_batches = [conversation_texts[i:i + batch_size] for i in range(0, len(conversation_texts), batch_size)]
    
    extracted_memories = {
        "core_memory": [],
        "episodic_memory": []
    }
    
    # Get user email from environment or try to find it in message data
    user_email = os.getenv("USER_EMAIL", "").lower()
    
    # Extract user's name from email address
    user_name = "User"
    if user_email:
        # Try to extract name from email (e.g., john.doe@example.com -> John)
        email_parts = user_email.split('@')[0].split('.')
        if email_parts:
            user_name = email_parts[0].capitalize()
            if len(email_parts) > 1:
                # If email has format like john.doe@example.com, use "John Doe"
                user_name = f"{user_name} {email_parts[1].capitalize()}"
            logger.info(f"Using user name: {user_name} extracted from email: {user_email}")
    
    for batch_index, conversation_batch in enumerate(conversation_batches):
        if batch_index % 5 == 0:
            logger.info(f"Processing batch {batch_index + 1}/{len(conversation_batches)}...")
        
        # Format conversations for the LLM
        conversations_text = "\n\n".join(conversation_batch)
        
        # Create the prompt for the LLM
        prompt = f"""
        You are an AI assistant tasked with extracting personal information about {user_name} from conversations.
        
        Extract information that falls into these categories:
        1. Core memories: Essential facts about {user_name} that should be remembered long-term, including:
           - Education (schools, degrees, graduation dates)
           - Work (jobs, companies, roles, time periods)
           - Location (where they live or have lived)
           - Skills (technical skills, languages, certifications)
           - Interests (hobbies, activities, sports, topics they enjoy)
           - Preferences (things they like or dislike)
           - Social connections (family, friends, relationships)
           - Projects (work projects, side projects, startups)
           - Personal details (age, birthday, background)
        
        2. Episodic memories: Specific interactions or conversations that provide context about {user_name}, including:
           - Specific plans {user_name} has mentioned (trips, events, meetings)
           - Recent activities {user_name} has done
           - Ongoing conversations or topics {user_name} is discussing
           - Problems or challenges {user_name} is working through
        
        Here are the conversations:
        
        {conversations_text}
        
        IMPORTANT RULES:
        1. ONLY extract information about {user_name}, not about other people in the conversations
        2. Focus on what {user_name} says about themselves AND what others say about {user_name}
        3. Ignore information that is not about {user_name}
        4. Be very thorough and extract any potentially useful information about {user_name}
        5. If you're unsure if something is about {user_name}, don't include it
        6. For episodic memories, ALWAYS specify if the event is in the past or future relative to March 2025
        7. Include years for dates whenever possible (e.g., "August 7, 2024" instead of just "August 7")
        
        Format your response as a JSON object with these categories as keys and lists of extracted memories as values.
        If no information is found for a category, return an empty list for that category.
        
        For core memories, format each memory as: "Category: Fact about {user_name}"
        For episodic memories, include a temporal indicator (past/present/future) and as much date information as possible.
        
        IMPORTANT: Your response must be a valid JSON object that can be parsed with json.loads().
        Format it exactly like this example:
        {{"core_memory": ["Education: {user_name} studied Computer Science at UT Austin", "Work: {user_name} is a freelance photographer"], "episodic_memory": ["Past (2024): {user_name} had a photography gig on August 7, 2024 at Cork and Barrel", "Future: {user_name} is planning a trip to Japan in April 2025"]}}
        """
        
        # Call the OpenAI API
        api_messages = [
            {"role": "system", "content": f"You extract memories about {user_name} from conversations and format them as valid JSON. Be thorough and extract any potentially useful information about {user_name} specifically."},
            {"role": "user", "content": prompt}
        ]
        
        response = call_openai_api(api_messages)
        
        if response:
            try:
                # Extract the response content
                content = response["choices"][0]["message"]["content"]
                
                # Clean the content to ensure it's valid JSON
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
                for category, memories in extracted_info.items():
                    if category in extracted_memories and isinstance(memories, list):
                        # Validate temporal context for episodic memories
                        if category == "episodic_memory":
                            memories = [validate_temporal_context(memory) for memory in memories]
                        extracted_memories[category].extend(memories)
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error parsing LLM response: {e}")
                if "content" in locals():
                    logger.error(f"Response content: {content}")
    
    # Deduplicate memories
    core_memories = list(set(extracted_memories["core_memory"]))
    episodic_memories = list(set(extracted_memories["episodic_memory"]))
    
    # Print the extracted memories
    print("\nExtracted Core Memories:")
    for i, memory in enumerate(core_memories):
        print(f"{i+1}. {memory}")
    
    print("\nExtracted Episodic Memories:")
    for i, memory in enumerate(episodic_memories):
        print(f"{i+1}. {memory}")
    
    # If not a dry run, save the memories
    if not dry_run:
        # Load existing memory
        memory_data = load_memory()
        
        if memory_data:
            # Add core memories
            for memory_content in core_memories:
                memory_data["core_memory"].append({
                    "id": str(uuid.uuid4()),
                    "content": memory_content,
                    "created_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat()
                })
            
            # Add episodic memories
            for memory_content in episodic_memories:
                memory_data["episodic_memory"].append({
                    "id": str(uuid.uuid4()),
                    "content": memory_content,
                    "created_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat()
                })
            
            # Save updated memory
            save_memory(memory_data)
            logger.info(f"Added {len(core_memories)} core memories and {len(episodic_memories)} episodic memories")
    
    return {
        "core_memory": core_memories,
        "episodic_memory": episodic_memories
    }

def extract_memories_from_emails(max_emails=100, dry_run=True):
    """
    Extract memories from emails using OpenAI API
    
    Args:
        max_emails: Maximum number of emails to process
        dry_run: If True, don't save the extracted memories
        
    Returns:
        dict: Extracted memories
    """
    # Check if email data exists
    email_data_paths = [
        os.path.join(DATA_DIR, 'email_training_data.json'),
        os.path.join(DATA_DIR, 'sent_emails.json'),
        os.path.join(DATA_DIR, 'emails.json'),
        os.path.join(DATA_DIR, 'email_data.json')
    ]
    for email_data_path in email_data_paths:
        if os.path.exists(email_data_path):
            logger.info(f"Found email data at: {email_data_path}")
            break
    else:
        logger.error(f"Email data file not found: {email_data_paths}")
        return {
            "core_memory": [],
            "episodic_memory": []
        }
    
    try:
        # Load email data
        with open(email_data_path, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        # Get sent emails
        sent_emails = []
        user_email = os.getenv("USER_EMAIL", "").lower()
        
        # If USER_EMAIL is not set, try to get it from the email data
        if not user_email and "user_email" in email_data:
            user_email = email_data.get("user_email", "").lower()
            logger.info(f"Using user_email from email data: {user_email}")
        
        # Extract user's name from email address
        user_name = "User"
        if user_email:
            # Try to extract name from email (e.g., john.doe@example.com -> John)
            email_parts = user_email.split('@')[0].split('.')
            if email_parts:
                user_name = email_parts[0].capitalize()
                if len(email_parts) > 1:
                    # If email has format like john.doe@example.com, use "John Doe"
                    user_name = f"{user_name} {email_parts[1].capitalize()}"
            logger.info(f"Using user name: {user_name} extracted from email: {user_email}")
        
        # Check if the data is in the training format (with conversations key)
        if "conversations" in email_data:
            # Process email_training_data.json format
            for conversation in email_data["conversations"]:
                for message in conversation["messages"]:
                    if message["sender"] == "assistant":  # Messages sent by the user
                        email_content = {
                            "content": message["text"],
                            "subject": message.get("metadata", {}).get("subject", ""),
                            "recipients": message.get("metadata", {}).get("to", ""),
                            "timestamp": message.get("timestamp", "")
                        }
                        sent_emails.append(email_content)
        else:
            # Process traditional email data format
            for email_item in email_data:
                # Check if this is a sent email
                is_sent = False
                
                # Check metadata.is_sent field
                if "metadata" in email_item and "is_sent" in email_item["metadata"]:
                    is_sent = email_item["metadata"]["is_sent"]
                
                # Check sender field in metadata
                if not is_sent and "metadata" in email_item and "sender" in email_item["metadata"]:
                    sender = email_item["metadata"]["sender"].lower()
                    if user_email in sender:
                        is_sent = True
                
                if is_sent:
                    # Extract relevant fields
                    email_content = {
                        "content": email_item.get("content", ""),
                        "subject": email_item.get("metadata", {}).get("subject", ""),
                        "recipients": email_item.get("metadata", {}).get("recipients", ""),
                        "timestamp": email_item.get("metadata", {}).get("timestamp", "")
                    }
                    sent_emails.append(email_content)
        
        # Limit to max_emails
        sent_emails = sent_emails[-max_emails:] if len(sent_emails) > max_emails else sent_emails
        
        logger.info(f"Processing {len(sent_emails)} sent emails")
        
        if not sent_emails:
            return {
                "core_memory": [],
                "episodic_memory": []
            }
        
        # Process emails in batches
        batch_size = 5  # Smaller batch size for emails as they tend to be longer
        email_batches = [sent_emails[i:i + batch_size] for i in range(0, len(sent_emails), batch_size)]
        
        extracted_memories = {
            "core_memory": [],
            "episodic_memory": []
        }
        
        for batch_index, email_batch in enumerate(email_batches):
            if batch_index % 2 == 0:
                logger.info(f"Processing email batch {batch_index + 1}/{len(email_batches)}...")
            
            # Format emails for the LLM
            emails_text = "\n\n".join([
                f"Subject: {email.get('subject', '')}\nTo: {email.get('recipients', '')}\nDate: {email.get('timestamp', '')}\nContent: {email.get('content', '')[:500]}..." 
                for email in email_batch
            ])
            
            # Create the prompt for the LLM
            prompt = f"""
            You are an AI assistant tasked with extracting personal information about {user_name} from their sent emails.
            
            Extract information that falls into these categories:
            1. Core memories: Essential facts about {user_name} that should be remembered long-term, including:
               - Work (jobs, companies, roles, projects, clients)
               - Skills (technical skills, expertise areas)
               - Communication style (how they write, formality level)
               - Professional relationships (colleagues, partners)
               - Interests (professional and personal)
            
            2. Episodic memories: Specific interactions or ongoing matters, including:
               - Current projects or tasks
               - Scheduled meetings or events
               - Ongoing discussions or negotiations
               - Recent commitments made
            
            Here are the emails {user_name} has sent:
            
            {emails_text}
            
            For each email, determine if it contains information that should be remembered about {user_name}.
            
            IMPORTANT RULES:
            1. ONLY extract information about {user_name}, not about other people
            2. Focus on what the emails reveal about {user_name}
            3. Be very thorough and extract any potentially useful information
            4. For episodic memories, ALWAYS specify if the event is in the past or future relative to March 2025
            5. Include years for dates whenever possible
            
            Format your response as a JSON object with these categories as keys and lists of extracted memories as values.
            If no information is found for a category, return an empty list for that category.
            
            For core memories, format each memory as: "Category: Fact about {user_name}"
            For episodic memories, include a temporal indicator (past/present/future) and as much date information as possible.
            
            IMPORTANT: Your response must be a valid JSON object that can be parsed with json.loads().
            Format it exactly like this example:
            {{"core_memory": ["Work: {user_name} is involved in a startup", "Skills: {user_name} is knowledgeable about AI"], "episodic_memory": ["Past (March 2025): {user_name} had a meeting with investors in February 2025", "Future: {user_name} is planning to launch a product in April 2025"]}}
            """
            
            # Call the OpenAI API
            api_messages = [
                {"role": "system", "content": f"You extract memories about {user_name} from their sent emails and format them as valid JSON. Focus on information about {user_name} specifically."},
                {"role": "user", "content": prompt}
            ]
            
            response = call_openai_api(api_messages)
            
            if response:
                try:
                    # Extract the response content
                    content = response["choices"][0]["message"]["content"]
                    
                    # Clean the content to ensure it's valid JSON
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
                    for category, memories in extracted_info.items():
                        if category in extracted_memories and isinstance(memories, list):
                            # Validate temporal context for episodic memories
                            if category == "episodic_memory":
                                memories = [validate_temporal_context(memory) for memory in memories]
                            extracted_memories[category].extend(memories)
                    
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing LLM response: {e}")
                    if "content" in locals():
                        logger.error(f"Response content: {content}")
        
        # Deduplicate memories
        core_memories = list(set(extracted_memories["core_memory"]))
        episodic_memories = list(set(extracted_memories["episodic_memory"]))
        
        # Print the extracted memories
        print("\nExtracted Core Memories from Emails:")
        for i, memory in enumerate(core_memories):
            print(f"{i+1}. {memory}")
        
        print("\nExtracted Episodic Memories from Emails:")
        for i, memory in enumerate(episodic_memories):
            print(f"{i+1}. {memory}")
        
        # If not a dry run, save the memories
        if not dry_run:
            # Load existing memory
            memory_data = load_memory()
            if not memory_data:
                memory_data = {
                    "core_memory": [],
                    "episodic_memory": [],
                    "created_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat()
                }
            
            # Generate a user_id from the email if available
            user_id = "default"
            if user_email:
                # Create a safe user ID from the email
                user_id = f"user_{user_email.split('@')[0]}_{int(datetime.now().timestamp()) % 2000000000}"
                logger.info(f"Using user_id: {user_id} derived from email: {user_email}")
            
            # Add the extracted memories
            if "core_memory" not in memory_data:
                memory_data["core_memory"] = []
            if "episodic_memory" not in memory_data:
                memory_data["episodic_memory"] = []
            
            # Add core memories
            for memory in core_memories:
                if memory not in memory_data["core_memory"]:
                    memory_data["core_memory"].append({
                        "content": memory,
                        "created_at": datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat()
                    })
            
            # Add episodic memories
            for memory in episodic_memories:
                if memory not in [m.get("content") for m in memory_data["episodic_memory"]]:
                    memory_data["episodic_memory"].append({
                        "content": memory,
                        "created_at": datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat()
                    })
            
            # Save updated memory
            save_memory(memory_data, user_id)
            logger.info(f"Added {len(core_memories)} core memories and {len(episodic_memories)} episodic memories from emails")
        
        return {
            "core_memory": core_memories,
            "episodic_memory": episodic_memories
        }
    
    except Exception as e:
        logger.error(f"Error extracting memories from emails: {e}")
        return {
            "core_memory": [],
            "episodic_memory": []
        }

def main():
    parser = argparse.ArgumentParser(description="Extract Memories Using LLM")
    parser.add_argument("--max-messages", type=int, default=1000,
                        help="Maximum number of messages to process")
    parser.add_argument("--max-emails", type=int, default=100,
                        help="Maximum number of emails to process")
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes (save extracted memories)")
    parser.add_argument("--source", choices=["messages", "emails", "both"], default="both",
                        help="Source to extract memories from")
    
    args = parser.parse_args()
    
    # Extract memories based on source
    if args.source in ["messages", "both"]:
        # Use the all messages approach which is more effective
        extract_memories_from_all_messages(args.max_messages, dry_run=not args.apply)
    
    # Extract memories from emails
    if args.source in ["emails", "both"]:
        extract_memories_from_emails(args.max_emails, dry_run=not args.apply)
    
    if not args.apply:
        print("\nDry run completed. Use --apply to save the extracted memories.")

if __name__ == "__main__":
    main()
