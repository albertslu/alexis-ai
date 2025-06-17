#!/usr/bin/env python3

"""
iMessage Training Data Extractor

This script extracts your iMessage conversations and formats them into training data
for fine-tuning your AI clone. It preserves conversation context to help the model
learn how to respond contextually.
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import argparse
import sys
from pathlib import Path

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# Default paths
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')

# Updated system prompt focused on iMessage draft suggestions
SYSTEM_PROMPT = """You are an AI assistant that generates draft message suggestions for iMessage conversations.

Generate natural-sounding message drafts that:
• Match the user's typical writing style (tone, length, punctuation, emoji usage)
• Fit the conversation context and respond naturally to important points
• Are concise and ready to send without editing
• Provide helpful, contextually appropriate responses
• Sound authentic as if the user wrote them

Your suggestions will be presented as drafts for the user to choose from."""


def extract_from_chat_history(days=7, min_conversations=50):
    """
    Extract training data from chat_history.json
    
    Args:
        days: Number of days of history to extract
        min_conversations: Minimum number of conversations to extract
        
    Returns:
        list: Training examples in the format required for fine-tuning
    """
    print(f"Extracting training data from {CHAT_HISTORY_PATH}...")
    
    # Load chat history
    try:
        with open(CHAT_HISTORY_PATH, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Chat history file not found at {CHAT_HISTORY_PATH}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in chat history file")
        return []
        
    # Calculate cutoff date
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Extract conversations
    training_examples = []
    conversation_count = 0
    
    # Process each conversation in the chat history
    for conversation in chat_data.get('conversations', []):
        messages = conversation.get('messages', [])
        
        # Skip if no messages
        if not messages:
            continue
            
        # Check if conversation is recent enough
        latest_message = messages[-1]
        if 'timestamp' in latest_message and latest_message['timestamp'] < cutoff_date:
            continue
            
        # Process conversation into training examples
        for i in range(len(messages) - 1):
            current_msg = messages[i]
            next_msg = messages[i + 1]
            
            # We only want examples where user message is followed by clone message
            if current_msg.get('sender') == 'user' and next_msg.get('sender') == 'clone':
                # Create a training example
                example = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": current_msg.get('text', '')},
                        {"role": "assistant", "content": next_msg.get('text', '')}
                    ]
                }
                
                # Add to training examples if both messages have content
                if current_msg.get('text') and next_msg.get('text'):
                    training_examples.append(example)
        
        conversation_count += 1
        
        # Stop if we have enough conversations
        if conversation_count >= min_conversations:
            break
    
    print(f"Extracted {len(training_examples)} training examples from {conversation_count} conversations")
    return training_examples


def extract_from_imessage_db(days=7):
    """
    Extract training data from macOS iMessage database
    Note: This requires special permissions to access the Messages database
    
    Args:
        days: Number of days of history to extract
        
    Returns:
        list: Training examples in the format required for fine-tuning
    """
    print("Attempting to extract data from iMessage database...")
    
    # Path to iMessage database
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    
    if not os.path.exists(db_path):
        print(f"Error: iMessage database not found at {db_path}")
        print("Note: Accessing the iMessage database requires special permissions.")
        print("You may need to grant Full Disk Access to Terminal in System Preferences.")
        return []
        
    # Calculate cutoff date
    cutoff_timestamp = int((datetime.now() - timedelta(days=days)).timestamp())
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get your Apple ID/phone number
        cursor.execute("SELECT ROWID, id FROM handle")
        handles = cursor.fetchall()
        
        training_examples = []
        
        # For each conversation partner
        for handle_id, handle_address in handles:
            print(f"Processing conversation with {handle_address}...")
            
            # First, check if the database has the message_attachment_join table (for reply references)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_attachment_join'")
            has_attachment_table = cursor.fetchone() is not None
            
            # Check if the database has the chat_message_join table (for thread context)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_message_join'")
            has_chat_message_table = cursor.fetchone() is not None
            
            # Get messages exchanged with this person
            cursor.execute("""
                SELECT 
                    m.ROWID, 
                    m.text, 
                    m.date, 
                    m.is_from_me,
                    h.id,
                    m.associated_message_guid,
                    m.associated_message_type
                FROM 
                    message m
                JOIN 
                    handle h ON m.handle_id = h.ROWID
                WHERE 
                    h.ROWID = ? AND
                    m.date/1000000000 + 978307200 > ? AND
                    m.text IS NOT NULL
                ORDER BY 
                    m.date ASC
            """, (handle_id, cutoff_timestamp))
            
            messages = cursor.fetchall()
            
            # Create a dictionary of messages by ROWID for quick lookup
            message_dict = {msg[0]: msg for msg in messages}
            
            # Create a dictionary to track which messages are replies to other messages
            reply_map = {}
            
            # If the database has the necessary tables, try to extract reply information
            if has_attachment_table:
                # Try to get reply associations
                try:
                    cursor.execute("""
                        SELECT 
                            message_id, 
                            target_message_id
                        FROM 
                            message_attachment_join
                        WHERE 
                            message_id IN (SELECT ROWID FROM message WHERE handle_id = ?)
                    """, (handle_id,))
                    
                    reply_associations = cursor.fetchall()
                    for msg_id, target_id in reply_associations:
                        if msg_id in message_dict and target_id in message_dict:
                            reply_map[msg_id] = target_id
                except sqlite3.Error as e:
                    print(f"Could not extract reply information: {e}")
            
            # Process messages into training examples
            processed_count = 0
            
            # First, process sequential pairs (standard conversation flow)
            for i in range(len(messages) - 1):
                current_msg = messages[i]
                next_msg = messages[i + 1]
                
                # We want pairs where: they message you, then you respond
                if current_msg[3] == 0 and next_msg[3] == 1:  # is_from_me: 0=them, 1=you
                    # Check if this is a threaded reply
                    is_threaded_reply = False
                    
                    # Check associated_message_guid and associated_message_type for reply info
                    if next_msg[5] and next_msg[6] in [1, 3]:  # Types 1 and 3 are often used for replies
                        is_threaded_reply = True
                    
                    # If it's not a threaded reply, create a standard training example
                    if not is_threaded_reply:
                        # Create a training example
                        example = {
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": current_msg[1]},  # text
                                {"role": "assistant", "content": next_msg[1]}  # text
                            ]
                        }
                        
                        # Add to training examples if both messages have content
                        if current_msg[1] and next_msg[1]:
                            training_examples.append(example)
                            processed_count += 1
            
            # Now process threaded replies using the reply_map
            for msg_id, target_id in reply_map.items():
                if msg_id in message_dict and target_id in message_dict:
                    reply_msg = message_dict[msg_id]
                    target_msg = message_dict[target_id]
                    
                    # Only process if the reply is from you and the target is from them
                    if reply_msg[3] == 1 and target_msg[3] == 0:  # is_from_me
                        # Create a training example for the threaded reply
                        example = {
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": target_msg[1]},  # original message text
                                {"role": "assistant", "content": reply_msg[1]}  # your reply text
                            ]
                        }
                        
                        # Add to training examples if both messages have content
                        if target_msg[1] and reply_msg[1]:
                            training_examples.append(example)
                            processed_count += 1
            
            print(f"Processed {processed_count} examples from conversation with {handle_address}")
        
        print(f"Extracted {len(training_examples)} total training examples from iMessage database")
        return training_examples
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return []
    except Exception as e:
        print(f"Error accessing iMessage database: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def extract_from_manual_input():
    """
    Allow manual input of conversation examples
    
    Returns:
        list: Training examples in the format required for fine-tuning
    """
    print("\n=== Manual Conversation Input ===")
    print("Enter conversation pairs. Empty input to finish.")
    
    training_examples = []
    pair_count = 1
    
    while True:
        print(f"\nConversation Pair #{pair_count}")
        user_message = input("Their message: ").strip()
        
        if not user_message:
            break
            
        your_response = input("Your response: ").strip()
        
        if not your_response:
            break
            
        # Create a training example
        example = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": your_response}
            ]
        }
        
        training_examples.append(example)
        pair_count += 1
    
    print(f"Added {len(training_examples)} manual training examples")
    return training_examples


def save_training_data(training_examples, output_prefix=None):
    """
    Save training examples to JSONL files
    
    Args:
        training_examples: List of training examples
        output_prefix: Prefix for output files
        
    Returns:
        dict: Information about the saved files
    """
    if not training_examples:
        print("No training examples to save")
        return {}
        
    # Create timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use provided prefix or default
    if not output_prefix:
        output_prefix = os.path.join(MODELS_DIR, f"imessage_clone_{timestamp}")
        
    # Split into training and validation sets (90/10 split)
    split_idx = int(len(training_examples) * 0.9)
    train_examples = training_examples[:split_idx]
    val_examples = training_examples[split_idx:]
    
    # Save training data
    train_file = f"{output_prefix}_train.jsonl"
    with open(train_file, 'w', encoding='utf-8') as f:
        for example in train_examples:
            f.write(json.dumps(example) + '\n')
    
    # Save validation data
    val_file = f"{output_prefix}_val.jsonl"
    with open(val_file, 'w', encoding='utf-8') as f:
        for example in val_examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"\nSaved {len(train_examples)} training examples to {train_file}")
    print(f"Saved {len(val_examples)} validation examples to {val_file}")
    
    return {
        'train_file': train_file,
        'val_file': val_file,
        'train_count': len(train_examples),
        'val_count': len(val_examples)
    }


def save_raw_imessage_data(messages_by_conversation, output_path=None):
    """
    Save the raw extracted iMessage data to a JSON file for review
    
    Args:
        messages_by_conversation: Dictionary of conversations and their messages
        output_path: Path to save the JSON file
        
    Returns:
        str: Path to the saved file
    """
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(DATA_DIR, f"imessage_raw_{timestamp}.json")
    
    # Format the data for better readability
    formatted_data = []
    
    for contact, messages in messages_by_conversation.items():
        conversation = {
            "contact": contact,
            "messages": []
        }
        
        for msg in messages:
            # Convert timestamp to readable format
            timestamp = datetime.fromtimestamp(msg[2]/1000000000 + 978307200).isoformat()
            
            formatted_msg = {
                "id": msg[0],
                "text": msg[1],
                "timestamp": timestamp,
                "is_from_me": bool(msg[3]),
                "has_thread_info": bool(msg[5] and msg[6] in [1, 3])
            }
            
            conversation["messages"].append(formatted_msg)
        
        formatted_data.append(conversation)
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nRaw iMessage data saved to {output_path}")
    return output_path


def extract_from_imessage_db(days=7, save_raw=True):
    """
    Extract training data from macOS iMessage database
    Note: This requires special permissions to access the Messages database
    
    Args:
        days: Number of days of history to extract
        save_raw: Whether to save raw data to a JSON file
        
    Returns:
        tuple: (training_examples, raw_data_path)
    """
    print("Attempting to extract data from iMessage database...")
    
    # Path to iMessage database
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    
    if not os.path.exists(db_path):
        print(f"Error: iMessage database not found at {db_path}")
        print("Note: Accessing the iMessage database requires special permissions.")
        print("You may need to grant Full Disk Access to Terminal in System Preferences.")
        return [], None
        
    # Calculate cutoff date
    cutoff_timestamp = int((datetime.now() - timedelta(days=days)).timestamp())
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get your Apple ID/phone number
        cursor.execute("SELECT ROWID, id FROM handle")
        handles = cursor.fetchall()
        
        training_examples = []
        messages_by_conversation = {}  # Store messages by conversation for raw data
        
        # For each conversation partner
        for handle_id, handle_address in handles:
            print(f"Processing conversation with {handle_address}...")
            
            # First, check if the database has the message_attachment_join table (for reply references)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_attachment_join'")
            has_attachment_table = cursor.fetchone() is not None
            
            # Check if the database has the chat_message_join table (for thread context)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_message_join'")
            has_chat_message_table = cursor.fetchone() is not None
            
            # Get messages exchanged with this person
            cursor.execute("""
                SELECT 
                    m.ROWID, 
                    m.text, 
                    m.date, 
                    m.is_from_me,
                    h.id,
                    m.associated_message_guid,
                    m.associated_message_type
                FROM 
                    message m
                JOIN 
                    handle h ON m.handle_id = h.ROWID
                WHERE 
                    h.ROWID = ? AND
                    m.date/1000000000 + 978307200 > ? AND
                    m.text IS NOT NULL
                ORDER BY 
                    m.date ASC
            """, (handle_id, cutoff_timestamp))
            
            messages = cursor.fetchall()
            
            # Store messages for this conversation
            if messages:
                messages_by_conversation[handle_address] = messages
            
            # Create a dictionary of messages by ROWID for quick lookup
            message_dict = {msg[0]: msg for msg in messages}
            
            # Create a dictionary to track which messages are replies to other messages
            reply_map = {}
            
            # If the database has the necessary tables, try to extract reply information
            if has_attachment_table:
                # Try to get reply associations
                try:
                    cursor.execute("""
                        SELECT 
                            message_id, 
                            target_message_id
                        FROM 
                            message_attachment_join
                        WHERE 
                            message_id IN (SELECT ROWID FROM message WHERE handle_id = ?)
                    """, (handle_id,))
                    
                    reply_associations = cursor.fetchall()
                    for msg_id, target_id in reply_associations:
                        if msg_id in message_dict and target_id in message_dict:
                            reply_map[msg_id] = target_id
                except sqlite3.Error as e:
                    print(f"Could not extract reply information: {e}")
            
            # Process messages into training examples
            processed_count = 0
            
            # First, process sequential pairs (standard conversation flow)
            for i in range(len(messages) - 1):
                current_msg = messages[i]
                next_msg = messages[i + 1]
                
                # We want pairs where: they message you, then you respond
                if current_msg[3] == 0 and next_msg[3] == 1:  # is_from_me: 0=them, 1=you
                    # Check if this is a threaded reply
                    is_threaded_reply = False
                    
                    # Check associated_message_guid and associated_message_type for reply info
                    if next_msg[5] and next_msg[6] in [1, 3]:  # Types 1 and 3 are often used for replies
                        is_threaded_reply = True
                    
                    # If it's not a threaded reply, create a standard training example
                    if not is_threaded_reply:
                        # Create a training example
                        example = {
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": current_msg[1]},  # text
                                {"role": "assistant", "content": next_msg[1]}  # text
                            ]
                        }
                        
                        # Add to training examples if both messages have content
                        if current_msg[1] and next_msg[1]:
                            training_examples.append(example)
                            processed_count += 1
            
            # Now process threaded replies using the reply_map
            for msg_id, target_id in reply_map.items():
                if msg_id in message_dict and target_id in message_dict:
                    reply_msg = message_dict[msg_id]
                    target_msg = message_dict[target_id]
                    
                    # Only process if the reply is from you and the target is from them
                    if reply_msg[3] == 1 and target_msg[3] == 0:  # is_from_me
                        # Create a training example for the threaded reply
                        example = {
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": target_msg[1]},  # original message text
                                {"role": "assistant", "content": reply_msg[1]}  # your reply text
                            ]
                        }
                        
                        # Add to training examples if both messages have content
                        if target_msg[1] and reply_msg[1]:
                            training_examples.append(example)
                            processed_count += 1
            
            print(f"Processed {processed_count} examples from conversation with {handle_address}")
        
        print(f"Extracted {len(training_examples)} total training examples from iMessage database")
        
        # Save raw data if requested
        raw_data_path = None
        if save_raw and messages_by_conversation:
            raw_data_path = save_raw_imessage_data(messages_by_conversation)
        
        return training_examples, raw_data_path
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return [], None
    except Exception as e:
        print(f"Error accessing iMessage database: {e}")
        return [], None
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    parser = argparse.ArgumentParser(description='Extract training data from iMessage conversations')
    parser.add_argument('--days', type=int, default=7, help='Number of days of history to extract')
    parser.add_argument('--output', type=str, help='Output file prefix')
    parser.add_argument('--raw-only', action='store_true', help='Only extract raw data, do not create training files')
    
    args = parser.parse_args()
    
    # Extract from iMessage database - always save raw data
    training_examples, raw_data_path = extract_from_imessage_db(days=args.days, save_raw=True)
    
    # If raw-only flag is set, don't create training files
    if args.raw_only:
        if raw_data_path:
            print("\nRaw data extraction complete!")
            print(f"Raw data saved to: {raw_data_path}")
            print("You can review this file to check the accuracy of the extraction.")
        else:
            print("\nNo raw data was extracted.")
        return
    
    # Save training data
    if training_examples:
        data_info = save_training_data(training_examples, args.output)
        print("\nTraining data extraction complete!")
        print("You can now use these files for fine-tuning your model.")
        
        if raw_data_path:
            print(f"\nRaw data saved to: {raw_data_path}")
            print("You can review this file to check the accuracy of the extraction.")
    else:
        print("\nNo training examples were extracted.")


if __name__ == "__main__":
    print("=== Conversation Training Data Extractor ===\n")
    main()
