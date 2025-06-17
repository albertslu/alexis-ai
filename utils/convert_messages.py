"""
Convert manually collected Discord messages to training format.

This script takes a text file with manually copied Discord conversations
and converts them to the JSON format needed for fine-tuning.

Example input format:
Friend: Hey, how's it going?
You: not much, just working on this ai project
Friend: That sounds cool! What does it do?
You: it's a discord bot that learns to talk like me

Usage:
    python convert_messages.py input_file.txt [output_file.json]
"""

import json
import sys
import re
import os
from datetime import datetime
import pandas as pd

def parse_conversation(file_path):
    """Parse a conversation file into message objects."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    messages = []
    current_context = []
    user_pattern = re.compile(r'^(.*?):\s+(.*?)$')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        match = user_pattern.match(line)
        if not match:
            # If no match, append to the previous message
            if messages:
                messages[-1]['content'] += "\n" + line
            continue
        
        sender, content = match.groups()
        is_you = sender.lower() in ['you', 'me', 'myself', 'i']
        
        message = {
            'message_id': f"manual_{len(messages)}",
            'channel_id': 'manual',
            'channel_name': 'Manual Collection',
            'guild_id': None,
            'guild_name': 'Manual',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'author': {
                'id': '1' if is_you else '2',
                'username': 'You' if is_you else sender,
                'discriminator': '0000'
            },
            'has_attachments': False,
            'mentions_users': [],
            'mentions_roles': [],
            'reference': None
        }
        
        # If this is your message, add the previous messages as context
        if is_you:
            # Add up to 5 previous messages as context
            message['context'] = current_context[-5:].copy()
            current_context = []
            messages.append(message)
        else:
            # Add to context for the next "You" message
            context_msg = {
                'author_id': '2',
                'author_name': sender,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            current_context.append(context_msg)
    
    return messages

def convert_to_training_format(messages):
    """Convert messages to OpenAI fine-tuning format."""
    training_data = []
    
    for msg in messages:
        # Skip messages that aren't from you
        if msg['author']['username'] != 'You':
            continue
        
        # Create context from previous messages
        context = ""
        for ctx in msg.get('context', []):
            context += f"{ctx['author_name']}: {ctx['content']}\n"
        
        # Create the training example
        example = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are Clone, an AI trained to respond exactly like the user would. Match their casual, concise communication style with minimal exclamation marks. Your responses should sound exactly like them."
                },
                {
                    "role": "user",
                    "content": context.strip()
                },
                {
                    "role": "assistant",
                    "content": msg['content']
                }
            ]
        }
        
        training_data.append(example)
    
    return training_data

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} input_file.txt [output_file.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    print(f"Converting messages from {input_file}...")
    messages = parse_conversation(input_file)
    print(f"Found {len(messages)} messages, {len([m for m in messages if m['author']['username'] == 'You'])} from you")
    
    training_data = convert_to_training_format(messages)
    print(f"Created {len(training_data)} training examples")
    
    # Save as JSONL (one JSON object per line)
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in training_data:
            f.write(json.dumps(example) + '\n')
    
    print(f"Training data saved to {output_file}")
    
    # Also save raw messages as JSON
    raw_file = output_file.replace('.json', '_raw.json')
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    
    print(f"Raw message data saved to {raw_file}")
    
    # Create a sample conversation file if none exists
    if not os.path.exists(input_file):
        sample_file = "sample_conversation.txt"
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write("Friend: Hey, how's it going?\n")
            f.write("You: not much, just working on this ai project\n")
            f.write("Friend: That sounds cool! What does it do?\n")
            f.write("You: it's a discord bot that learns to talk like me\n")
            f.write("Friend: How does it work?\n")
            f.write("You: it uses my discord messages to learn my style\n")
        print(f"\nCreated sample conversation file: {sample_file}")
        print("Edit this file with your actual conversations and run the script again.")

if __name__ == "__main__":
    main()
