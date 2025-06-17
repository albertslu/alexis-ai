#!/usr/bin/env python3
"""
Clean Bad Responses from RAG Database

This script removes specific problematic messages from the chat history and RAG database
to prevent them from being used as examples for future responses.
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the RAG system
from rag.rag_system import MessageRAG

# Path to chat history
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')

def remove_bad_responses():
    """
    Remove specific bad responses from the chat history and RAG database.
    """
    print("Starting cleanup of bad responses from RAG database...")
    
    # Message IDs to remove (these are the problematic responses)
    bad_message_ids = [
        "4b1579b6-a05c-48e5-acb1-fba0470663b7",  # "yo bert who is the nba goat"
        "a2419d5b-29a2-40f5-8627-bb0ee8b7ec93",  # "who is better lebron or mj"
    ]
    
    # Load chat history
    try:
        with open(CHAT_HISTORY_PATH, 'r') as f:
            chat_history = json.load(f)
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return
    
    # Print messages that will be removed from RAG
    print("\nRemoving these messages from RAG database:")
    messages_to_remove = []
    for conversation in chat_history.get("conversations", []):
        for message in conversation.get("messages", []):
            if message.get("id") in bad_message_ids:
                messages_to_remove.append({
                    "id": message.get("id"),
                    "text": message.get("text")
                })
                print(f"  - {message.get('text')}")
    
    # Clear and reinitialize the RAG database
    print("\nReinitializing RAG database to remove bad examples...")
    try:
        # Initialize RAG with clear_existing=True to reset the database
        rag = MessageRAG(clear_existing=True)
        
        # Re-add messages from chat history, excluding the bad ones
        message_data = []
        for conversation in chat_history.get("conversations", []):
            for message in conversation.get("messages", []):
                # Only add clone messages to RAG (user messages are added as context)
                if message.get("sender") == "clone" and message.get("id") not in bad_message_ids:
                    # Find the preceding user message for context
                    idx = conversation["messages"].index(message)
                    previous_message = ""
                    if idx > 0 and conversation["messages"][idx-1].get("sender") == "user":
                        previous_message = conversation["messages"][idx-1].get("text", "")
                    
                    message_data.append({
                        "text": message.get("text", ""),
                        "previous_message": previous_message,
                        "sender": "clone",
                        "timestamp": message.get("timestamp", ""),
                        "model_version": message.get("model_version")
                    })
        
        # Add messages to RAG database
        rag.add_message_batch(message_data)
        print(f"Reinitialized RAG database with {len(message_data)} clean messages")
    except Exception as e:
        print(f"Error reinitializing RAG database: {e}")
        return
    
    print("\nRAG database cleanup completed successfully!")
    print("NOTE: The chat_history.json file was NOT modified. Please edit it manually to remove the bad messages.")

if __name__ == "__main__":
    remove_bad_responses()
