#!/usr/bin/env python3

"""
RAG Database Cleanup Script

This script cleans the RAG database by removing:
1. Test messages (hello, hi, test, etc.)
2. Very short messages (less than 10 characters)
3. Messages from chat_history.json that contradict memory facts
4. Generic responses that don't provide value

It creates a backup of the original database before making changes.
"""

import os
import json
import sys
import re
import shutil
from datetime import datetime, timedelta

# Add parent directory to path to import RAG modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RAG_DIR = os.path.join(DATA_DIR, 'rag')
MEMORY_DIR = os.path.join(DATA_DIR, 'memory')
MEMORY_FILE = os.path.join(MEMORY_DIR, 'albert_memory.json')
RAG_DB_PATH = os.path.join(RAG_DIR, 'default_message_db.json')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')

def load_json_file(file_path):
    """Load a JSON file and return its contents."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {str(e)}")
        return None

def save_json_file(file_path, data):
    """Save data to a JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving to {file_path}: {str(e)}")
        return False

def backup_database(file_path):
    """Create a backup of the database file."""
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"Created backup at {backup_path}")
        return True
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        return False

def clean_rag_database():
    """Clean the RAG database by removing unwanted messages."""
    # Load RAG database
    rag_db = load_json_file(RAG_DB_PATH)
    if not rag_db:
        print("Failed to load RAG database")
        return
    
    # Load memory file to check for contradictions
    memory_data = load_json_file(MEMORY_FILE)
    if not memory_data:
        print("Failed to load memory file")
        return
    
    # Extract travel-related memories for contradiction checking
    travel_memories = []
    for memory_type in ['core_memory', 'episodic_memory']:
        for memory in memory_data.get(memory_type, []):
            content = memory.get('content', '').lower()
            if 'travel' in content or 'trip' in content or 'middle east' in content or 'lebanon' in content:
                travel_memories.append(content)
    
    # Define criteria for messages to keep or remove
    test_phrases = ['hello', 'hi', 'test', 'hey', 'shalom']
    generic_responses = ['yes', 'no', 'maybe', 'ok', 'sure', 'thanks']
    contradictory_phrases = ['no travel plans', 'not traveling', 'staying in austin', 'no trips']
    
    # Counters for statistics
    total_messages = len(rag_db.get('messages', []))
    messages_to_remove = []
    cleaned_messages = []
    
    # Analyze each message
    for i, msg in enumerate(rag_db.get('messages', [])):
        text = msg.get('text', '').lower().strip()
        should_remove = False
        reason = None
        
        # Check if it's a test message
        if any(phrase == text for phrase in test_phrases):
            should_remove = True
            reason = "Test message"
        
        # Check if it's too short
        elif len(text) < 10:
            should_remove = True
            reason = "Too short"
        
        # Check if it's a generic response
        elif text in generic_responses:
            should_remove = True
            reason = "Generic response"
        
        # Check if it contradicts memory facts
        elif any(phrase in text for phrase in contradictory_phrases):
            # Only remove if we have travel memories that contradict this
            if travel_memories:
                should_remove = True
                reason = "Contradicts memory facts about travel"
        
        # Track the message
        if should_remove:
            messages_to_remove.append((i, msg, reason))
        else:
            cleaned_messages.append(msg)
    
    # Print statistics
    print(f"RAG Database Cleanup")
    print(f"===================")
    print(f"Total messages: {total_messages}")
    print(f"Messages kept: {len(cleaned_messages)}")
    print(f"Messages removed: {len(messages_to_remove)}")
    print()
    
    # Create a backup before modifying
    if not backup_database(RAG_DB_PATH):
        print("Failed to create backup. Aborting cleanup.")
        return
    
    # Update the database with cleaned messages
    rag_db['messages'] = cleaned_messages
    
    # Save the cleaned database
    if save_json_file(RAG_DB_PATH, rag_db):
        print(f"Successfully cleaned RAG database. Removed {len(messages_to_remove)} messages.")
    else:
        print("Failed to save cleaned database.")

if __name__ == "__main__":
    # Ask for confirmation
    confirmation = input("This will clean the RAG database by removing test messages and contradictory information. Continue? (y/n): ")
    if confirmation.lower() == 'y':
        clean_rag_database()
    else:
        print("Operation cancelled.")
