#!/usr/bin/env python3

"""
Chat History Analysis Tool for AI Clone

This script analyzes the chat history to identify patterns of repetition and poor responses.
It helps diagnose issues with the AI clone's response generation and can clean problematic
examples from the RAG database.
"""

import os
import json
import re
from datetime import datetime
import argparse

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')
RAG_DIR = os.path.join(DATA_DIR, 'rag')
DEFAULT_RAG_DB = os.path.join(RAG_DIR, 'default_message_db.json')

def calculate_similarity(text1, text2):
    """
    Calculate similarity between two text strings.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        float: Similarity score (0-1)
    """
    # Convert to lowercase
    text1 = text1.lower()
    text2 = text2.lower()
    
    # Remove punctuation
    text1 = re.sub(r'[^\w\s]', '', text1)
    text2 = re.sub(r'[^\w\s]', '', text2)
    
    # Get word sets
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    # Calculate Jaccard similarity
    if not words1 or not words2:
        return 0.0
        
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union

def is_repetitive_response(user_message, ai_response):
    """
    Check if the AI response is repetitive of the user message.
    
    Args:
        user_message: User's message
        ai_response: AI's response
        
    Returns:
        bool: True if repetitive, False otherwise
    """
    # Convert to lowercase
    user_lower = user_message.lower()
    ai_lower = ai_response.lower()
    
    # Check for exact repetition
    if user_lower == ai_lower:
        return True
        
    # Check if AI response contains the entire user message
    if len(user_message.split()) > 2 and user_lower in ai_lower:
        return True
        
    # Check if AI response starts with the user message
    if ai_lower.startswith(user_lower) and len(user_message.split()) > 1:
        return True
        
    # Check for high similarity
    similarity = calculate_similarity(user_message, ai_response)
    if similarity > 0.7:  # High threshold for repetition
        return True
        
    # Check for question repetition pattern
    if '?' in user_message and user_lower in ai_lower:
        return True
        
    return False

def analyze_chat_history(chat_history_path=CHAT_HISTORY_PATH):
    """
    Analyze chat history to identify patterns of repetition and poor responses.
    
    Args:
        chat_history_path: Path to chat history JSON file
        
    Returns:
        dict: Analysis results
    """
    try:
        with open(chat_history_path, 'r') as f:
            chat_history = json.load(f)
    except Exception as e:
        print(f"Error loading chat history: {str(e)}")
        return {}
        
    # Analysis results
    results = {
        'total_conversations': 0,
        'total_messages': 0,
        'repetitive_responses': 0,
        'short_responses': 0,
        'question_responses': 0,
        'problematic_conversations': [],
        'repetition_examples': []
    }
    
    # Analyze conversations
    for conversation in chat_history.get('conversations', []):
        results['total_conversations'] += 1
        messages = conversation.get('messages', [])
        results['total_messages'] += len(messages)
        
        # Track conversation-level issues
        has_repetition = False
        
        # Analyze message pairs
        for i in range(len(messages) - 1):
            if messages[i].get('sender') == 'user' and messages[i+1].get('sender') in ['clone', 'assistant']:
                user_message = messages[i].get('text', '')
                ai_response = messages[i+1].get('text', '')
                
                # Check for repetitive responses
                if is_repetitive_response(user_message, ai_response):
                    results['repetitive_responses'] += 1
                    has_repetition = True
                    
                    # Add to examples
                    results['repetition_examples'].append({
                        'conversation_id': conversation.get('id'),
                        'user_message': user_message,
                        'ai_response': ai_response,
                        'timestamp': messages[i+1].get('timestamp')
                    })
                
                # Check for very short responses
                if len(ai_response.split()) <= 2:
                    results['short_responses'] += 1
                    
                # Check for question responses
                if '?' in user_message and '?' in ai_response:
                    results['question_responses'] += 1
        
        # Add problematic conversation
        if has_repetition:
            results['problematic_conversations'].append({
                'id': conversation.get('id'),
                'message_count': len(messages)
            })
    
    return results

def clean_rag_database(rag_db_path=DEFAULT_RAG_DB, dry_run=True):
    """
    Clean the RAG database by removing examples that might lead to repetition.
    
    Args:
        rag_db_path: Path to RAG database JSON file
        dry_run: If True, don't actually modify the database
        
    Returns:
        dict: Cleaning results
    """
    try:
        with open(rag_db_path, 'r') as f:
            rag_db = json.load(f)
    except Exception as e:
        print(f"Error loading RAG database: {str(e)}")
        return {}
        
    # Cleaning results
    results = {
        'total_messages': len(rag_db.get('messages', [])),
        'removed_messages': 0,
        'removed_examples': []
    }
    
    # Filter messages
    filtered_messages = []
    for msg in rag_db.get('messages', []):
        context = msg.get('context', '')
        text = msg.get('text', '')
        
        # Skip if either is empty
        if not context or not text:
            filtered_messages.append(msg)
            continue
            
        # Check if this is a repetitive example
        if is_repetitive_response(context, text):
            results['removed_messages'] += 1
            results['removed_examples'].append({
                'context': context,
                'text': text
            })
        else:
            filtered_messages.append(msg)
    
    # Update database if not dry run
    if not dry_run:
        rag_db['messages'] = filtered_messages
        
        # Create backup
        backup_path = f"{rag_db_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            with open(backup_path, 'w') as f:
                json.dump(rag_db, f, indent=2)
            print(f"Created backup at {backup_path}")
        except Exception as e:
            print(f"Error creating backup: {str(e)}")
            return results
            
        # Save cleaned database
        try:
            with open(rag_db_path, 'w') as f:
                json.dump(rag_db, f, indent=2)
            print(f"Saved cleaned database with {len(filtered_messages)} messages (removed {results['removed_messages']})")
        except Exception as e:
            print(f"Error saving cleaned database: {str(e)}")
    else:
        print(f"Dry run: Would remove {results['removed_messages']} messages from database")
    
    return results

def add_good_examples(rag_db_path=DEFAULT_RAG_DB, dry_run=True):
    """
    Add good examples to the RAG database to improve response quality.
    
    Args:
        rag_db_path: Path to RAG database JSON file
        dry_run: If True, don't actually modify the database
        
    Returns:
        int: Number of examples added
    """
    try:
        with open(rag_db_path, 'r') as f:
            rag_db = json.load(f)
    except Exception as e:
        print(f"Error loading RAG database: {str(e)}")
        return 0
        
    # Good examples for text messages
    good_examples = [
        {
            "context": "how are you?",
            "text": "doing well! just finished a project. how about you?",
            "sender": "user",
            "timestamp": datetime.now().isoformat(),
            "keywords": ["doing", "well", "finished", "project"],
            "metadata": {"channel": "text", "quality": "high"}
        },
        {
            "context": "what are you up to?",
            "text": "working on some code and grabbing coffee. you?",
            "sender": "user",
            "timestamp": datetime.now().isoformat(),
            "keywords": ["working", "code", "grabbing", "coffee"],
            "metadata": {"channel": "text", "quality": "high"}
        },
        {
            "context": "why?",
            "text": "because i thought it would be more efficient that way. saves us time in the long run",
            "sender": "user",
            "timestamp": datetime.now().isoformat(),
            "keywords": ["thought", "efficient", "saves", "time", "long"],
            "metadata": {"channel": "text", "quality": "high"}
        },
        {
            "context": "how?",
            "text": "by using the new api they released. it handles all the authentication stuff automatically",
            "sender": "user",
            "timestamp": datetime.now().isoformat(),
            "keywords": ["using", "released", "handles", "authentication", "automatically"],
            "metadata": {"channel": "text", "quality": "high"}
        },
        {
            "context": "when will you be free?",
            "text": "probably around 5 today. need to finish this meeting first",
            "sender": "user",
            "timestamp": datetime.now().isoformat(),
            "keywords": ["probably", "around", "today", "need", "finish", "meeting"],
            "metadata": {"channel": "text", "quality": "high"}
        }
    ]
    
    # Add examples if not dry run
    if not dry_run:
        # Create backup
        backup_path = f"{rag_db_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            with open(backup_path, 'w') as f:
                json.dump(rag_db, f, indent=2)
            print(f"Created backup at {backup_path}")
        except Exception as e:
            print(f"Error creating backup: {str(e)}")
            return 0
            
        # Add examples
        rag_db['messages'].extend(good_examples)
        
        # Save updated database
        try:
            with open(rag_db_path, 'w') as f:
                json.dump(rag_db, f, indent=2)
            print(f"Added {len(good_examples)} good examples to database")
        except Exception as e:
            print(f"Error saving updated database: {str(e)}")
            return 0
    else:
        print(f"Dry run: Would add {len(good_examples)} good examples to database")
    
    return len(good_examples)

def main():
    parser = argparse.ArgumentParser(description='Chat History Analysis Tool for AI Clone')
    parser.add_argument('--analyze', action='store_true', help='Analyze chat history')
    parser.add_argument('--clean', action='store_true', help='Clean RAG database')
    parser.add_argument('--add-examples', action='store_true', help='Add good examples to RAG database')
    parser.add_argument('--no-dry-run', action='store_true', help='Actually modify the database (not just simulate)')
    parser.add_argument('--rag-db', type=str, default=DEFAULT_RAG_DB, help='Path to RAG database')
    parser.add_argument('--chat-history', type=str, default=CHAT_HISTORY_PATH, help='Path to chat history')
    
    args = parser.parse_args()
    
    # Default to analyze if no action specified
    if not (args.analyze or args.clean or args.add_examples):
        args.analyze = True
        
    # Analyze chat history
    if args.analyze:
        print(f"Analyzing chat history from {args.chat_history}...")
        results = analyze_chat_history(args.chat_history)
        
        print(f"\nAnalysis Results:")
        print(f"Total conversations: {results['total_conversations']}")
        print(f"Total messages: {results['total_messages']}")
        print(f"Repetitive responses: {results['repetitive_responses']} ({results['repetitive_responses']/max(1, results['total_messages'])*100:.1f}%)")
        print(f"Very short responses: {results['short_responses']} ({results['short_responses']/max(1, results['total_messages'])*100:.1f}%)")
        print(f"Question responses: {results['question_responses']} ({results['question_responses']/max(1, results['total_messages'])*100:.1f}%)")
        print(f"Problematic conversations: {len(results['problematic_conversations'])} ({len(results['problematic_conversations'])/max(1, results['total_conversations'])*100:.1f}%)")
        
        # Show examples of repetition
        if results['repetition_examples']:
            print(f"\nExamples of Repetitive Responses:")
            for i, example in enumerate(results['repetition_examples'][:5]):  # Show top 5
                print(f"\nExample {i+1}:")
                print(f"User: {example['user_message']}")
                print(f"AI: {example['ai_response']}")
    
    # Clean RAG database
    if args.clean:
        print(f"\nCleaning RAG database at {args.rag_db}...")
        results = clean_rag_database(args.rag_db, dry_run=not args.no_dry_run)
        
        print(f"\nCleaning Results:")
        print(f"Total messages in database: {results['total_messages']}")
        print(f"Messages to remove: {results['removed_messages']} ({results['removed_messages']/max(1, results['total_messages'])*100:.1f}%)")
        
        # Show examples of removed messages
        if results['removed_examples']:
            print(f"\nExamples of Removed Messages:")
            for i, example in enumerate(results['removed_examples'][:5]):  # Show top 5
                print(f"\nExample {i+1}:")
                print(f"Context: {example['context']}")
                print(f"Text: {example['text']}")
    
    # Add good examples
    if args.add_examples:
        print(f"\nAdding good examples to RAG database at {args.rag_db}...")
        count = add_good_examples(args.rag_db, dry_run=not args.no_dry_run)
        
        print(f"\nAdded {count} good examples to database")

if __name__ == "__main__":
    main()
