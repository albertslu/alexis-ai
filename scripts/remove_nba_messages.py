#!/usr/bin/env python3

"""
Script to remove specific NBA-related messages from the RAG database.
This script will create a backup of the original file before making changes.
"""

import json
import os
import shutil
from datetime import datetime

# Path to the RAG database
RAG_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                           'data', 'rag', 'default_message_db.json')

# Create a backup first
def backup_file(file_path):
    """Create a backup of the file with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at: {backup_path}")
    return backup_path

# Messages to remove (partial text to identify them)
NBA_MESSAGES_TO_REMOVE = [
    "bert who's the nba goat?",
    "lebron or jordan",
    "who u got winning the nba title this year?",
    "why do u say that?",
    "what about okc",
    "what do u think about the luka trade?",
    "nba goat",
    "lebron",
    "jordan",
    "nba title",
    "luka trade",
    "okc"
]

# Additional keywords to identify clone responses
NBA_KEYWORDS = [
    "nba",
    "goat",
    "lebron",
    "jordan",
    "basketball",
    "lakers",
    "celtics",
    "warriors",
    "bulls",
    "heat",
    "nuggets",
    "mavericks",
    "mavs",
    "pelicans",
    "luka",
    "championship",
    "finals"
]

def remove_messages(file_path, messages_to_remove, keywords, dry_run=False):
    """Remove specific messages from the RAG database"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Count original messages
        original_count = len(data.get('messages', []))
        
        # Filter out the messages to remove
        filtered_messages = []
        removed_messages = []
        
        # Get today's date for filtering recent messages
        today = datetime.now().strftime("%Y-%m-%d")
        
        for msg in data.get('messages', []):
            should_remove = False
            msg_text = msg.get('text', '').lower()
            msg_context = msg.get('context', '').lower()
            msg_timestamp = msg.get('timestamp', '')
            
            # Only consider messages from today
            if today in msg_timestamp:
                # Check if it matches any of the specific messages to remove
                for remove_text in messages_to_remove:
                    if remove_text.lower() in msg_text:
                        should_remove = True
                        removed_messages.append(f"[MATCHED TEXT] {msg.get('text', '')}")
                        break
                
                # If not already marked for removal, check for NBA keywords
                if not should_remove:
                    for keyword in keywords:
                        if keyword.lower() in msg_text or keyword.lower() in msg_context:
                            should_remove = True
                            removed_messages.append(f"[MATCHED KEYWORD '{keyword}'] {msg.get('text', '')}")
                            break
            
            if not should_remove:
                filtered_messages.append(msg)
        
        # Update the data with filtered messages (only if not in dry run mode)
        if not dry_run:
            data['messages'] = filtered_messages
            
            # Write back to the file
            with open(file_path, 'w') as f:
                json.dump(data, f)
        
        # Print summary
        print(f"Original message count: {original_count}")
        print(f"New message count: {len(filtered_messages)}")
        print(f"{'Would remove' if dry_run else 'Removed'} {original_count - len(filtered_messages)} messages:")
        for msg in removed_messages:
            print(f"  - {msg[:100]}...")
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    # Set dry run mode
    DRY_RUN = False
    
    print(f"Running in {'DRY RUN' if DRY_RUN else 'LIVE'} mode")
    
    # Create backup (only if not in dry run mode)
    if not DRY_RUN:
        backup_path = backup_file(RAG_DB_PATH)
    else:
        backup_path = "[DRY RUN] No backup created"
    
    # Remove messages
    success = remove_messages(RAG_DB_PATH, NBA_MESSAGES_TO_REMOVE, NBA_KEYWORDS, dry_run=DRY_RUN)
    
    if success:
        if DRY_RUN:
            print("\nThis was a dry run. No changes were made to the RAG database.")
            print("To actually remove the messages, change DRY_RUN = False at the top of the script.")
        else:
            print("Successfully removed NBA-related messages from the RAG database.")
            print(f"If you need to restore the original file, use the backup at: {backup_path}")
    else:
        print("Failed to remove messages. Please check the error above.")
        if not DRY_RUN:
            print(f"You can restore from the backup at: {backup_path}")
