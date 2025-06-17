"""
Prepare Training Data for GPT-4 Fine-tuning

This script processes the collected Discord messages and prepares them
in the format required for OpenAI's fine-tuning.
"""

import os
import json
import pandas as pd
import numpy as np
from tqdm import tqdm
import argparse
from sklearn.model_selection import train_test_split

def prepare_fine_tuning_data(input_file, output_prefix, min_tokens=20, max_tokens=1024, train_size=0.8, val_size=0.1, test_size=0.1):
    # Load training data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Extract LinkedIn data if available
    linkedin_integrated = data.get('linkedin_integrated', False)
    linkedin_context = data.get('linkedin_context', '')
    
    # Extract key information from LinkedIn context if available
    background_info = "Computer Engineering at UT Austin, founder of an AI startup, and experience as a freelance photographer"
    if linkedin_integrated and linkedin_context:
        # This is a simple extraction, could be made more sophisticated
        background_info = ""
        if "UT Austin" in linkedin_context or "University of Texas" in linkedin_context:
            background_info += "Computer Engineering at UT Austin, "
        if "Founder" in linkedin_context or "founder" in linkedin_context:
            background_info += "founder of an AI startup, "
        if "Photographer" in linkedin_context or "photographer" in linkedin_context:
            background_info += "experience as a freelance photographer"
        
        # Fallback if extraction fails
        if not background_info.strip():
            background_info = "Computer Engineering at UT Austin, founder of an AI startup, and experience as a freelance photographer"

    """
    Prepare Discord message data for GPT fine-tuning.
    
    Args:
        input_file: Path to the JSON file with collected Discord messages
        output_file: Path to save the prepared JSONL file for fine-tuning
        min_tokens: Minimum number of tokens for a message to be included
        max_tokens: Maximum number of tokens for a message to be included
    """
    # Load the collected message data
    with open(input_file, 'r', encoding='utf-8') as f:
        messages = json.load(f)
    
    print(f"Loaded {len(messages)} messages from {input_file}")
    
    # Filter messages
    filtered_messages = []
    for msg in tqdm(messages, desc="Filtering messages"):
        # Skip empty messages or those with just a few characters
        if not msg['content'] or len(msg['content']) < min_tokens:
            continue
            
        # Skip messages that are too long
        if len(msg['content']) > max_tokens:
            continue
            
        # Skip messages with attachments (images, files, etc.)
        if msg['has_attachments']:
            continue
            
        # Add the message to our filtered list
        filtered_messages.append(msg)
    
    print(f"Filtered down to {len(filtered_messages)} messages")
    
    # Prepare the data in the format required for fine-tuning
    fine_tuning_data = []
    
    # Track messages with friend references for potential filtering or special handling
    messages_with_friend_references = 0
    total_messages = 0
    
    for msg in tqdm(filtered_messages, desc="Preparing fine-tuning data"):
        total_messages += 1
        
        # Check if this is an identity-related message (talking about oneself)
        is_identity_context = msg.get('is_identity_context', False)
        has_second_person_reference = msg.get('has_second_person_reference', False)
        
        # Track messages with identity context for reporting
        if is_identity_context:
            messages_with_friend_references += 1  # Keeping variable name for compatibility
            
            # For identity-related messages with second-person references, we need to be careful
            # These could be messages where you're talking about yourself but also addressing someone else
            # which might confuse the model about your identity vs. others
            if has_second_person_reference and any(identity_term in msg['content'].lower() for identity_term in ['i am', 'i\'m', 'my name', 'about me', 'about myself']):
                # We'll keep these messages but make sure they have proper context
                # The RAG system will help provide accurate identity information when needed
                pass
        
        # Get context (previous messages)
        context = ""
        if msg['context']:
            # Group consecutive messages from the same author
            grouped_context = []
            current_author = None
            current_messages = []
            
            for ctx_msg in msg['context']:
                author = ctx_msg['author_name']
                content = ctx_msg['content']
                
                # If this is a new author or the first message
                if author != current_author:
                    # Add the previous author's grouped messages if they exist
                    if current_messages:
                        grouped_content = " ".join(current_messages)
                        grouped_context.append((current_author, grouped_content))
                    
                    # Start a new group
                    current_author = author
                    current_messages = [content]
                else:
                    # Add to the current group
                    current_messages.append(content)
            
            # Add the last group if it exists
            if current_messages:
                grouped_content = " ".join(current_messages)
                grouped_context.append((current_author, grouped_content))
            
            # Format the grouped context
            for author, content in grouped_context:
                context += f"{author}: {content}\n"
        
        # Format for GPT fine-tuning
        # Using the chat format: {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        fine_tuning_example = {
            "messages": [
                {
                    "role": "system",
                    "content": f"Respond exactly as the user would. Use casual style with minimal punctuation and lowercase. Include accurate information about the user's background: {background_info}. Keep responses contextually relevant to the conversation. When people send multiple messages in a row, you should respond to the entire context, not just the last message. When asked about yourself, focus on your actual identity and background information, not on nicknames or references to other people that appear in your messages."
                },
                {
                    "role": "user",
                    "content": context.strip() if context.strip() else "Start a conversation."
                },
                {
                    "role": "assistant",
                    "content": msg['content']
                }
            ]
        }
        
        fine_tuning_data.append(fine_tuning_example)
    
    # Split the data into training, validation, and testing sets
    # First split into training and temp (validation + testing)
    train_data, temp_data = train_test_split(fine_tuning_data, train_size=train_size, random_state=42)
    
    # Then split temp into validation and testing
    # Calculate the relative sizes for the second split
    relative_val_size = val_size / (val_size + test_size)
    val_data, test_data = train_test_split(temp_data, train_size=relative_val_size, random_state=42)
    
    # Save the prepared data
    train_file = f"{output_prefix}_train.jsonl"
    val_file = f"{output_prefix}_val.jsonl"
    test_file = f"{output_prefix}_test.jsonl"
    
    # Save training data
    with open(train_file, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item) + '\n')
    
    # Save validation data
    with open(val_file, 'w', encoding='utf-8') as f:
        for item in val_data:
            f.write(json.dumps(item) + '\n')
    
    # Save testing data
    with open(test_file, 'w', encoding='utf-8') as f:
        for item in test_data:
            f.write(json.dumps(item) + '\n')
    
    print(f"Saved {len(train_data)} examples to {train_file} (training set)")
    print(f"Saved {len(val_data)} examples to {val_file} (validation set)")
    print(f"Saved {len(test_data)} examples to {test_file} (testing set)")
    print(f"Processed {total_messages} total messages, {messages_with_friend_references} contained identity context")
    print("The data is now ready for fine-tuning with OpenAI's API.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Discord message data for GPT fine-tuning")
    parser.add_argument("input_file", help="Path to the JSON file with collected Discord messages")
    parser.add_argument("output_prefix", help="Prefix for output files (will create prefix_train.jsonl, prefix_val.jsonl, prefix_test.jsonl)")
    parser.add_argument("--min-tokens", type=int, default=20, help="Minimum number of tokens for a message to be included")
    parser.add_argument("--max-tokens", type=int, default=1024, help="Maximum number of tokens for a message to be included")
    parser.add_argument("--train-size", type=float, default=0.8, help="Proportion of data to use for training (default: 0.8)")
    parser.add_argument("--val-size", type=float, default=0.1, help="Proportion of data to use for validation (default: 0.1)")
    parser.add_argument("--test-size", type=float, default=0.1, help="Proportion of data to use for testing (default: 0.1)")
    
    args = parser.parse_args()
    
    # Verify that proportions sum to 1
    total = args.train_size + args.val_size + args.test_size
    if abs(total - 1.0) > 0.001:
        print(f"Warning: Train, validation, and test proportions sum to {total}, not 1.0")
        print("Normalizing proportions...")
        args.train_size /= total
        args.val_size /= total
        args.test_size /= total
        print(f"Adjusted proportions: train={args.train_size:.2f}, val={args.val_size:.2f}, test={args.test_size:.2f}")
    
    prepare_fine_tuning_data(
        args.input_file, 
        args.output_prefix, 
        args.min_tokens, 
        args.max_tokens,
        args.train_size,
        args.val_size,
        args.test_size
    )
