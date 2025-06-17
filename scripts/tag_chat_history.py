#!/usr/bin/env python3

"""
Utility script to tag conversations in chat_history.json with model version information
and clean up the RAG database by removing problematic examples.
"""

import os
import json
import argparse
from datetime import datetime, timedelta

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')
RAG_DIR = os.path.join(DATA_DIR, 'rag')
DEFAULT_RAG_DB = os.path.join(RAG_DIR, 'default_message_db.json')

def tag_messages_by_date(chat_history_path=CHAT_HISTORY_PATH, cutoff_dates=None, dry_run=True):
    """
    Tag messages in chat_history.json with model version information based on date ranges.
    
    Args:
        chat_history_path: Path to chat history JSON file
        cutoff_dates: Dictionary mapping dates to model versions
        dry_run: If True, don't actually modify the file
        
    Returns:
        dict: Statistics about the tagging operation
    """
    if cutoff_dates is None:
        # Default model version cutoff dates - adjust these based on your actual model deployment dates
        cutoff_dates = {
            "2025-03-05": "v1.0",  # Initial model
            "2025-03-07": "v1.1",  # First improvement
            "2025-03-10": "v1.2",  # Second improvement
            "2025-03-13": "v1.3",  # Latest model
        }
    
    try:
        # Load chat history
        with open(chat_history_path, 'r') as f:
            chat_data = json.load(f)
            
        # Statistics
        stats = {
            'total_conversations': len(chat_data.get('conversations', [])),
            'total_messages': 0,
            'tagged_messages': 0,
            'model_versions': {}
        }
        
        # Convert cutoff dates to datetime objects - make them timezone-naive
        date_version_map = {}
        for date_str, version in cutoff_dates.items():
            try:
                # Create naive datetime objects for comparison
                date_obj = datetime.fromisoformat(date_str)
                date_version_map[date_obj] = version
            except ValueError:
                print(f"Invalid date format: {date_str}")
        
        # Sort dates for easier comparison
        sorted_dates = sorted(date_version_map.keys())
        
        # Process each conversation
        for conversation in chat_data.get('conversations', []):
            # Add conversation-level model_version field if not already present
            if 'model_version' not in conversation:
                # Default to the latest model version
                conversation['model_version'] = date_version_map[sorted_dates[-1]]
                stats['tagged_conversations'] = stats.get('tagged_conversations', 0) + 1
                
            # Process each message
            messages = conversation.get('messages', [])
            stats['total_messages'] += len(messages)
            
            for msg in messages:
                timestamp_str = msg.get('timestamp', '')
                
                try:
                    # Parse timestamp and make it naive by removing timezone info
                    if 'Z' in timestamp_str:
                        # Handle UTC 'Z' format
                        timestamp_str = timestamp_str.replace('Z', '+00:00')
                    
                    # Parse the timestamp
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    # Remove timezone info if present to make it naive
                    if timestamp.tzinfo is not None:
                        timestamp = timestamp.replace(tzinfo=None)
                    
                    # Determine model version based on date
                    model_version = None
                    for cutoff_date in sorted_dates:
                        if timestamp >= cutoff_date:
                            model_version = date_version_map[cutoff_date]
                    
                    # Tag message with model version
                    if model_version:
                        if 'model_version' not in msg:
                            msg['model_version'] = model_version
                            stats['tagged_messages'] += 1
                            stats['model_versions'][model_version] = stats['model_versions'].get(model_version, 0) + 1
                        
                except (ValueError, TypeError) as e:
                    print(f"Error parsing timestamp: {timestamp_str} - {str(e)}")
        
        # Save updated chat history
        if not dry_run:
            # Create backup
            backup_path = f"{chat_history_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            with open(backup_path, 'w') as f:
                json.dump(chat_data, f, indent=2)
            print(f"Created backup at {backup_path}")
            
            # Save updated file
            with open(chat_history_path, 'w') as f:
                json.dump(chat_data, f, indent=2)
            print(f"Updated chat history with model version tags")
        else:
            print("Dry run - no changes made to chat history file")
            
        return stats
        
    except Exception as e:
        print(f"Error tagging messages: {str(e)}")
        return {'error': str(e)}

def clean_rag_database(rag_db_path=DEFAULT_RAG_DB, min_model_version=None, min_date=None, dry_run=True):
    """
    Clean the RAG database by removing examples from older model versions or before a certain date.
    
    Args:
        rag_db_path: Path to RAG database JSON file
        min_model_version: Minimum model version to keep
        min_date: Minimum date to keep (ISO format)
        dry_run: If True, don't actually modify the file
        
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
            'kept_messages': 0
        }
        
        # Convert min_date to datetime object if provided
        min_datetime = None
        if min_date:
            try:
                min_datetime = datetime.fromisoformat(min_date.replace('Z', '+00:00'))
                print(f"Filtering messages after {min_datetime}")
            except (ValueError, TypeError) as e:
                print(f"Invalid min_date format: {e}")
        
        # Filter messages
        filtered_messages = []
        for msg in rag_db.get('messages', []):
            keep_message = True
            
            # Check model version if specified
            if min_model_version and 'model_version' in msg:
                if msg['model_version'] is None or msg['model_version'] < min_model_version:
                    keep_message = False
            
            # Check date if specified
            if keep_message and min_datetime and 'timestamp' in msg:
                try:
                    msg_datetime = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    
                    # Remove timezone info if present to make it naive
                    if msg_datetime.tzinfo is not None:
                        msg_datetime = msg_datetime.replace(tzinfo=None)
                    
                    if msg_datetime < min_datetime:
                        keep_message = False
                except (ValueError, TypeError):
                    # If we can't parse the timestamp, keep the message by default
                    pass
            
            if keep_message:
                filtered_messages.append(msg)
                stats['kept_messages'] += 1
            else:
                stats['removed_messages'] += 1
        
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
    parser = argparse.ArgumentParser(description='Tag chat history with model versions and clean RAG database')
    parser.add_argument('--tag', action='store_true', help='Tag chat history with model versions')
    parser.add_argument('--clean', action='store_true', help='Clean RAG database')
    parser.add_argument('--chat-history', type=str, default=CHAT_HISTORY_PATH, help='Path to chat history JSON file')
    parser.add_argument('--rag-db', type=str, default=DEFAULT_RAG_DB, help='Path to RAG database JSON file')
    parser.add_argument('--min-version', type=str, help='Minimum model version to keep in RAG database')
    parser.add_argument('--min-date', type=str, help='Minimum date to keep in RAG database (YYYY-MM-DD)')
    parser.add_argument('--no-dry-run', action='store_true', help='Actually modify files (default is dry run)')
    
    args = parser.parse_args()
    
    # Default to both operations if none specified
    if not args.tag and not args.clean:
        args.tag = True
        args.clean = True
    
    # Tag chat history
    if args.tag:
        print(f"\nTagging messages in chat history at {args.chat_history}...")
        stats = tag_messages_by_date(args.chat_history, dry_run=not args.no_dry_run)
        
        print("\nTagging Statistics:")
        print(f"Total conversations: {stats.get('total_conversations', 0)}")
        print(f"Total messages: {stats.get('total_messages', 0)}")
        print(f"Tagged messages: {stats.get('tagged_messages', 0)}")
        
        if 'model_versions' in stats:
            print("\nModel Version Distribution:")
            for version, count in stats['model_versions'].items():
                print(f"  {version}: {count} messages")
    
    # Clean RAG database
    if args.clean:
        min_date = args.min_date
        if min_date and len(min_date) == 10:  # YYYY-MM-DD format
            min_date = f"{min_date}T00:00:00"
            
        print(f"\nCleaning RAG database at {args.rag_db}...")
        stats = clean_rag_database(
            args.rag_db, 
            min_model_version=args.min_version,
            min_date=min_date,
            dry_run=not args.no_dry_run
        )
        
        print("\nCleaning Statistics:")
        print(f"Total messages: {stats.get('total_messages', 0)}")
        print(f"Removed messages: {stats.get('removed_messages', 0)}")
        print(f"Kept messages: {stats.get('kept_messages', 0)}")
        
        if 'error' in stats:
            print(f"\nError: {stats['error']}")

if __name__ == "__main__":
    main()
