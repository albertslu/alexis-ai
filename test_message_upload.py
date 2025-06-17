#!/usr/bin/env python3

"""
Simple test script for message uploads

This script demonstrates how to upload and process messages without using the full RAG system.
"""

import os
import json
from datetime import datetime
from pathlib import Path

# Sample conversation data for testing
SAMPLE_CONVERSATION = """
Friend: Hey, how's your day going?
Me: Pretty good! Just finished working on that AI project I told you about.
Friend: Oh cool, the one with the language model?
Me: Yeah, I'm trying to make it respond more like me. It's coming along well.
Friend: That sounds impressive. How accurate is it?
Me: I'd say it's about 75% there. Still needs some fine-tuning.
Friend: What's the hardest part about it?
Me: Getting it to understand context and maintain my conversational style consistently.
Friend: Makes sense. Are you using any specific techniques?
Me: Yeah, I'm implementing a hybrid approach with RAG and fine-tuning.
"""

# Sample messages for testing
SAMPLE_MESSAGES = """
I prefer coding in Python for most projects, but JavaScript has its place too.
I'm thinking about going hiking this weekend if the weather is good.
Remind me to pick up some groceries on the way home.
I've been working on this AI project for about three months now.
My favorite food is definitely Thai curry, especially with extra spice.
"""

def process_conversation(conversation_text):
    """Process conversation format text into structured messages."""
    # Pattern to match "Name: Message" format
    lines = conversation_text.strip().split('\n')
    messages = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # Split by first colon
        parts = line.split(':', 1)
        if len(parts) != 2:
            continue
            
        sender = parts[0].strip()
        text = parts[1].strip()
        
        # Check if this is a user message (from "Me")
        is_user = sender.lower() in ['me', 'i', 'self', 'user']
        
        if is_user:
            messages.append({
                "text": text,
                "sender": "user",
                "timestamp": datetime.now().isoformat()
            })
    
    return messages

def process_messages(messages_text):
    """Process individual messages format."""
    lines = messages_text.strip().split('\n')
    messages = []
    
    for line in lines:
        text = line.strip()
        if not text:
            continue
            
        messages.append({
            "text": text,
            "sender": "user",
            "timestamp": datetime.now().isoformat()
        })
    
    return messages

def save_messages(messages, output_file):
    """Save messages to a JSON file."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Load existing data if file exists
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {"messages": []}
    else:
        data = {"messages": []}
    
    # Add new messages
    data["messages"].extend(messages)
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return len(messages)

def main():
    print("\n===== Testing Message Upload Functionality =====\n")
    
    # Set up output directory
    data_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "data"
    os.makedirs(data_dir, exist_ok=True)
    output_file = data_dir / "uploaded_messages.json"
    
    # Process conversation data
    print("Processing conversation data...")
    conversation_messages = process_conversation(SAMPLE_CONVERSATION)
    print(f"Extracted {len(conversation_messages)} user messages from conversation")
    
    # Save conversation messages
    saved_count = save_messages(conversation_messages, output_file)
    print(f"Saved {saved_count} conversation messages to {output_file}")
    
    # Process message data
    print("\nProcessing individual messages...")
    individual_messages = process_messages(SAMPLE_MESSAGES)
    print(f"Extracted {len(individual_messages)} individual messages")
    
    # Save individual messages
    saved_count = save_messages(individual_messages, output_file)
    print(f"Saved {saved_count} individual messages to {output_file}")
    
    # Print total messages
    with open(output_file, 'r') as f:
        data = json.load(f)
        total_messages = len(data["messages"])
    
    print(f"\nTotal messages saved: {total_messages}")
    print(f"Messages saved to: {output_file}")
    
    # Print sample of saved messages
    print("\nSample of saved messages:")
    for i, msg in enumerate(data["messages"][:3]):
        print(f"  {i+1}. {msg['text']}")
    
    print("\nMessage upload test completed successfully!")

if __name__ == "__main__":
    main()
