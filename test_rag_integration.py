#!/usr/bin/env python3

"""
Test script for the RAG integration with message uploads

This script demonstrates how to use the data integration module to upload
messages and then test the RAG system's ability to retrieve similar messages.
"""

import os
import json
from datetime import datetime

# Import our modules
from rag.data_integration import DataIntegration
from rag.rag_system import MessageRAG
from utils.hybrid_response import HybridResponseGenerator

# Sample conversation data for testing
SAMPLE_CONVERSATION = """
Friend: Hey, how's your day going?
Me: Pretty good! Just finished working on that AI project I told you about.
Friend: Oh cool, the one with the language model?
Me: Yeah, I'm trying to make it respond more like me. It's coming along well.
Friend: That sounds impressive. How accurate is it?
Me: I'd say it's about 75% there. Still needs some fine-tuning.
Friend: What's the hardest part about it?
Me: Getting it to understand context and maintain my conversational style consistently.
Friend: Makes sense. Are you using any specific techniques?
Me: Yeah, I'm implementing a hybrid approach with RAG and fine-tuning.
"""

# Sample messages for testing
SAMPLE_MESSAGES = """
I prefer coding in Python for most projects, but JavaScript has its place too.
I'm thinking about going hiking this weekend if the weather is good.
Remind me to pick up some groceries on the way home.
I've been working on this AI project for about three months now.
My favorite food is definitely Thai curry, especially with extra spice.
"""

def main():
    print("\n===== Testing RAG Integration with Message Uploads =====\n")
    
    # Initialize the data integration module
    data_integration = DataIntegration()
    
    # Initialize the RAG system
    rag_system = MessageRAG()
    
    # Initialize the hybrid response generator
    hybrid_generator = HybridResponseGenerator()
    
    # Process conversation data
    print("Processing conversation data...")
    conversation_count = data_integration.process_text_data(
        SAMPLE_CONVERSATION, 
        source_type="conversation"
    )
    print(f"Added {conversation_count} messages from conversation")
    
    # Process message data
    print("\nProcessing individual messages...")
    message_count = data_integration.process_text_data(
        SAMPLE_MESSAGES, 
        source_type="messages"
    )
    print(f"Added {message_count} individual messages")
    
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
    
    # Test hybrid response generation
    print("\n===== Testing Hybrid Response Generation =====\n")
    
    # Start a conversation
    conversation_id = hybrid_generator.start_conversation()
    
    # Generate responses for the test queries
    for query in test_queries:
        print(f"\nUser: {query}")
        response = hybrid_generator.generate_response(query, conversation_id)
        print(f"AI: {response}")

if __name__ == "__main__":
    main()
