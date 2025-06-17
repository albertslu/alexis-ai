#!/usr/bin/env python3

"""
RAG Storage Integration

This module provides functions to store interactions in the RAG system.
It's a focused extraction from the original app_integration.py, keeping
only the essential functionality for adding new message examples to the RAG system.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Any

def add_interaction_to_rag(user_message: str, ai_response: str, 
                          conversation_history: Optional[List[Dict[str, Any]]] = None, 
                          model_version: Optional[str] = None, 
                          user_id: str = "default"):
    """
    Add a new interaction to the RAG system.
    
    Args:
        user_message: The user's message
        ai_response: The AI's response
        conversation_history: Recent conversation history
        model_version: Version of the model that generated the response
        user_id: User ID for the RAG system (default: "default")
    """
    # Import here to avoid circular imports
    from .pinecone_rag import PineconeRAGSystem
    
    # Get or initialize the RAG system for this user
    rag_system = PineconeRAGSystem(user_id=user_id)
    
    # Skip if either message is empty
    if not user_message or not ai_response:
        return
    
    # Get the channel from conversation history
    channel = None
    if conversation_history and len(conversation_history) > 0:
        channel = conversation_history[-1].get('channel', 'text')
    
    # Create message entry
    message_entry = {
        'text': ai_response,
        'previous_message': user_message,
        'sender': 'clone',
        'timestamp': datetime.now().isoformat(),
        'model_version': model_version,
        'user_id': user_id,
        'metadata': {
            'channel': channel
        }
    }
    
    # Add to Pinecone RAG system
    rag_system.add_messages_to_index([message_entry])
    
    print(f"Added interaction to Pinecone RAG: {user_message[:30]}... -> {ai_response[:30]}...")
