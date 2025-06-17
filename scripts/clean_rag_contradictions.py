#!/usr/bin/env python3

"""
RAG Database Contradiction Cleanup Script

This script specifically targets and removes messages in the RAG database that contradict
important facts in your memory, particularly about travel plans. It focuses on messages
from the chat interface with the clone, not from iMessage conversations.

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

def clean_rag_contradictions(dry_run=True):
    """
    Clean contradictions from the RAG database.
    
    Args:
        dry_run: If True, only show what would be removed without making changes
    """
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
    
    print(f"Found {len(travel_memories)} travel-related memories:")
    for memory in travel_memories:
        print(f"- {memory}")
    print()
    
    # Define contradictory phrases specifically about travel plans
    contradictory_phrases = [
        'no travel plans', 
        'not traveling', 
        'not planning to travel',
        'staying in austin',
        'no trips',
        'not really planning',
        'not going anywhere',
        'no plans to travel',
        'not going to travel'
    ]
    
    # Counters for statistics
    total_messages = len(rag_db.get('messages', []))
    messages_to_remove = []
    cleaned_messages = []
    
    # Analyze each message
    for i, msg in enumerate(rag_db.get('messages', [])):
        text = msg.get('text', '').lower().strip()
        should_remove = False
        reason = None
        
        # Check if it contradicts memory facts about travel
        if any(phrase in text for phrase in contradictory_phrases):
            should_remove = True
            reason = "Contradicts memory facts about travel"
            
            # Find which phrase matched
            matching_phrases = [phrase for phrase in contradictory_phrases if phrase in text]
            reason += f" (matched: {', '.join(matching_phrases)})"
        
        # Track the message
        if should_remove:
            messages_to_remove.append((i, msg, reason))
        else:
            cleaned_messages.append(msg)
    
    # Print statistics
    print(f"RAG Database Contradiction Analysis")
    print(f"==================================")
    print(f"Total messages: {total_messages}")
    print(f"Contradictory messages found: {len(messages_to_remove)}")
    print()
    
    # Print messages to remove
    print(f"Messages that {'would be' if dry_run else 'will be'} removed:")
    for i, (idx, msg, reason) in enumerate(messages_to_remove):
        text = msg.get('text', '')
        if len(text) > 50:
            text = text[:47] + "..."
        print(f"{i+1}. [{reason}] '{text}'")
    
    if dry_run:
        print("\nThis is a dry run. No changes have been made to the database.")
        print("To actually clean the database, run with --apply parameter.")
        return
    
    # Create a backup before modifying
    if not backup_database(RAG_DB_PATH):
        print("Failed to create backup. Aborting cleanup.")
        return
    
    # Update the database with cleaned messages
    rag_db['messages'] = cleaned_messages
    
    # Save the cleaned database
    if save_json_file(RAG_DB_PATH, rag_db):
        print(f"\nSuccessfully cleaned RAG database. Removed {len(messages_to_remove)} contradictory messages.")
    else:
        print("\nFailed to save cleaned database.")

if __name__ == "__main__":
    # Check if --apply flag is provided
    apply_changes = "--apply" in sys.argv
    
    if apply_changes:
        confirmation = input("This will remove contradictory messages from the RAG database. Continue? (y/n): ")
        if confirmation.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    
    clean_rag_contradictions(dry_run=not apply_changes)
