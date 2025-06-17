"""
RAG initialization module for AI Clone.

This module provides functions to initialize the appropriate RAG system
based on availability and configuration.
"""

import os
import logging
from typing import Tuple, Optional
import importlib.util
import sys

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for user-specific RAG systems
user_rag_cache = {}

def initialize_rag_system(user_id="default"):
    """
    Initialize the RAG system based on available implementations.
    
    Args:
        user_id: User ID for user-specific RAG
        
    Returns:
        RAG system instance
    """
    # Check if we already have a cached instance for this user
    if user_id in user_rag_cache:
        logger.info(f"Using cached RAG system for user {user_id}")
        return user_rag_cache[user_id]
        
    logger.info(f"Initializing embedding RAG system for user {user_id}")
    
    try:
        # Skip FAISS initialization for now until fully implemented
        # Just use the embedding RAG system directly
        from rag.activate_embedding_rag import EmbeddingRAGWrapper
        
        # Initialize embedding RAG wrapper
        embedding_rag = EmbeddingRAGWrapper(user_id=user_id)
        logger.info(f"Successfully initialized embedding RAG for user {user_id}")
        
        # Cache the instance for future use
        user_rag_cache[user_id] = embedding_rag
        
        return embedding_rag
    except Exception as e:
        logger.error(f"Error initializing embedding RAG: {str(e)}")
        
        # Fall back to original MessageRAG as last resort
        from rag.rag_system import MessageRAG
        logger.warning(f"Falling back to original MessageRAG for user {user_id}")
        
        # Cache the fallback instance
        fallback_rag = MessageRAG(user_id=user_id)
        user_rag_cache[user_id] = fallback_rag
        
        return fallback_rag

def initialize_enhanced_rag(data_dir: str = None, user_id: str = "default") -> Tuple[object, object]:
    """
    Initialize the enhanced RAG system with personal information enhancement.
    
    This function will try to use the FAISS-enhanced RAG system if available,
    falling back to the original embedding RAG system if necessary.
    
    Args:
        data_dir: Directory to store RAG data
        user_id: User ID for multi-user support
        
    Returns:
        Tuple of (RAG system, personal info enhancer)
    """
    # Set default data directory if not provided
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    
    # Initialize RAG system
    rag_system = initialize_rag_system(user_id=user_id)
    
    # For now, we'll use the same system for personal info enhancement
    personal_info_enhancer = rag_system
    
    return rag_system, personal_info_enhancer
