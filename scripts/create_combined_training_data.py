#!/usr/bin/env python3
"""
Script to create a combined training dataset with both text messages and emails.
This script processes raw text message and email data to create a JSONL file
suitable for fine-tuning a model that can handle both communication channels.

Email data is optional - if the email_data.json file doesn't exist, the script
will proceed with only text message data.
"""

import json
import random
import os
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths to data files - using user-specific paths
def get_user_data_dir():
    """Get the user-specific data directory"""
    # Check if we're running in development or production
    if os.path.exists("../data"):
        return "../data"
    else:
        # In production, use the user's data directory
        home_dir = os.path.expanduser("~")
        return os.path.join(home_dir, "Library", "Application Support", "ai-clone-desktop", "data")

# Dynamic paths
DATA_DIR = get_user_data_dir()
EMAIL_DATA_PATH = os.path.join(DATA_DIR, "email_data.json")

# Find all imessage raw data files
def find_imessage_files():
    """Find all imessage raw data files in the data directory"""
    imessage_files = []
    if os.path.exists(DATA_DIR):
        for file in os.listdir(DATA_DIR):
            if file.startswith("imessage_raw_") and file.endswith(".json"):
                imessage_files.append(os.path.join(DATA_DIR, file))
    return imessage_files

IMESSAGE_PATHS = find_imessage_files()
OUTPUT_PATH = os.path.join(DATA_DIR, "combined_channel_model.jsonl")

def load_json_data(file_path):
    """Load JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        return None

def create_text_message_examples(imessage_data):
    """Create training examples from iMessage data."""
    examples = []
    
    for contact_data in imessage_data:
        contact = contact_data.get("contact", "Unknown")
        messages = contact_data.get("messages", [])
        
        # Group messages into conversations
        conversations = []
        current_convo = []
        
        for msg in messages:
            # Skip empty or media-only messages
            if not msg.get("text") or msg.get("text") == "￼":
                continue
                
            current_convo.append(msg)
            
            # Start a new conversation if we have enough messages
            if len(current_convo) >= 2:
                if random.random() < 0.3:  # 30% chance to end conversation and start new one
                    if len(current_convo) >= 2:
                        conversations.append(current_convo)
                        current_convo = []
        
        # Add the last conversation if it has at least 2 messages
        if len(current_convo) >= 2:
            conversations.append(current_convo)
        
        # Create training examples from conversations
        for convo in conversations:
            for i in range(1, len(convo)):
                if convo[i-1]["is_from_me"] == False and convo[i]["is_from_me"] == True:
                    # Found a user message responding to someone else
                    user_msg = convo[i-1]["text"]
                    response = convo[i]["text"]
                    
                    # Create training example
                    example = {
                        "messages": [
                            {
                                "role": "system", 
                                "content": "You are an AI clone that responds to messages as if you were the user. The following is a text message conversation. Respond in the user's texting style, which is typically casual with minimal capitalization and punctuation."
                            },
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": response}
                        ]
                    }
                    examples.append(example)
    
    return examples

def create_email_examples(email_data):
    """Create training examples from email data."""
    examples = []
    
    if not email_data:
        return examples
    
    for email in email_data:
        content = email.get("content", "").strip()
        metadata = email.get("metadata", {})
        context = email.get("context", {})
        
        # Skip empty emails or non-sent emails
        if not content or not metadata.get("is_sent", False):
            continue
        
        # Get the previous message if available
        previous_message = context.get("previous_message", "").strip()
        
        if previous_message:
            # Create training example
            example = {
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an AI clone that responds to messages as if you were the user. The following is an email conversation. Respond in the user's email style, which is typically more formal and structured than text messages."
                    },
                    {"role": "user", "content": previous_message},
                    {"role": "assistant", "content": content}
                ]
            }
            examples.append(example)
    
    return examples

def write_jsonl(examples, output_path):
    """Write examples to a JSONL file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')

def main():
    logger.info(f"Starting combined training data creation")
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Email data path: {EMAIL_DATA_PATH}")
    logger.info(f"Found {len(IMESSAGE_PATHS)} iMessage data files")
    
    # Load email data (optional)
    email_examples = []
    if os.path.exists(EMAIL_DATA_PATH):
        email_data = load_json_data(EMAIL_DATA_PATH)
        if email_data:
            email_examples = create_email_examples(email_data)
            logger.info(f"Created {len(email_examples)} email examples")
    else:
        logger.info(f"No email data found at {EMAIL_DATA_PATH}. Proceeding with only text message data.")
    
    # Load and process iMessage data
    text_examples = []
    for imessage_path in IMESSAGE_PATHS:
        if os.path.exists(imessage_path):
            imessage_data = load_json_data(imessage_path)
            if imessage_data:
                new_examples = create_text_message_examples(imessage_data)
                text_examples.extend(new_examples)
                logger.info(f"Created {len(new_examples)} text message examples from {imessage_path}")
    
    logger.info(f"Created {len(text_examples)} total text message examples")
    
    # Check if we have any examples
    if not email_examples and not text_examples:
        logger.error("No training examples could be created. Please extract email or iMessage data first.")
        return
    
    # Combine examples
    all_examples = email_examples + text_examples
    random.shuffle(all_examples)
    
    # Write to JSONL file
    write_jsonl(all_examples, OUTPUT_PATH)
    logger.info(f"Written {len(all_examples)} combined examples to {OUTPUT_PATH}")
    
    # Create train/val split
    train_ratio = 0.9
    train_size = int(len(all_examples) * train_ratio)
    
    train_examples = all_examples[:train_size]
    val_examples = all_examples[train_size:]
    
    train_path = OUTPUT_PATH.replace('.jsonl', '_train.jsonl')
    val_path = OUTPUT_PATH.replace('.jsonl', '_val.jsonl')
    
    write_jsonl(train_examples, train_path)
    write_jsonl(val_examples, val_path)
    
    logger.info(f"Split into {len(train_examples)} training examples and {len(val_examples)} validation examples")

if __name__ == "__main__":
    main()
