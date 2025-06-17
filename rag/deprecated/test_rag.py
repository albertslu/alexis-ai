#!/usr/bin/env python3

"""
RAG System Test Tool

This script tests the RAG system by loading your chat history and allowing you
to query it interactively. It demonstrates how the RAG system retrieves relevant
examples from your message history.
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path to allow importing from rag module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.rag_system import MessageRAG

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')

def main():
    print("=== AI Clone RAG System Test ===\n")
    
    # Initialize RAG system
    rag = MessageRAG()
    
    # Load data from chat history
    print(f"Loading chat history from {CHAT_HISTORY_PATH}...")
    rag.add_from_chat_history(CHAT_HISTORY_PATH)
    
    # Interactive query loop
    print("\nEnter a message to see how the RAG system would retrieve similar examples.")
    print("Type 'exit' to quit.\n")
    
    while True:
        query = input("Your message: ")
        if query.lower() in ['exit', 'quit', 'q']:
            break
            
        # Retrieve similar messages
        similar_messages = rag.retrieve_similar_messages(query, top_k=3)
        
        if not similar_messages:
            print("\nNo similar messages found in your chat history.")
            continue
            
        print(f"\nFound {len(similar_messages)} similar messages:")
        for i, msg in enumerate(similar_messages):
            print(f"\nExample {i+1}:")
            print(f"Context: {msg['context']}")
            print(f"Your response: {msg['text']}")
        
        print("\n---")
    
    print("\nThank you for testing the RAG system!")

if __name__ == "__main__":
    main()
