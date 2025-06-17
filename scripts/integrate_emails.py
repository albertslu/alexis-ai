#!/usr/bin/env python3
"""
Email Integration Script for AI Clone

This script integrates extracted emails into the RAG system.

Usage:
    python integrate_emails.py --email_data ../data/email_data.json
"""

import os
import json
import argparse
import sys
import numpy as np
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import RAG utilities
from rag.rag_system import MessageRAG

def load_email_data(file_path):
    """
    Load extracted email data
    
    Args:
        file_path: Path to email data JSON file
        
    Returns:
        List of email data items
    """
    if not os.path.exists(file_path):
        print(f"Error: Email data file not found at {file_path}")
        return []
    
    with open(file_path, 'r') as f:
        return json.load(f)

def preprocess_for_rag(email_items):
    """
    Preprocess email items for RAG system
    
    Args:
        email_items: List of email data items
        
    Returns:
        List of processed items ready for RAG
    """
    processed_items = []
    
    for item in email_items:
        # Extract content and metadata
        content = item['content']
        metadata = item['metadata']
        
        # Prepare text and context
        text = content  # The email content is the main text
        
        # Create RAG item with channel-specific metadata
        rag_item = {
            'text': text,
            'metadata': {
                'channel': 'email',  # Tag with email channel
                'timestamp': metadata['timestamp'],
                'subject': metadata.get('subject', ''),
                'formality_score': metadata.get('formality_score', 0.5),
                'is_response': 'context' in item,
                'recipients': metadata.get('recipients', ''),
                'context': item.get('context', {}).get('previous_message', '') if 'context' in item else ''
            }
        }
        
        processed_items.append(rag_item)
    
    return processed_items

def integrate_with_rag(email_items, rag_system):
    """
    Integrate email items with RAG system
    
    Args:
        email_items: Preprocessed email items
        rag_system: RAG system instance
        
    Returns:
        Number of items added
    """
    # Convert to the format expected by add_message_batch
    message_batch = []
    
    for item in email_items:
        message_entry = {
            'text': item['text'],
            'previous_message': item['metadata'].get('context', ''),
            'sender': 'user',
            'timestamp': item['metadata']['timestamp']
        }
        message_batch.append(message_entry)
    
    # Add the batch to the RAG system
    try:
        rag_system.add_message_batch(message_batch)
        added_count = len(message_batch)
        print(f"Added {added_count} email items to RAG system")
    except Exception as e:
        print(f"Error adding items to RAG: {str(e)}")
        added_count = 0
    
    return added_count

def main():
    parser = argparse.ArgumentParser(description='Integrate emails into RAG system')
    parser.add_argument('--email_data', type=str, default='../data/email_data.json',
                        help='Path to email data JSON file')
    parser.add_argument('--rag_db', type=str, default='../data/rag_database.json',
                        help='Path to RAG database')
    args = parser.parse_args()
    
    # Load email data
    print(f"Loading email data from {args.email_data}...")
    email_data = load_email_data(args.email_data)
    
    if not email_data:
        print("No email data found. Exiting.")
        return
    
    print(f"Loaded {len(email_data)} email items.")
    
    # Preprocess for RAG
    print("Preprocessing email data for RAG...")
    processed_items = preprocess_for_rag(email_data)
    
    # Initialize RAG system
    print(f"Initializing RAG system from {args.rag_db}...")
    # Extract directory from the path
    rag_db_dir = os.path.dirname(args.rag_db)
    rag_db_name = os.path.basename(args.rag_db)
    user_id = rag_db_name.split('_')[0] if '_' in rag_db_name else 'default'
    
    # Ensure the directory exists
    os.makedirs(rag_db_dir, exist_ok=True)
    
    # Initialize the MessageRAG with the appropriate user_id
    rag_system = MessageRAG(user_id=user_id)
    
    # Integrate with RAG
    print("Integrating emails with RAG system...")
    added_count = integrate_with_rag(processed_items, rag_system)
    
    print(f"Successfully added {added_count} email items to RAG system.")
    print(f"Total items in RAG system: {len(rag_system.messages)}")
    
    # Save RAG database
    rag_system.save_database()
    print(f"RAG database saved to {args.rag_db}")

if __name__ == "__main__":
    main()
