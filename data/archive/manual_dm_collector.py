"""
Manual Discord Message Collector

This script helps you manually create a dataset from your Discord messages.
Just paste your messages and the context they were responding to.
"""

import json
import os
from datetime import datetime
import uuid

def collect_manual_messages():
    """Collect messages manually from user input"""
    messages = []
    message_id = 1
    
    print("=== Manual Discord Message Collector ===")
    print("Enter your messages and the messages you were responding to.")
    print("This will help create a dataset for fine-tuning your AI clone.")
    print("Type 'done' when finished.")
    print()
    
    while True:
        print(f"--- Message #{message_id} ---")
        
        # Get the other person's message (context)
        other_message = input("Other person's message (or 'skip' if none, 'done' to finish): ")
        if other_message.lower() == 'done':
            break
            
        # Skip this message pair if no context
        if other_message.lower() == 'skip':
            continue
            
        # Get your response
        your_message = input("Your response: ")
        if your_message.lower() == 'done':
            break
            
        # Get the other person's name
        other_name = input("Other person's name (default: Friend): ") or "Friend"
        
        # Create context message
        context = [{
            'author_id': str(uuid.uuid4()),
            'author_name': other_name,
            'content': other_message,
            'timestamp': datetime.now().isoformat()
        }]
        
        # Create your message
        message = {
            'message_id': message_id,
            'channel_id': str(uuid.uuid4()),
            'channel_name': 'direct_messages',
            'guild_id': None,
            'guild_name': 'DMs',
            'content': your_message,
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'has_attachments': False,
            'mentions_users': [],
            'mentions_roles': [],
            'reference': None
        }
        
        # Add to messages list
        messages.append(message)
        message_id += 1
        print("Message pair added!")
        print()
    
    # Save the collected messages
    if messages:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'manual_messages_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            
        print(f"\nCollected {len(messages)} message pairs")
        print(f"Data saved to {filename}")
        return filename
    else:
        print("\nNo messages collected")
        return None

if __name__ == "__main__":
    collect_manual_messages()
