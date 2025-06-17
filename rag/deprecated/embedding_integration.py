#!/usr/bin/env python3

"""
Integration module for embedding-based RAG with the hybrid response generator.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Import embedding RAG
from rag.embedding_rag import EmbeddingRAG

# Import existing RAG components
from utils.hybrid_response import HybridResponseGenerator

# Load environment variables
load_dotenv()

class EmbeddingRAGIntegration:
    """
    Integration class for embedding-based RAG with the hybrid response generator.
    """
    
    def __init__(self, data_dir=None):
        """
        Initialize the embedding RAG integration.
        
        Args:
            data_dir: Directory for storing data files
        """
        # Set data directory
        if data_dir is None:
            self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        else:
            self.data_dir = data_dir
            
        # Initialize embedding RAG
        self.embedding_rag = EmbeddingRAG(data_dir=self.data_dir)
        
        # Load chat history
        self.chat_history_file = os.path.join(self.data_dir, 'chat_history.json')
        self.chat_history = self._load_chat_history()
        
        # Initialize embeddings with existing data
        self._initialize_embeddings()
    
    def _load_chat_history(self):
        """
        Load chat history from file.
        
        Returns:
            dict: Chat history
        """
        if os.path.exists(self.chat_history_file):
            try:
                with open(self.chat_history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading chat history: {str(e)}")
        
        return {"conversations": []}
    
    def _initialize_embeddings(self):
        """
        Initialize embeddings with existing data.
        """
        # Extract messages from chat history
        messages = []
        for conversation in self.chat_history.get('conversations', []):
            messages.extend(conversation.get('messages', []))
        
        # Add messages to embedding index
        self.embedding_rag.add_messages_to_index(messages)
    
    def update_with_new_messages(self, messages):
        """
        Update embeddings with new messages.
        
        Args:
            messages: List of new message dictionaries
        """
        self.embedding_rag.add_messages_to_index(messages)
    
    def enhance_hybrid_response(self, hybrid_generator, user_message, conversation_id=None, channel=None, metadata=None):
        """
        Enhance hybrid response with embedding-based RAG.
        
        Args:
            hybrid_generator: HybridResponseGenerator instance
            user_message: User message
            conversation_id: Optional conversation ID
            channel: Optional communication channel
            metadata: Optional metadata
            
        Returns:
            str: Enhanced response
        """
        # Get base system prompt from hybrid generator
        base_system_message = hybrid_generator._prepare_system_message({}, channel)
        
        # Enhance with message history using embeddings
        enhanced_prompt = self.embedding_rag.enhance_prompt_with_message_history(user_message, base_system_message)
        
        # Generate response using enhanced prompt
        response = hybrid_generator.generate_response(
            user_message,
            conversation_id=conversation_id,
            enhanced_prompt=enhanced_prompt,
            channel=channel,
            metadata=metadata
        )
        
        return response


def initialize_embedding_rag():
    """
    Initialize embedding RAG integration.
    
    Returns:
        EmbeddingRAGIntegration: Initialized integration
    """
    return EmbeddingRAGIntegration()


def generate_response_with_embedding_rag(user_message, conversation_id=None, channel=None, metadata=None):
    """
    Generate response using embedding-based RAG.
    
    Args:
        user_message: User message
        conversation_id: Optional conversation ID
        channel: Optional communication channel
        metadata: Optional metadata
        
    Returns:
        str: Generated response
    """
    # Initialize embedding RAG
    embedding_integration = initialize_embedding_rag()
    
    # Initialize hybrid generator
    hybrid_generator = HybridResponseGenerator()
    
    # Generate enhanced response
    response = embedding_integration.enhance_hybrid_response(
        hybrid_generator,
        user_message,
        conversation_id=conversation_id,
        channel=channel,
        metadata=metadata
    )
    
    # Update embeddings with new message
    embedding_integration.update_with_new_messages([
        {
            "id": conversation_id or "temp_id",
            "sender": "user",
            "text": user_message,
            "timestamp": datetime.now().isoformat(),
            "channel": channel or "default"
        },
        {
            "id": conversation_id or "temp_id_response",
            "sender": "clone",
            "text": response,
            "timestamp": datetime.now().isoformat(),
            "channel": channel or "default"
        }
    ])
    
    return response
