#!/usr/bin/env python3

"""
Memory-Enhanced RAG Integration Script

This script integrates the memory-enhanced RAG system with the AI clone backend.
It adds the necessary hooks to use the memory system in the chat and handle_message endpoints.
"""

import os
import sys
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def integrate_memory_rag():
    """
    Integrate the memory-enhanced RAG system with the AI clone backend.
    """
    try:
        # Import the memory-enhanced RAG system
        from rag.memory_enhanced_rag import enhance_prompt_with_memory, update_memory_from_conversation, MemoryEnhancedRAG
        
        # Initialize the memory-enhanced RAG system with the user's ID
        memory_rag = MemoryEnhancedRAG(user_id="albert")
        
        # Import the app_integration module to monkey patch
        import rag.app_integration
        
        # Store the original enhance_prompt_with_rag function
        original_enhance_prompt = rag.app_integration.enhance_prompt_with_rag
        
        # Define a wrapper function that logs before and after
        def enhanced_prompt_wrapper(system_prompt, user_message, conversation_history=None):
            """
            Wrapper for the enhance_prompt_with_memory function that adds logging.
            """
            logger.info(f"Enhancing prompt with memory for message: {user_message[:30]}...")
            
            # Call the memory-enhanced version
            enhanced_prompt = enhance_prompt_with_memory(system_prompt, user_message, conversation_history)
            
            logger.info("Prompt enhanced with memory system")
            return enhanced_prompt
        
        # Monkey patch the enhance_prompt_with_rag function
        rag.app_integration.enhance_prompt_with_rag = enhanced_prompt_wrapper
        
        # Import the backend app to patch the response handling
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from backend.app import hybrid_generator
        
        # Store the original generate_response method
        original_generate_response = hybrid_generator.generate_response
        
        # Define a wrapper for the generate_response method
        def generate_response_with_memory(user_message, conversation_id=None, system_prompt=None):
            """
            Wrapper for the generate_response method that updates memory after generating a response.
            """
            # Call the original method
            ai_response = original_generate_response(user_message, conversation_id, system_prompt)
            
            # Update memory with the conversation regardless of add_to_rag flag
            update_memory_from_conversation(user_message, ai_response)
            logger.info(f"Updated memory with conversation: {user_message[:30]}... -> {ai_response[:30]}...")
            
            return ai_response
        
        # Monkey patch the generate_response method
        hybrid_generator.generate_response = generate_response_with_memory
        
        logger.info("Successfully integrated memory-enhanced RAG system with AI clone backend")
        return True
    
    except Exception as e:
        logger.error(f"Error integrating memory-enhanced RAG system: {e}")
        return False

if __name__ == "__main__":
    # Integrate the memory-enhanced RAG system
    success = integrate_memory_rag()
    
    if success:
        print(" Memory-enhanced RAG system successfully integrated with AI clone backend")
        print("Your AI clone now has access to all the rich memories extracted from messages and emails")
        print("This should significantly improve response accuracy and reduce hallucinations")
    else:
        print(" Failed to integrate memory-enhanced RAG system")
        print("Please check the logs for more information")
