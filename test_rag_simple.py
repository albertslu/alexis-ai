#!/usr/bin/env python3

"""
Simple test script for the RAG system

This script tests the basic functionality of the RAG system without the hybrid response generation.
"""

import os
import json
from datetime import datetime

# Import our modules
from rag.rag_system import MessageRAG

# Sample messages for testing
SAMPLE_MESSAGES = [
    {
        "text": "I prefer coding in Python for most projects, but JavaScript has its place too.",
        "sender": "user",
        "timestamp": datetime.now().isoformat()
    },
    {
        "text": "I'm thinking about going hiking this weekend if the weather is good.",
        "sender": "user",
        "timestamp": datetime.now().isoformat()
    },
    {
        "text": "I've been working on this AI project for about three months now.",
        "sender": "user",
        "timestamp": datetime.now().isoformat()
    },
    {
        "text": "My favorite food is definitely Thai curry, especially with extra spice.",
        "sender": "user",
        "timestamp": datetime.now().isoformat()
    }
]

def main():
    print("\n===== Testing Basic RAG Functionality =====\n")
    
    # Initialize the RAG system
    rag_system = MessageRAG()
    
    # Add sample messages directly to the RAG system
    print("Adding sample messages to RAG system...")
    rag_system.add_message_batch(SAMPLE_MESSAGES)
    print(f"Added {len(SAMPLE_MESSAGES)} messages to RAG system")
    
    # Test retrieval with different queries
    test_queries = [
        "Tell me about your AI project",
        "What programming languages do you like?",
        "What are your weekend plans?",
        "What's your favorite food?"
    ]
    
    print("\n===== Testing Message Retrieval =====\n")
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = rag_system.retrieve_similar_messages(query, top_k=2)
        
        print(f"Found {len(results)} similar messages:")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result.get('text', '')}")
            if result.get('context'):
                print(f"     Context: {result.get('context', '')}")

if __name__ == "__main__":
    main()
