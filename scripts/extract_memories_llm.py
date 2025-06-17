#!/usr/bin/env python3

"""
Extract Memories Using LLM

This script extracts memories from messages and emails using an LLM,
similar to how personal_info.json is created, but formatted for the memory system.
"""

import os
import json
import sys
import argparse
import uuid
from datetime import datetime
import logging
import openai
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the memory-enhanced RAG system
from rag.memory_enhanced_rag import MemoryEnhancedRAG
from rag.rag_system import MessageRAG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MEMORY_DIR = os.path.join(DATA_DIR, 'memory')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')
RAG_DB_PATH = os.path.join(DATA_DIR, 'rag', 'default_message_db.json')
DEFAULT_EMAIL_DATA = os.path.join(DATA_DIR, 'email_data.json')

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
    Save memory to file
    
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
        
        with open(memory_file, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        logger.info(f"Memory saved to: {memory_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return False

def extract_memories_from_messages(max_messages=500, dry_run=True):
    """
    Extract memories from messages using LLM
    
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
    
    # Filter to user messages only
    user_messages = []
    for msg in recent_messages:
        if "user_message" in msg and msg["user_message"]:
            user_messages.append({
                "text": msg["user_message"],
                "ai_response": msg.get("ai_message", "")
            })
    
    logger.info(f"Found {len(user_messages)} user messages")
    
    # Process messages in batches
    batch_size = 10
    message_batches = [user_messages[i:i + batch_size] for i in range(0, len(user_messages), batch_size)]
    
    extracted_memories = {
        "core_memory": [],
        "episodic_memory": []
    }
    
    for batch_index, message_batch in enumerate(message_batches):
        if batch_index % 5 == 0:
            logger.info(f"Processing batch {batch_index + 1}/{len(message_batches)}...")
        
        # Format messages for the LLM
        messages_text = "\n\n".join([
            f"User: {msg.get('text', '')}\nAI: {msg.get('ai_response', '')}" 
            for msg in message_batch
        ])
        
        # Create the prompt for the LLM
        prompt = f"""
        You are an AI assistant tasked with extracting personal information from a user's messages.
        
        Extract information that falls into these categories:
        1. Core memories: Essential facts about the user that should be remembered long-term, including:
           - Education (schools, degrees, graduation dates)
           - Work (jobs, companies, roles, time periods)
           - Location (where they live or have lived)
           - Skills (technical skills, languages, certifications)
           - Interests (hobbies, activities, sports, topics they enjoy)
           - Preferences (things they like or dislike)
           - Social connections (family, friends, relationships)
           - Projects (work projects, side projects, startups)
           - Personal details (age, birthday, background)
        
        2. Episodic memories: Specific interactions or conversations that provide context, including:
           - Specific plans they've mentioned (trips, events, meetings)
           - Recent activities they've done
           - Ongoing conversations or topics they're discussing
           - Problems or challenges they're working through
        
        Here are the messages:
        
        {messages_text}
        
        For each message, determine if it contains information that should be remembered.
        Be very thorough and extract any potentially useful information.
        
        Format your response as a JSON object with these categories as keys and lists of extracted memories as values.
        If no information is found for a category, return an empty list for that category.
        
        For core memories, format each memory as: "Category: Fact about the user"
        For episodic memories, just include the relevant information.
        
        IMPORTANT: Your response must be a valid JSON object that can be parsed with json.loads().
        Format it exactly like this example:
        {{"core_memory": ["Education: The user studied Computer Science at UT Austin", "Work: The user is a freelance photographer"], "episodic_memory": ["The user is planning a trip to Japan next month", "The user is working on a new photography project"]}}
        """
        
        try:
            # Call the OpenAI API
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You extract memories from messages and format them as valid JSON. Be thorough and extract any potentially useful information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            
            # Parse the JSON response
            try:
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
                        extracted_memories[category].extend(memories)
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response: {e}")
                logger.error(f"Response content: {content}")
        
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
    
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
    Extract memories from emails using LLM
    
    Args:
        max_emails: Maximum number of emails to process
        dry_run: If True, don't save the extracted memories
        
    Returns:
        dict: Extracted memories
    """
    # Check if email_data.json exists
    if not os.path.exists(DEFAULT_EMAIL_DATA):
        logger.error(f"Email data file not found: {DEFAULT_EMAIL_DATA}")
        return {
            "core_memory": [],
            "episodic_memory": []
        }
    
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
        
        logger.info(f"Processing {len(sent_emails)} sent emails")
        
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
                f"Subject: {email.get('subject', '')}\nTo: {email.get('to', '')}\nContent: {email.get('content', '')[:500]}..." 
                for email in email_batch
            ])
            
            # Create the prompt for the LLM
            prompt = f"""
            You are an AI assistant tasked with extracting personal information from a user's sent emails.
            
            Extract information that falls into these categories:
            1. Core memories: Essential facts about the user that should be remembered long-term, including:
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
            
            Here are the emails the user has sent:
            
            {emails_text}
            
            For each email, determine if it contains information that should be remembered.
            Focus on extracting information about the sender (the user), not about the recipients.
            
            Format your response as a JSON object with these categories as keys and lists of extracted memories as values.
            If no information is found for a category, return an empty list for that category.
            
            For core memories, format each memory as: "Category: Fact about the user"
            For episodic memories, just include the relevant information.
            
            IMPORTANT: Your response must be a valid JSON object that can be parsed with json.loads().
            Format it exactly like this example:
            {{"core_memory": ["Work: The user works as a project manager at TechCorp", "Skills: The user is proficient in data analysis"], "episodic_memory": ["The user is leading the Q2 marketing campaign", "The user has a meeting with the design team on Friday"]}}
            """
            
            try:
                # Call the OpenAI API
                response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You extract memories from emails and format them as valid JSON. Focus on information about the sender."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1000
                )
                
                # Extract the response content
                content = response.choices[0].message.content
                
                # Parse the JSON response
                try:
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
                            extracted_memories[category].extend(memories)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing LLM response: {e}")
                    logger.error(f"Response content: {content}")
            
            except Exception as e:
                logger.error(f"Error calling OpenAI API: {e}")
        
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
    parser.add_argument("--source", choices=["messages", "emails", "both"], default="both",
                        help="Source to extract memories from")
    parser.add_argument("--max-messages", type=int, default=500,
                        help="Maximum number of messages to process")
    parser.add_argument("--max-emails", type=int, default=100,
                        help="Maximum number of emails to process")
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes (save extracted memories)")
    
    args = parser.parse_args()
    
    # Extract memories from messages
    if args.source in ["messages", "both"]:
        extract_memories_from_messages(args.max_messages, dry_run=not args.apply)
    
    # Extract memories from emails
    if args.source in ["emails", "both"]:
        extract_memories_from_emails(args.max_emails, dry_run=not args.apply)
    
    if not args.apply:
        print("\nDry run completed. Use --apply to save the extracted memories.")

if __name__ == "__main__":
    main()
