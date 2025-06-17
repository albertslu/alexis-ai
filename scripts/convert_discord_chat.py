"""
Convert Discord chat logs to training format.

This script takes a text file with Discord conversations and converts them to
the JSON format needed for fine-tuning. It's designed to work with actual
Discord conversation formats.

Usage:
    python convert_discord_chat.py input_file.txt [output_prefix] [--days=1]
"""

import json
import sys
import re
import os
from datetime import datetime, timedelta
import pandas as pd
import argparse
from sklearn.model_selection import train_test_split

def parse_conversation(file_path, your_names=None):
    """Parse a conversation file into message objects."""
    if your_names is None:
        your_names = ['You', 'you', 'Me', 'me', 'I', 'i', 'Myself', 'myself']
    
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
            elif current_context:
                current_context[-1]['content'] += "\n" + line
            continue
        
        sender, content = match.groups()
        is_you = sender.lower() in [name.lower() for name in your_names]
        
        message = {
            'message_id': f"manual_{len(messages) + len(current_context)}",
            'channel_id': 'manual',
            'channel_name': 'Manual Collection',
            'guild_id': None,
            'guild_name': 'Manual',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'author': {
                'id': '1' if is_you else f"2_{sender}",
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
                'author_id': f"2_{sender}",
                'author_name': sender,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            current_context.append(context_msg)
    
    return messages

def convert_to_training_format(messages, system_prompt=None):
    """Convert messages to OpenAI fine-tuning format."""
    if system_prompt is None:
        system_prompt = "You are Clone, an AI trained to respond exactly like the user would. Match their casual, concise communication style with minimal exclamation marks. Your responses should sound exactly like them."
    
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
                    "content": system_prompt
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

def split_data(data, train_size=0.7, val_size=0.15, test_size=0.15):
    """Split data into training, validation, and test sets."""
    # Handle small datasets
    if len(data) <= 3:
        # If we have 3 or fewer examples, just put them all in training
        return data, [], []
    elif len(data) <= 5:
        # If we have 4-5 examples, use 3 for training, 1 for validation, 1 for testing
        train_size = 3
        val_size = 1
        test_size = len(data) - train_size - val_size
        train_data = data[:train_size]
        val_data = data[train_size:train_size+val_size]
        test_data = data[train_size+val_size:]
        return train_data, val_data, test_data
    
    # For larger datasets, use sklearn's train_test_split
    # First split into training and temp (validation + testing)
    train_data, temp_data = train_test_split(data, train_size=train_size, random_state=42)
    
    # Then split temp into validation and testing
    # Calculate the relative sizes for the second split
    relative_val_size = val_size / (val_size + test_size)
    val_data, test_data = train_test_split(temp_data, train_size=relative_val_size, random_state=42)
    
    return train_data, val_data, test_data

def main():
    parser = argparse.ArgumentParser(description="Convert Discord chat logs to training format")
    parser.add_argument("input_file", help="Path to the text file with Discord conversations")
    parser.add_argument("output_prefix", nargs="?", default=None, help="Prefix for output files")
    parser.add_argument("--your-name", action="append", help="Your name in the chat (can specify multiple)")
    parser.add_argument("--system-prompt", help="Custom system prompt for the model")
    parser.add_argument("--train-size", type=float, default=0.7, help="Proportion for training set")
    parser.add_argument("--val-size", type=float, default=0.15, help="Proportion for validation set")
    parser.add_argument("--test-size", type=float, default=0.15, help="Proportion for test set")
    
    args = parser.parse_args()
    
    # Set default output prefix if not provided
    if args.output_prefix is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output_prefix = f"models/shaco_{timestamp}"
    
    # Set default names if not provided
    your_names = args.your_name if args.your_name else ['You']
    
    print(f"Converting messages from {args.input_file}...")
    print(f"Your name(s) in the chat: {', '.join(your_names)}")
    
    messages = parse_conversation(args.input_file, your_names)
    print(f"Found {len(messages)} messages, {len([m for m in messages if m['author']['username'] == 'You'])} from you")
    
    training_data = convert_to_training_format(messages, args.system_prompt)
    print(f"Created {len(training_data)} training examples")
    
    # Split the data
    train_data, val_data, test_data = split_data(
        training_data, 
        train_size=args.train_size, 
        val_size=args.val_size, 
        test_size=args.test_size
    )
    
    print(f"Split into {len(train_data)} training, {len(val_data)} validation, and {len(test_data)} test examples")
    
    # Save the data
    os.makedirs(os.path.dirname(args.output_prefix), exist_ok=True)
    
    # Save as JSONL (one JSON object per line)
    train_file = f"{args.output_prefix}_train.jsonl"
    val_file = f"{args.output_prefix}_val.jsonl"
    test_file = f"{args.output_prefix}_test.jsonl"
    
    with open(train_file, 'w', encoding='utf-8') as f:
        for example in train_data:
            f.write(json.dumps(example) + '\n')
    
    with open(val_file, 'w', encoding='utf-8') as f:
        for example in val_data:
            f.write(json.dumps(example) + '\n')
    
    with open(test_file, 'w', encoding='utf-8') as f:
        for example in test_data:
            f.write(json.dumps(example) + '\n')
    
    print(f"Training data saved to {train_file}")
    print(f"Validation data saved to {val_file}")
    print(f"Test data saved to {test_file}")
    
    # Also save raw messages as JSON
    raw_file = f"{args.output_prefix}_raw.json"
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    
    print(f"Raw message data saved to {raw_file}")

if __name__ == "__main__":
    main()
