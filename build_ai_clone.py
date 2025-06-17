#!/usr/bin/env python3

"""
Build AI Clone

This script demonstrates how to use the UnifiedDataRepository to build an AI clone
by integrating data from various sources like iMessages and LinkedIn.
"""

import os
import json
from datetime import datetime, timedelta
import subprocess
from pathlib import Path

# Import our modules
from rag.unified_repository import UnifiedDataRepository
from rag.rag_system import MessageRAG
from utils.hybrid_response import HybridResponseGenerator

# Set up the repository
def setup_repository(user_id="me"):
    """
    Set up the unified data repository for the user.
    
    Args:
        user_id: Identifier for the user (default: "me")
        
    Returns:
        UnifiedDataRepository instance
    """
    print(f"Setting up repository for user: {user_id}")
    repository = UnifiedDataRepository(user_id=user_id)
    print(f"Repository initialized at: {repository.data_dir}")
    return repository

# Import iMessages
def import_imessages(repository, days=7):
    """
    Import iMessages from the last N days.
    
    This function assumes you have a script to extract iMessages.
    Replace the placeholder with your actual extraction logic.
    
    Args:
        repository: UnifiedDataRepository instance
        days: Number of days to look back (default: 7)
        
    Returns:
        Number of messages added
    """
    print(f"Importing iMessages from the last {days} days...")
    
    # TODO: Replace this with your actual iMessage extraction logic
    # For now, we'll use a placeholder that reads from a JSON file if it exists
    
    # Check if you have an iMessage export file
    imessage_file = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "imessage_export.json"
    
    if imessage_file.exists():
        with open(imessage_file, 'r') as f:
            imessage_data = json.load(f)
            messages = imessage_data.get("messages", [])
    else:
        # If no file exists, create some placeholder messages for testing
        print("No iMessage export file found. Using placeholder messages for testing.")
        messages = [
            {
                "text": "This is a placeholder message for testing.",
                "sender": "user",
                "timestamp": datetime.now().isoformat()
            }
        ]
    
    # Add messages to repository
    added_count = repository.add_messages(messages, source="imessage")
    print(f"Added {added_count} iMessages to repository")
    
    return added_count

# Import LinkedIn data
def import_linkedin(repository):
    """
    Import LinkedIn profile and activity data.
    
    This function assumes you have exported your LinkedIn data or have access to the API.
    Replace the placeholder with your actual LinkedIn data import logic.
    
    Args:
        repository: UnifiedDataRepository instance
        
    Returns:
        True if successful, False otherwise
    """
    print("Importing LinkedIn data...")
    
    # TODO: Replace this with your actual LinkedIn data import logic
    # For now, we'll use a placeholder that reads from a JSON file if it exists
    
    # Check if you have a LinkedIn export file
    linkedin_file = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "linkedin_export.json"
    
    if linkedin_file.exists():
        with open(linkedin_file, 'r') as f:
            linkedin_data = json.load(f)
    else:
        # If no file exists, create some placeholder data for testing
        print("No LinkedIn export file found. Using placeholder data for testing.")
        linkedin_data = {
            "profile": {
                "name": "Test User",
                "headline": "AI Enthusiast",
                "summary": "This is a placeholder LinkedIn profile for testing."
            },
            "posts": [
                {
                    "text": "Excited to be working on my AI clone project!",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
    
    # Add LinkedIn data to repository
    success = repository.add_linkedin_data(linkedin_data)
    if success:
        print("LinkedIn data added successfully")
    else:
        print("Failed to add LinkedIn data")
    
    return success

# Initialize the RAG system
def setup_rag_system(repository):
    """
    Set up the RAG system using the repository data.
    
    Args:
        repository: UnifiedDataRepository instance
        
    Returns:
        MessageRAG instance
    """
    print("Setting up RAG system...")
    rag_system = MessageRAG()
    
    # Add repository messages to RAG system
    messages = repository.get_all_messages()
    rag_system.add_message_batch(messages)
    
    print(f"RAG system initialized with {len(messages)} messages")
    return rag_system

# Set up the hybrid response generator
def setup_response_generator(rag_system):
    """
    Set up the hybrid response generator using the RAG system.
    
    Args:
        rag_system: MessageRAG instance
        
    Returns:
        HybridResponseGenerator instance
    """
    print("Setting up hybrid response generator...")
    response_generator = HybridResponseGenerator(rag_system=rag_system)
    print("Response generator initialized")
    return response_generator

# Test the AI clone
def test_ai_clone(response_generator):
    """
    Test the AI clone by sending some sample queries.
    
    Args:
        response_generator: HybridResponseGenerator instance
    """
    print("\n===== Testing AI Clone =====\n")
    
    test_queries = [
        "What programming languages do you like?",
        "Tell me about your AI project",
        "What's your professional background?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        response = response_generator.generate_response(query)
        print(f"AI Clone: {response}")

def main():
    print("\n===== Building AI Clone =====\n")
    
    # Step 1: Set up the repository
    repository = setup_repository(user_id="me")
    
    # Step 2: Import data from various sources
    import_imessages(repository)
    import_linkedin(repository)
    
    # Step 3: Set up the RAG system
    rag_system = setup_rag_system(repository)
    
    # Step 4: Set up the response generator
    response_generator = setup_response_generator(rag_system)
    
    # Step 5: Test the AI clone
    test_ai_clone(response_generator)
    
    print("\nAI Clone built successfully!")
    print("You can now integrate this with your preferred interface (web, Discord, etc.)")

if __name__ == "__main__":
    main()
