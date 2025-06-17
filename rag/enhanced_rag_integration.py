#!/usr/bin/env python3

"""
iMessage RAG Integration

This module provides a simplified RAG (Retrieval Augmented Generation) integration
specifically optimized for iMessage suggestions.
"""

import os
import json
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import RAG system
from .pinecone_rag import PineconeRAGSystem

# Cache for RAG systems to avoid reloading
_rag_cache = {}

def get_conversation_context(conversation_history: List[Dict]) -> str:
    """
    Extract relevant context from conversation history.
    
    Args:
        conversation_history: Recent conversation history
        
    Returns:
        str: Formatted conversation context
    """
    if not conversation_history or len(conversation_history) < 2:
        return ""
        
    # Get the last few messages
    recent_messages = conversation_history[-3:]
    
    # Format as a conversation
    context = ""
    for msg in recent_messages:
        sender = "User" if msg.get('sender') == 'user' else "Assistant"
        text = msg.get('text', '')
        context += f"{sender}: {text}\n"
        
    return context

def initialize_enhanced_rag(user_id="default"):
    """
    Initialize the enhanced RAG system using Pinecone.
    
    Args:
        user_id: User identifier for the RAG system
    
    Returns:
        PineconeRAGSystem instance
    """
    # Check if we already have this RAG system in the cache
    global _rag_cache
    if user_id in _rag_cache:
        print(f"Using cached RAG system for user: {user_id}")
        return _rag_cache[user_id]
    
    # Initialize the Pinecone RAG system directly
    rag_system = PineconeRAGSystem(user_id=user_id)
    
    # Store in cache for future use
    _rag_cache[user_id] = rag_system
    
    print(f"Enhanced Pinecone RAG system initialized for user: {user_id} (verification running in background)")
    
    return rag_system

def filter_examples(examples: List[Dict]) -> List[Dict]:
    """
    Apply simple filtering to RAG examples to remove bad examples.
    
    Args:
        examples: List of RAG examples
        
    Returns:
        List[Dict]: Filtered examples
    """
    # Filter out examples explicitly marked as bad
    filtered_examples = [ex for ex in examples if not ex.get('is_bad_example', False)]
    
    # Sort by score if available
    if filtered_examples and 'score' in filtered_examples[0]:
        filtered_examples.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # Return top examples (limit to 5 for focus)
    return filtered_examples[:5]

def get_rag_context(message_text: str, conversation_history: Optional[List[Dict]] = None, user_id: str = "default") -> str:
    """
    Get RAG context for an iMessage, retrieving similar past messages.
    
    Args:
        message_text: The current message text
        conversation_history: Recent conversation history (optional)
        user_id: User identifier for the RAG system
        
    Returns:
        str: RAG context with similar messages
    """
    # Initialize RAG system
    rag_system = initialize_enhanced_rag(user_id)
    
    # Get relevant messages from the RAG system
    relevant_messages = rag_system.search(message_text, top_k=10)
    
    # Filter messages
    filtered_messages = filter_examples(relevant_messages)
    
    # Format the messages
    rag_context = ""
    if filtered_messages:
        rag_context = "Here are some relevant past messages that might help with your response:\n\n"
        for i, msg in enumerate(filtered_messages):
            rag_context += f"{i+1}. {msg['text']}\n\n"
    
    # Add conversation context if available
    if conversation_history:
        conv_context = get_conversation_context(conversation_history)
        if conv_context:
            rag_context += "\nRecent conversation:\n" + conv_context
    
    return rag_context

def enhance_prompt_with_rag(system_prompt: str, user_message: str, channel: str = 'text', user_id: str = "default", conversation_history: Optional[List[Dict]] = None) -> str:
    """
    Enhance the system prompt with relevant examples from the RAG system.
    
    Args:
        system_prompt: The original system prompt
        user_message: The current user message
        channel: The communication channel (always 'text' for iMessage)
        user_id: User identifier for the RAG system
        conversation_history: Optional conversation history
        
    Returns:
        str: Enhanced system prompt with RAG examples
    """
    # Get RAG context
    rag_context = get_rag_context(user_message, conversation_history, user_id)
    
    # Combine system prompt with RAG context
    final_prompt = f"{system_prompt}\n\n{rag_context}" if rag_context else system_prompt
    
    return final_prompt

# Example usage
if __name__ == "__main__":
    test_prompt = "You draft message suggestions that match the user's writing style."
    test_message = "Are you free this weekend?"
    
    enhanced = enhance_prompt_with_rag(test_prompt, test_message, user_id="test_user")
    print(enhanced)
