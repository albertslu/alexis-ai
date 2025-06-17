#!/usr/bin/env python3

"""
Script to clean the RAG database by removing examples where the AI response is too similar to the user message.
This will help improve email response quality by removing bad examples from the database.
"""

import json
import os
import sys

# Add the parent directory to the path so we can import from app_integration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.app_integration import is_response_too_similar, initialize_rag

def clean_rag_database():
    """Clean the RAG database by removing bad examples"""
    print("Initializing RAG system...")
    rag_system = initialize_rag()
    
    # The messages are stored directly in the rag_system.messages list
    all_messages = rag_system.messages
    print(f"Found {len(all_messages)} total messages in the database")
    
    # Count messages by channel
    email_count = sum(1 for msg in all_messages if msg.get('channel') == 'email')
    text_count = sum(1 for msg in all_messages if msg.get('channel') != 'email')
    print(f"Channel breakdown: {email_count} email messages, {text_count} text messages")
    
    # Find bad examples (where AI response is too similar to user message)
    bad_examples = []
    for i, msg in enumerate(all_messages):
        if msg.get('sender') == 'clone':  # Only check AI responses
            # Find the previous message (user message)
            user_msg = msg.get('previous_message', '')
            if not user_msg and i > 0:
                # Try to get from context field
                user_msg = msg.get('context', '')
                
            ai_resp = msg.get('text', '')
            
            if user_msg and ai_resp and is_response_too_similar(user_msg, ai_resp):
                # Add index to the message for removal
                msg['index'] = i
                bad_examples.append(msg)
    
    print(f"Found {len(bad_examples)} bad examples where AI response is too similar to user message")
    
    # Show some examples of bad responses
    if bad_examples:
        print("\nExamples of bad responses:")
        for i, example in enumerate(bad_examples[:3]):
            print(f"\nExample {i+1}:")
            print(f"User: {example.get('previous_message', '') or example.get('context', '')[:100]}...")
            print(f"AI: {example.get('text', '')[:100]}...")
    
    # Auto-remove bad examples (since this is a script run from command line)
    if bad_examples:
        # Create a backup first
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'rag')
        db_file = os.path.join(db_path, f'{rag_system.user_id}_message_db.json')
        backup_file = os.path.join(db_path, f'{rag_system.user_id}_message_db_backup.json')
        
        print(f"Creating backup at {backup_file}")
        with open(db_file, 'r') as f:
            db_data = json.load(f)
            with open(backup_file, 'w') as backup_f:
                json.dump(db_data, backup_f, indent=2)
        
        # Sort indices in reverse order to avoid shifting issues when removing
        indices_to_remove = sorted([msg['index'] for msg in bad_examples], reverse=True)
        print(f"Removing {len(indices_to_remove)} bad examples from the database")
        
        # Remove messages by index (in reverse order to avoid index shifting)
        for index in indices_to_remove:
            if 0 <= index < len(rag_system.messages):
                del rag_system.messages[index]
        
        # Save the updated database
        rag_system.save_database()
        print("Database cleaned successfully!")
    else:
        print("No bad examples found. Database is clean!")

if __name__ == "__main__":
    clean_rag_database()
