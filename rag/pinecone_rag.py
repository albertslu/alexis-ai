"""
Pinecone-based RAG System for AI Clone

This module implements semantic retrieval using OpenAI embeddings with Pinecone for
efficient and persistent vector storage. It provides industry-standard vector search
that persists across app reinstalls and rebuilds.
"""

import os
import logging
import time
import json
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import pinecone
from openai import OpenAI
from dotenv import load_dotenv
import threading
import hashlib

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI()

def verify_pinecone_setup(max_retries=2, retry_delay=2, wait_time=3):
    """
    Verify that Pinecone is properly set up and working.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        wait_time: Wait time for indexing in seconds
        
    Returns:
        bool: True if verification passed, raises an exception otherwise
    """
    api_key = os.getenv("PINECONE_API_KEY")
    environment = os.getenv("PINECONE_ENVIRONMENT")
    
    if not api_key or not environment:
        error_msg = "PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Get the correct embedding dimension
    try:
        test_embedding = client.embeddings.create(
            input="test", 
            model="text-embedding-3-large"
        )
        embedding_dim = len(test_embedding.data[0].embedding)
        logger.info(f"OpenAI embedding dimension: {embedding_dim}")
    except Exception as e:
        logger.error(f"Error getting OpenAI embedding: {e}")
        raise RuntimeError(f"OpenAI API error: {e}")
    
    # Initialize Pinecone
    pc = pinecone.Pinecone(api_key=api_key)
    
    # Check if index exists
    index_name = "ai-clone-rag"
    indexes = pc.list_indexes()
    index_names = [idx.name for idx in indexes]
    
    if index_name not in index_names:
        logger.info(f"Creating Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=embedding_dim,
            metric="cosine",
            spec=pinecone.ServerlessSpec(cloud="aws", region=environment)
        )
        logger.info(f"Created Pinecone index with dimension {embedding_dim}")
    
    # Test basic operations
    logger.info("Testing basic Pinecone operations...")
    
    # Connect to the index
    index = pc.Index(index_name)
    
    # Test vector - random but with the correct dimension
    test_id = "verify_test_vector"
    test_vector = [0.1] * embedding_dim
    
    # Upsert the test vector
    try:
        # Try to upsert with retries
        for attempt in range(max_retries):
            try:
                logger.info(f"Upserting test vector (attempt {attempt+1}/{max_retries})")
                index.upsert(
                    vectors=[{
                        'id': test_id,
                        'values': test_vector,
                        'metadata': {'text': 'Verification test'}
                    }],
                    namespace=""
                )
                logger.info("Test vector upserted successfully")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Upsert attempt {attempt+1} failed: {e}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise
        
        # Wait for indexing to complete
        logger.info(f"Waiting {wait_time} seconds for indexing to complete...")
        time.sleep(wait_time)
        
        # Query the test vector with retries
        for attempt in range(max_retries):
            try:
                logger.info(f"Querying test vector (attempt {attempt+1}/{max_retries})")
                results = index.query(
                    vector=test_vector,
                    namespace="",
                    top_k=1
                )
                
                # Verify we got a result
                if results.matches and results.matches[0].id == test_id:
                    logger.info("✓ Pinecone verification passed")
                    
                    # Clean up
                    try:
                        index.delete(ids=[test_id], namespace="")
                        logger.info("Test vector deleted successfully")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to delete test vector: {cleanup_error}")
                    
                    return True
                else:
                    if attempt < max_retries - 1:
                        logger.warning(f"Query attempt {attempt+1} returned no matches, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                    else:
                        error_msg = "Pinecone verification failed - couldn't query test vector"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Query attempt {attempt+1} failed: {e}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise
    except Exception as e:
        logger.error(f"Pinecone verification failed: {e}")
        raise RuntimeError(f"Pinecone verification failed: {e}")

class PineconeRAGSystem:
    """
    RAG system using Pinecone for efficient and persistent vector storage.
    """
    
    def __init__(self, user_id="default"):
        """
        Initialize the Pinecone RAG system.
        
        Args:
            user_id: User ID for multi-user support
        """
        self.user_id = user_id
        self.embedding_dim = 3072  # Correct dimension for text-embedding-3-large confirmed by testing
        self.verification_complete = False
        self.verification_success = False
        
        # Initialize Pinecone
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            environment = os.getenv("PINECONE_ENVIRONMENT")
            
            if not api_key or not environment:
                raise ValueError("PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set")
            
            # Initialize Pinecone
            self.pc = pinecone.Pinecone(api_key=api_key)
            
            # Check if index exists
            index_name = "ai-clone-rag"
            indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in indexes]
            
            if index_name not in index_names:
                logger.warning(f"Index {index_name} not found. Will be created during verification.")
            
            # Connect to the index
            self.index = self.pc.Index(index_name)
            self.index_name = index_name
            
            # Start verification in a background thread with reduced timeouts
            threading.Thread(target=self._verify_pinecone_async, daemon=True).start()
            
            logger.info(f"Connected to Pinecone index: {index_name} for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone: {e}")
            raise RuntimeError(f"Failed to initialize Pinecone: {e}")
    
    def is_verified(self):
        """Check if verification is complete and successful."""
        return self.verification_complete and self.verification_success
    
    def wait_for_verification(self, timeout=5):
        """
        Wait for verification to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if verification succeeded, False otherwise
        """
        start_time = time.time()
        while not self.verification_complete and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        return self.verification_success
    
    def _verify_pinecone_async(self):
        """Run Pinecone verification asynchronously in the background with reduced timeouts."""
        try:
            # Verify Pinecone setup with reduced timeouts and retries
            verify_pinecone_setup(max_retries=2, retry_delay=1, wait_time=2)
            self.verification_success = True
            logger.info("Pinecone verification completed successfully")
        except Exception as e:
            logger.error(f"Pinecone verification failed: {e}")
            self.verification_success = False
        finally:
            self.verification_complete = True
            logger.info(f"Pinecone verification complete, success={self.verification_success}")
    
    def _get_embedding(self, text):
        """
        Get embedding for text using OpenAI's embedding model.
        
        Args:
            text: Text to get embedding for
            
        Returns:
            list: Embedding vector
        """
        try:
            # Use text-embedding-3-large for higher quality embeddings
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            
            # For debugging, log the dimensions of the embedding
            embedding = response.data[0].embedding
            logger.info(f"Generated embedding with dimension: {len(embedding)}")
            
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None
    
    def add_messages_to_index(self, messages):
        """
        Add messages to the Pinecone index.
        
        Args:
            messages: List of message objects
            
        Returns:
            int: Number of messages added
        """
        if not messages:
            return 0
        
        # Process in batches of 100
        batch_size = 100
        total_added = 0
        
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i+batch_size]
            vectors = []
            
            for msg in batch:
                # Generate a stable ID based on content hash
                content = msg.get('text', '')
                if not content:
                    continue
                
                msg_hash = hashlib.md5(content.encode()).hexdigest()
                msg_id = f"msg_{self.user_id}_{msg_hash}"
                
                # Get embedding for the text
                embedding = self._get_embedding(content)
                
                # Create vector with metadata
                vector = {
                    'id': msg_id,
                    'values': embedding,
                    'metadata': {
                        'text': content,
                        'source': msg.get('source', 'unknown'),
                        'channel': msg.get('channel') or msg.get('metadata', {}).get('channel', 'text'),
                        'timestamp': msg.get('timestamp', datetime.now().isoformat()),
                        'user_id': self.user_id
                    }
                }
                vectors.append(vector)
            
            if vectors:
                # Check if verification is complete before proceeding
                if not self.is_verified():
                    logger.warning("Pinecone verification not complete, waiting before adding messages...")
                    self.wait_for_verification()
                
                # Only proceed if verification was successful
                if self.verification_success:
                    try:
                        self.index.upsert(vectors=vectors, namespace="")
                        total_added += len(vectors)
                        logger.info(f"Added {len(vectors)} messages to Pinecone")
                    except Exception as e:
                        logger.error(f"Error adding messages to Pinecone: {e}")
                        raise
                else:
                    logger.error("Pinecone verification failed, cannot add messages")
                    raise RuntimeError("Pinecone verification failed, cannot add messages")
        
        return total_added
    
    def add_personal_info_to_index(self, personal_info_items):
        """
        Add personal information to the Pinecone index.
        
        Args:
            personal_info_items: List of personal information items
            
        Returns:
            int: Number of items added
        """
        if not personal_info_items:
            return 0
        
        # Process in batches of 100
        batch_size = 100
        total_added = 0
        
        for i in range(0, len(personal_info_items), batch_size):
            batch = personal_info_items[i:i+batch_size]
            vectors = []
            
            for item in batch:
                # Generate a stable ID based on content hash
                content = item.get('text', '')
                if not content:
                    continue
                
                item_hash = hashlib.md5(content.encode()).hexdigest()
                item_id = f"pi_{self.user_id}_{item_hash}"
                
                # Get embedding for the text
                embedding = self._get_embedding(content)
                
                # Create vector with metadata
                vector = {
                    'id': item_id,
                    'values': embedding,
                    'metadata': {
                        'text': content,
                        'source': item.get('source', 'unknown'),
                        'category': item.get('category', 'personal_info'),
                        'timestamp': item.get('timestamp', datetime.now().isoformat()),
                        'user_id': self.user_id
                    }
                }
                vectors.append(vector)
            
            if vectors:
                # Check if verification is complete before proceeding
                if not self.is_verified():
                    logger.warning("Pinecone verification not complete, waiting before adding personal info...")
                    self.wait_for_verification()
                
                # Only proceed if verification was successful
                if self.verification_success:
                    try:
                        self.index.upsert(vectors=vectors, namespace="")
                        total_added += len(vectors)
                        logger.info(f"Added {len(vectors)} personal info items to Pinecone")
                    except Exception as e:
                        logger.error(f"Error adding personal info to Pinecone: {e}")
                        raise
                else:
                    logger.error("Pinecone verification failed, cannot add personal info")
                    raise RuntimeError("Pinecone verification failed, cannot add personal info")
        
        return total_added
    
    def search(self, query, top_k=5):
        """
        Search for similar content in the Pinecone index.
        
        Args:
            query: Query text
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        # Check if verification is complete before proceeding
        if not self.is_verified():
            logger.warning("Pinecone verification not complete, waiting before searching...")
            self.wait_for_verification()
        
        # Only proceed if verification was successful
        if self.verification_success:
            # Get embedding for the query
            query_embedding = self._get_embedding(query)
            
            # Search Pinecone with user_id filter
            try:
                # Filter by user_id to ensure privacy and correct context
                filter_dict = {"user_id": {"$eq": self.user_id}}
                
                results = self.index.query(
                    vector=query_embedding,
                    top_k=top_k,
                    include_metadata=True,
                    namespace="",
                    filter=filter_dict
                )
                
                # Format results
                formatted_results = []
                for match in results.matches:
                    formatted_results.append({
                        'score': match.score,
                        'text': match.metadata.get('text', ''),
                        'source': match.metadata.get('source', 'unknown'),
                        'timestamp': match.metadata.get('timestamp', ''),
                        'id': match.id
                    })
                
                return formatted_results
            except Exception as e:
                logger.error(f"Error searching Pinecone: {e}")
                raise
        else:
            logger.error("Pinecone verification failed, cannot search")
            raise RuntimeError("Pinecone verification failed, cannot search")
    
    def delete_user_data(self):
        """
        Delete all data for this user from Pinecone.
        This is useful for testing or user account deletion.
        """
        try:
            # Delete all vectors in the user's namespace with updated API
            self.index.delete(
                filter={"user_id": self.user_id},
                namespace=""  # Use empty namespace for reliability
            )
            logger.info(f"Deleted all vectors for user {self.user_id} from Pinecone")
            return True
        except Exception as e:
            logger.error(f"Error deleting user data from Pinecone: {e}")
            return False
