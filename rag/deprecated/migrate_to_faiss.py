"""
Migration script to transition from the original embedding RAG system to the FAISS-enhanced version.

This script will:
1. Load the existing embedding RAG system
2. Initialize the new FAISS RAG system
3. Migrate all data and embeddings
4. Verify the migration was successful

Usage:
    python migrate_to_faiss.py [user_id]
"""

import os
import sys
import logging
from embedding_rag import EmbeddingRAG
from faiss_rag import FaissRAGSystem

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_user_rag(data_dir, user_id="default"):
    """
    Migrate a user's RAG system from embedding-based to FAISS-based.
    
    Args:
        data_dir: Directory containing RAG data
        user_id: User ID to migrate
    """
    logger.info(f"Starting migration for user {user_id}")
    
    # Initialize the original embedding RAG system
    logger.info("Initializing original embedding RAG system")
    original_rag = EmbeddingRAG(data_dir, user_id=user_id)
    
    # Initialize the new FAISS RAG system
    logger.info("Initializing new FAISS RAG system")
    faiss_rag = FaissRAGSystem(data_dir, user_id=user_id)
    
    # Migrate data
    logger.info("Migrating data to FAISS RAG system")
    faiss_rag.migrate_from_embedding_rag(original_rag)
    
    # Verify migration
    message_count = len(faiss_rag.message_data)
    personal_info_count = len(faiss_rag.personal_info_data)
    
    logger.info(f"Migration complete!")
    logger.info(f"FAISS message index contains {faiss_rag.message_index.ntotal} vectors and {message_count} messages")
    logger.info(f"FAISS personal info index contains {faiss_rag.personal_info_index.ntotal} vectors and {personal_info_count} personal info items")
    
    return {
        "message_count": message_count,
        "personal_info_count": personal_info_count,
        "message_vectors": faiss_rag.message_index.ntotal,
        "personal_info_vectors": faiss_rag.personal_info_index.ntotal
    }

def main():
    # Get user ID from command line argument or use default
    user_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    
    # Set data directory
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    
    # Migrate user RAG system
    result = migrate_user_rag(data_dir, user_id)
    
    # Print summary
    print("\nMigration Summary:")
    print(f"User: {user_id}")
    print(f"Messages: {result['message_count']} (with {result['message_vectors']} vectors)")
    print(f"Personal Info Items: {result['personal_info_count']} (with {result['personal_info_vectors']} vectors)")

if __name__ == "__main__":
    main()
