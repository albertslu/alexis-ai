#!/usr/bin/env python
"""
Convert training_data.json to OpenAI fine-tuning format.

This script takes the training_data.json file from the AI Clone app and converts it
to the JSONL format required for OpenAI fine-tuning.
"""

import json
import os
import argparse
from datetime import datetime

def convert_to_finetuning_format(training_data_path, system_prompt=None):
    """Convert training_data.json to OpenAI fine-tuning format."""
    # Default system prompt if none provided
    if system_prompt is None:
        system_prompt = "You are an AI trained to respond exactly like the user would. Match their communication style perfectly."
    
    # Load the training data
    with open(training_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    training_examples = []
    
    # Process each conversation
    for conversation in data.get('conversations', []):
        messages = conversation.get('messages', [])
        
        # Group messages into user-bot pairs
        i = 0
        while i < len(messages) - 1:
            # Find a user message
            if messages[i]['sender'] == 'user':
                user_msg = messages[i]
                
                # Look for the next bot response
                if i + 1 < len(messages) and messages[i + 1]['sender'] == 'bot':
                    bot_msg = messages[i + 1]
                    
                    # Create a training example
                    example = {
                        "messages": [
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": user_msg['text']
                            },
                            {
                                "role": "assistant",
                                "content": bot_msg['text']
                            }
                        ]
                    }
                    
                    training_examples.append(example)
            
            i += 1
    
    print(f"Created {len(training_examples)} training examples")
    return training_examples

def split_data(data, train_size=0.8, val_size=0.2):
    """Split data into training and validation sets."""
    # Calculate split indices
    n = len(data)
    train_end = int(n * train_size)
    
    # Split the data
    train_data = data[:train_end]
    val_data = data[train_end:]
    
    return train_data, val_data

def main():
    parser = argparse.ArgumentParser(description="Convert training_data.json to OpenAI fine-tuning format")
    parser.add_argument("--input", default="../data/training_data.json", help="Path to training_data.json")
    parser.add_argument("--output-prefix", default=None, help="Prefix for output files")
    parser.add_argument("--system-prompt", help="Custom system prompt for the model")
    parser.add_argument("--train-size", type=float, default=0.8, help="Proportion for training set")
    parser.add_argument("--val-size", type=float, default=0.2, help="Proportion for validation set")
    
    args = parser.parse_args()
    
    # Set default output prefix if not provided
    if args.output_prefix is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output_prefix = f"models/clone_{timestamp}"
    
    print(f"Converting messages from {args.input}...")
    
    training_examples = convert_to_finetuning_format(args.input, args.system_prompt)
    
    # Split the data
    train_data, val_data = split_data(
        training_examples, 
        train_size=args.train_size, 
        val_size=args.val_size
    )
    
    print(f"Split into {len(train_data)} training and {len(val_data)} validation examples")
    
    # Save the data
    os.makedirs(os.path.dirname(args.output_prefix), exist_ok=True)
    
    # Save as JSONL (one JSON object per line)
    train_file = f"{args.output_prefix}_train.jsonl"
    val_file = f"{args.output_prefix}_val.jsonl"
    
    with open(train_file, 'w', encoding='utf-8') as f:
        for example in train_data:
            f.write(json.dumps(example) + '\n')
    
    with open(val_file, 'w', encoding='utf-8') as f:
        for example in val_data:
            f.write(json.dumps(example) + '\n')
    
    print(f"Training data saved to {train_file}")
    print(f"Validation data saved to {val_file}")
    
    print("\nNext steps:")
    print(f"1. Run fine-tuning: python scripts/finetune_ai_clone.py {train_file} --validation-file {val_file} --suffix clone")

if __name__ == "__main__":
    main()
