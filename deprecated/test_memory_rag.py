#!/usr/bin/env python3

"""
Test script for the memory-enhanced RAG system.
"""

import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import the memory-enhanced RAG system
from rag.memory_enhanced_rag import MemoryEnhancedRAG, enhance_prompt_with_memory, update_memory_from_conversation

def test_memory_rag(test_mode=True):
    """
    Test the memory-enhanced RAG system.
    
    Args:
        test_mode: If True, don't save test interactions to the memory file
    """
    print("\n=== Testing Memory-Enhanced RAG System ===")
    
    # Initialize the memory-enhanced RAG system
    memory_rag = MemoryEnhancedRAG(user_id="albert")
    
    # Display core memories initialized from personal_info.json
    print("\nCore memories initialized from personal_info.json:")
    core_memories = memory_rag.memory["core_memory"]
    for i, memory in enumerate(core_memories[:5]):  # Show first 5 memories
        print(f"{i+1}. {memory['content']}")
    
    print(f"\nTotal core memories: {len(core_memories)}")
    
    # Test prompt enhancement with memory
    print("\nTesting prompt enhancement with memory:")
    query = "What do you do for work?"
    enhanced_prompt = enhance_prompt_with_memory(query, "You are an AI clone that mimics the user's communication style.")
    
    print(f"Enhanced prompt preview:")
    # Show a preview of the enhanced prompt
    preview_lines = enhanced_prompt.split('\n')[:15]
    print('\n'.join(preview_lines) + "\n...")
    
    # Test memory retrieval for different queries
    print("\nTesting memory retrieval for different queries:\n")
    test_queries = [
        "Tell me about your education",
        "What photography work do you do?",
        "Where do you live?",
        "What are your hobbies?"
    ]
    
    for query in test_queries:
        print(f"Query: {query}")
        relevant_memories = memory_rag.get_relevant_memories(query)
        
        if relevant_memories["core_memories"]:
            print("Relevant core memories:")
            for memory in relevant_memories["core_memories"][:3]:  # Show top 3
                print(f"- {memory}")
        
        if relevant_memories["episodic_memories"]:
            print("Relevant episodic memories:")
            for memory in relevant_memories["episodic_memories"][:2]:  # Show top 2
                print(f"- {memory}")
        
        print()
    
    # Test memory update from conversation (only if not in test mode)
    print("Testing memory update from conversation:\n")
    user_msg = "I'm thinking about learning to play guitar. Do you play any instruments?"
    ai_response = "I don't currently play any instruments, but I've been thinking about learning piano. Photography takes up most of my creative time right now."
    
    # In test mode, we'll simulate the update but not actually save it
    if not test_mode:
        # Actually update the memory
        update_memory_from_conversation(user_msg, ai_response)
        print("New episodic memory added:")
        print(f"User: {user_msg}")
        print(f"Me: {ai_response}")
        
        # Check if any new core memory was extracted
        print("\nAny new core memory extracted:")
        # This is a simplified check - in reality we'd need to compare before/after
        if any("instrument" in memory["content"].lower() for memory in memory_rag.memory["core_memory"]):
            print("New core memory about instruments was extracted.")
        else:
            print("No new core memory about instruments was extracted.")
        
        # Save the memory to disk
        memory_file = memory_rag.save_memory()
        print(f"\nMemory saved to: {memory_file}")
    else:
        print("Test mode: Memory update simulated but not saved")
        print(f"Would have added: User: {user_msg}")
        print(f"Would have added: Me: {ai_response}")
        print("\nNo changes were made to the memory file in test mode")

if __name__ == "__main__":
    # Run the test in test mode (don't save test interactions)
    test_memory_rag(test_mode=True)
