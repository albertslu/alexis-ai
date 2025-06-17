#!/usr/bin/env python3

"""
RAG Database Cleanup Script (Dry Run)

This script analyzes the current RAG database and identifies messages that should be removed
based on various criteria. It performs a dry run, showing what would be removed without
actually modifying the database.

Criteria for removal:
1. Test messages (hello, hi, test, etc.)
2. Very short messages (less than 10 characters)
3. Messages from chat_history.json that contradict memory facts
4. Generic responses that don't provide value
"""

import os
import json
import sys
import re
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

def analyze_rag_database():
    """Analyze the RAG database and identify messages to remove."""
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
    messages_to_keep = []
    
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
            messages_to_keep.append((i, msg))
    
    # Print statistics
    print(f"RAG Database Analysis (DRY RUN)")
    print(f"================================")
    print(f"Total messages: {total_messages}")
    print(f"Messages to keep: {len(messages_to_keep)}")
    print(f"Messages to remove: {len(messages_to_remove)}")
    print()
    
    # Print sample of messages to remove
    print(f"Sample of messages that would be removed:")
    for i, (idx, msg, reason) in enumerate(messages_to_remove[:20]):
        text = msg.get('text', '')
        if len(text) > 50:
            text = text[:47] + "..."
        print(f"{i+1}. [{reason}] '{text}'")
    
    if len(messages_to_remove) > 20:
        print(f"... and {len(messages_to_remove) - 20} more")
    
    print()
    print("This is a dry run. No changes have been made to the database.")
    print("To actually clean the database, run the clean_rag_database.py script.")

if __name__ == "__main__":
    analyze_rag_database()
