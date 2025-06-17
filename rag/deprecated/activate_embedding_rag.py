"""
Activate Embedding RAG for AI Clone

This script integrates the Pinecone-based RAG system into the main application flow.
It creates a wrapper that maintains compatibility with the existing MessageRAG interface
while using the more advanced Pinecone vector database for persistent storage.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import RAG systems
from rag.pinecone_rag import PineconeRAGSystem
from rag.rag_system import MessageRAG

class EmbeddingRAGWrapper(MessageRAG):
    """
    Wrapper class that provides the MessageRAG interface but uses Pinecone for
    persistent vector storage that survives app reinstalls.
    
    This class maintains compatibility with the existing codebase while leveraging
    the industry-standard Pinecone vector database for reliable persistence.
    """
    
    def __init__(self, user_id="default", clear_existing=False):
        """
        Initialize the embedding RAG wrapper with Pinecone.
        
        Args:
            user_id: Identifier for the user
            clear_existing: If True, clear existing data
        """
        # Initialize the parent MessageRAG class first
        super().__init__(user_id=user_id, clear_existing=clear_existing)
        
        # Initialize the Pinecone RAG system
        try:
            self.pinecone_rag = PineconeRAGSystem(user_id=user_id)
            
            # If clear_existing flag is set, delete user data
            if clear_existing:
                self.pinecone_rag.delete_user_data()
                logger.info(f"Cleared existing Pinecone data for user {user_id}")
            
            logger.info(f"Initialized PineconeRAGSystem for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise RuntimeError(f"Pinecone initialization failed: {e}")
        
        # Sync data from MessageRAG to Pinecone
        self._sync_data_to_pinecone()
    
    def _sync_data_to_pinecone(self):
        """
        Sync existing data from MessageRAG to Pinecone.
        """
        try:
            # Add messages to Pinecone
            self.pinecone_rag.add_messages_to_index(self.messages)
            logger.info(f"Synced {len(self.messages)} messages to Pinecone")
            
            # Add personal info to Pinecone
            personal_info_items = []
            for category, items in self.personal_info.items():
                for item in items:
                    personal_info_items.append({
                        'category': category,
                        'text': item,
                        'type': 'personal_info'
                    })
            
            self.pinecone_rag.add_personal_info_to_index(personal_info_items)
            logger.info(f"Synced {len(personal_info_items)} personal info items to Pinecone")
        except Exception as e:
            logger.error(f"Error syncing data to Pinecone: {str(e)}")
            raise RuntimeError(f"Failed to sync data to Pinecone: {e}")
    
    def add_messages(self, messages):
        """
        Add messages to both MessageRAG and Pinecone.
        
        Args:
            messages: List of message dictionaries to add
        """
        # Add to parent MessageRAG
        super().add_messages(messages)
        
        # Add to Pinecone
        try:
            self.pinecone_rag.add_messages_to_index(messages)
            logger.info(f"Added {len(messages)} messages to Pinecone")
        except Exception as e:
            logger.error(f"Error adding messages to Pinecone: {str(e)}")
            raise RuntimeError(f"Failed to add messages to Pinecone: {e}")
    
    def extract_personal_info(self, text):
        """
        Extract personal information from user message.
        
        Args:
            text: User message text
            
        Returns:
            bool: True if successful
        """
        # Extract with MessageRAG first (maintains compatibility)
        super().extract_personal_info(text)
        
        # Now sync personal info to Pinecone
        personal_info_items = []
        for category, items in self.personal_info.items():
            for item in items:
                personal_info_items.append({
                    'category': category,
                    'text': item,
                    'type': 'personal_info'
                })
        
        try:
            # Add to Pinecone
            self.pinecone_rag.add_personal_info_to_index(personal_info_items)
            logger.info(f"Synced {len(personal_info_items)} personal info items to Pinecone")
            return True
        except Exception as e:
            logger.error(f"Error syncing personal info to Pinecone: {str(e)}")
            raise RuntimeError(f"Failed to sync personal info to Pinecone: {e}")
    
    def retrieve_similar_messages(self, query, conversation_history=None, channel=None, max_results=5):
        """
        Retrieve similar messages to the query.
        
        Args:
            query: Query text
            conversation_history: Optional conversation history
            channel: Optional channel to filter by
            max_results: Maximum number of results to return
            
        Returns:
            list: List of similar messages
        """
        try:
            # Use Pinecone for semantic similarity search
            # but adapt the return format to match MessageRAG's format
            
            # Get relevant messages from Pinecone
            relevant_messages = self.pinecone_rag.search(
                query=query,
                top_k=max_results
            )
            
            # Convert to format expected by the original MessageRAG interface
            similar_messages = []
            for message in relevant_messages:
                similar_messages.append({
                    'text': message.get('text', ''),
                    'similarity': message.get('score', 0),
                    'timestamp': message.get('timestamp', ''),
                    **{k: v for k, v in message.items() if k not in ['text', 'score', 'timestamp']}
                })
            
            return similar_messages
        except Exception as e:
            logger.error(f"Error retrieving similar messages from Pinecone: {str(e)}")
            # Fall back to parent MessageRAG's method
            return super().retrieve_similar_messages(query, conversation_history, channel, max_results)
    
    def get_context_for_query(self, query):
        """
        Get context for a query using Pinecone-based retrieval.
        
        Args:
            query: The user query
            
        Returns:
            str: Context from relevant messages and personal info
        """
        try:
            # Use Pinecone for better semantic matching
            result = self.pinecone_rag.retrieve_relevant_context(query, include_personal_info=True)
            
            # Format context
            context_parts = []
            
            # Add message context
            if result['messages']:
                context_parts.append("Relevant message history:")
                for item in result['messages']:
                    message_text = item['item'].get('text', '')
                    if message_text:
                        context_parts.append(f"- {message_text}")
            
            # Add personal info context
            if result['personal_info']:
                context_parts.append("\nRelevant personal information:")
                for item in result['personal_info']:
                    info_text = item['item'].get('text', '')
                    category = item['item'].get('category', '')
                    if info_text:
                        context_parts.append(f"- {category}: {info_text}")
            
            return "\n".join(context_parts)
        except Exception as e:
            logger.error(f"Error getting context with Pinecone: {str(e)}")
            # Fall back to keyword-based retrieval
            return super().get_context_for_query(query)

# Monkey patch function for the activate_embedding_rag function
def activate_embedding_rag():
    """
    Activate the Pinecone-based RAG system by monkey patching the MessageRAG class.
    
    This function replaces the MessageRAG class with the EmbeddingRAGWrapper class,
    which maintains the same interface but uses Pinecone for persistent vector storage.
    
    Returns:
        bool: True if activated successfully
    """
    try:
        # Save the original MessageRAG class
        original_message_rag = MessageRAG
        
        # Replace with the wrapper class
        MessageRAG.__new__ = lambda cls, *args, **kwargs: object.__new__(EmbeddingRAGWrapper)
        
        logger.info("Activated Pinecone RAG system")
        return True
    except Exception as e:
        logger.error(f"Error activating Pinecone RAG: {str(e)}")
        return False

# Activate if this script is run directly
if __name__ == "__main__":
    # Activate embedding RAG
    success = activate_embedding_rag()
    
    if success:
        print("Pinecone RAG system activated successfully!")
    else:
        print("Failed to activate Pinecone RAG system")
