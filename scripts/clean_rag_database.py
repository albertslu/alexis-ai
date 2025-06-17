#!/usr/bin/env python3

"""
Utility script to clean up the RAG database by removing problematic examples
from earlier models that could be confusing the AI clone.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RAG_DIR = os.path.join(DATA_DIR, 'rag')
DEFAULT_RAG_DB = os.path.join(RAG_DIR, 'default_message_db.json')

def clean_rag_database(rag_db_path=DEFAULT_RAG_DB, min_date=None, dry_run=True, 
                      remove_problematic_patterns=True, remove_by_date=True):
    """
    Clean the RAG database by removing problematic examples from earlier models.
    
    Args:
        rag_db_path: Path to RAG database JSON file
        min_date: Minimum date to keep (ISO format)
        dry_run: If True, don't actually modify the file
        remove_problematic_patterns: Remove messages with problematic patterns
        remove_by_date: Remove messages before min_date
        
    Returns:
        dict: Statistics about the cleaning operation
    """
    try:
        # Load RAG database
        with open(rag_db_path, 'r') as f:
            rag_db = json.load(f)
            
        # Statistics
        stats = {
            'total_messages': len(rag_db.get('messages', [])),
            'removed_messages': 0,
            'kept_messages': 0,
            'removal_reasons': {
                'date': 0,
                'problematic_pattern': 0,
                'self_reference': 0,
                'irrelevant_response': 0
            }
        }
        
        # Convert min_date to datetime object if provided
        min_datetime = None
        if min_date and remove_by_date:
            try:
                min_datetime = datetime.fromisoformat(min_date.replace('Z', '+00:00'))
                if min_datetime.tzinfo is not None:
                    min_datetime = min_datetime.replace(tzinfo=None)
                print(f"Filtering messages after {min_datetime}")
            except (ValueError, TypeError) as e:
                print(f"Invalid min_date format: {e}")
        
        # Problematic patterns to filter out
        problematic_patterns = [
            r"i am currently waiting for you to ask me",
            r"i can ask you some questions",
            r"besides these that i already answered",
            r"what ask me some more",
            r"ask me some more besides these",
            r"ask me some questions",
            r"what would you like to know about me",
            r"i'm not sure what you're asking",
            r"i don't understand the question",
            r"i don't know how to respond to that",
            r"i'm sorry, i don't understand",
            r"i'm an ai assistant",
            r"as an ai",
            r"i'm not a real person",
            r"i'm just a language model",
            r"i don't have access to",
            r"i don't have the ability to"
        ]
        
        # Filter messages
        filtered_messages = []
        for msg in rag_db.get('messages', []):
            keep_message = True
            removal_reason = None
            
            # Check date if specified
            if keep_message and min_datetime and remove_by_date and 'timestamp' in msg:
                try:
                    msg_datetime = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    if msg_datetime.tzinfo is not None:
                        msg_datetime = msg_datetime.replace(tzinfo=None)
                    if msg_datetime < min_datetime:
                        keep_message = False
                        removal_reason = 'date'
                except (ValueError, TypeError):
                    # If we can't parse the timestamp, keep the message by default
                    pass
            
            # Check for problematic patterns
            if keep_message and remove_problematic_patterns and 'text' in msg and msg.get('sender') == 'clone':
                text = msg.get('text', '').lower().strip()
                
                # Check for self-referential or meta responses
                if any(re.search(pattern, text) for pattern in problematic_patterns):
                    keep_message = False
                    removal_reason = 'problematic_pattern'
                
                # Check for responses that reference being an AI
                elif any(phrase in text for phrase in ["i'm an ai", "as an ai", "i'm not a real person", "i'm just a language model"]):
                    keep_message = False
                    removal_reason = 'self_reference'
                
                # Check for irrelevant responses
                elif any(phrase in text for phrase in ["i don't have access to", "i don't have the ability to"]):
                    keep_message = False
                    removal_reason = 'irrelevant_response'
            
            if keep_message:
                filtered_messages.append(msg)
                stats['kept_messages'] += 1
            else:
                stats['removed_messages'] += 1
                if removal_reason:
                    stats['removal_reasons'][removal_reason] = stats['removal_reasons'].get(removal_reason, 0) + 1
        
        # Update database
        if not dry_run and stats['removed_messages'] > 0:
            # Create backup
            backup_path = f"{rag_db_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            with open(backup_path, 'w') as f:
                json.dump(rag_db, f, indent=2)
            print(f"Created backup at {backup_path}")
            
            # Save updated database
            rag_db['messages'] = filtered_messages
            with open(rag_db_path, 'w') as f:
                json.dump(rag_db, f, indent=2)
            print(f"Updated RAG database - removed {stats['removed_messages']} messages")
        else:
            if dry_run:
                print("Dry run - no changes made to RAG database")
            else:
                print("No messages removed from RAG database")
        
        return stats
        
    except Exception as e:
        print(f"Error cleaning RAG database: {str(e)}")
        return {'error': str(e)}

def main():
    parser = argparse.ArgumentParser(description='Clean RAG database by removing problematic examples')
    parser.add_argument('--rag-db', type=str, default=DEFAULT_RAG_DB, help='Path to RAG database JSON file')
    parser.add_argument('--min-date', type=str, help='Minimum date to keep in RAG database (YYYY-MM-DD)')
    parser.add_argument('--no-date-filter', action='store_true', help='Don\'t filter by date')
    parser.add_argument('--no-pattern-filter', action='store_true', help='Don\'t filter by problematic patterns')
    parser.add_argument('--no-dry-run', action='store_true', help='Actually modify files (default is dry run)')
    
    args = parser.parse_args()
    
    # Format min_date if provided
    min_date = args.min_date
    if min_date and len(min_date) == 10:  # YYYY-MM-DD format
        min_date = f"{min_date}T00:00:00"
    
    print(f"\nCleaning RAG database at {args.rag_db}...")
    stats = clean_rag_database(
        args.rag_db,
        min_date=min_date,
        dry_run=not args.no_dry_run,
        remove_problematic_patterns=not args.no_pattern_filter,
        remove_by_date=not args.no_date_filter
    )
    
    print("\nCleaning Statistics:")
    print(f"Total messages: {stats.get('total_messages', 0)}")
    print(f"Removed messages: {stats.get('removed_messages', 0)}")
    print(f"Kept messages: {stats.get('kept_messages', 0)}")
    
    if 'removal_reasons' in stats:
        print("\nRemoval Reasons:")
        for reason, count in stats['removal_reasons'].items():
            if count > 0:
                print(f"  {reason}: {count} messages")
    
    if 'error' in stats:
        print(f"\nError: {stats['error']}")

if __name__ == "__main__":
    main()
