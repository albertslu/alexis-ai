# RAG System for AI Clone
# This package provides Retrieval Augmented Generation functionality

from .rag_system import MessageRAG
from .enhanced_rag_integration import enhance_prompt_with_rag
from .rag_storage import add_interaction_to_rag

# Note: initialize_rag is deprecated, use initialize_enhanced_rag from enhanced_rag_integration instead
from .enhanced_rag_integration import initialize_enhanced_rag

__all__ = ['MessageRAG', 'enhance_prompt_with_rag', 'add_interaction_to_rag', 'initialize_enhanced_rag']
