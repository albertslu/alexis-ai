"""
Test script for the embedding RAG system.

This script tests the embedding RAG system by:
1. Initializing the embedding RAG wrapper
2. Adding some test messages
3. Retrieving similar messages for a test query
4. Comparing the results with the keyword-based RAG system
"""

import os
import sys
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import RAG systems
from rag.rag_system import MessageRAG
from rag.activate_embedding_rag import EmbeddingRAGWrapper

def test_embedding_rag():
    """
    Test the embedding RAG system.
    """
    print("Testing Embedding RAG System")
    print("-" * 50)
    
    # Initialize both RAG systems
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    
    # Create test directories and clean them if they exist
    test_keyword_dir = os.path.join(data_dir, "test_keyword")
    test_embedding_dir = os.path.join(data_dir, "test_embedding")
    
    # Clean test directories if they exist
    import shutil
    for dir_path in [test_keyword_dir, test_embedding_dir]:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"Cleaned test directory: {dir_path}")
            except Exception as e:
                print(f"Error cleaning directory {dir_path}: {e}")
    
    # Original keyword-based RAG
    keyword_rag = MessageRAG(user_id="test_keyword")
    
    # Embedding-based RAG
    embedding_rag = EmbeddingRAGWrapper(user_id="test_embedding")
    
    # Add some test messages to both systems
    test_messages = [
        {
            "id": "test1",
            "sender": "user",
            "text": "What's the weather like in San Francisco today?",
            "timestamp": datetime.now().isoformat(),
            "channel": "test"
        },
        {
            "id": "test2",
            "sender": "clone",
            "text": "The weather in San Francisco is currently sunny with a high of 72°F.",
            "timestamp": datetime.now().isoformat(),
            "channel": "test"
        },
        {
            "id": "test3",
            "sender": "user",
            "text": "Can you recommend a good restaurant in the city?",
            "timestamp": datetime.now().isoformat(),
            "channel": "test"
        },
        {
            "id": "test4",
            "sender": "clone",
            "text": "I'd recommend Acquerello for Italian cuisine, or Kokkari Estiatorio for Greek food. Both are excellent options in San Francisco.",
            "timestamp": datetime.now().isoformat(),
            "channel": "test"
        },
        {
            "id": "test5",
            "sender": "user",
            "text": "What's your favorite programming language?",
            "timestamp": datetime.now().isoformat(),
            "channel": "test"
        },
        {
            "id": "test6",
            "sender": "clone",
            "text": "I enjoy working with Python because of its readability and versatility. It's great for everything from web development to data science.",
            "timestamp": datetime.now().isoformat(),
            "channel": "test"
        }
    ]
    
    print("Adding test messages to both RAG systems...")
    keyword_rag.add_message_batch(test_messages)
    embedding_rag.add_message_batch(test_messages)
    
    # Test queries
    test_queries = [
        "What's the forecast for San Francisco?",
        "Where should I eat dinner tonight?",
        "Do you like coding in Python?"
    ]
    
    # Test retrieval
    print("\nTesting retrieval with both systems...")
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        
        # Get results from keyword RAG
        print("\nKeyword RAG Results:")
        keyword_results = keyword_rag.retrieve_similar_messages(query, top_k=2)
        for i, result in enumerate(keyword_results):
            print(f"{i+1}. {result.get('text', '')[:100]}... (Score: {result.get('similarity', 0):.4f})")
        
        # Get results from embedding RAG
        print("\nEmbedding RAG Results:")
        embedding_results = embedding_rag.retrieve_similar_messages(query, top_k=2)
        for i, result in enumerate(embedding_results):
            print(f"{i+1}. {result.get('text', '')[:100]}... (Score: {result.get('similarity', 0):.4f})")
    
    print("\nTest complete!")

if __name__ == "__main__":
    test_embedding_rag()
