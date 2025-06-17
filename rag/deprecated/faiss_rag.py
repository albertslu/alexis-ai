"""
DEPRECATED: This FAISS-based RAG implementation has been replaced by PineconeRAGSystem.

This file is kept for reference only and should be removed in a future update.
All new code should use PineconeRAGSystem from pinecone_rag.py for vector storage.
"""

"""
FAISS-enhanced RAG System for AI Clone

This module implements semantic retrieval using OpenAI embeddings with FAISS for
efficient vector search. It significantly improves search performance while
maintaining the high-quality semantic matching of the original system.
"""

import os
import pickle
import logging
import numpy as np
import faiss
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
from datetime import datetime

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI()

class FaissRAGSystem:
    """
    RAG system using FAISS for efficient vector search with OpenAI embeddings.
    """
    
    def __init__(self, data_dir, user_id="default"):
        """
        Initialize the FAISS RAG system.
        
        Args:
            data_dir: Directory to store data
            user_id: User ID for multi-user support
        """
        self.data_dir = data_dir
        self.user_id = user_id
        
        # Create user-specific directory if it doesn't exist
        self.user_data_dir = os.path.join(data_dir, f"rag_data_{user_id}")
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        # File paths for storing data
        self.faiss_index_file = os.path.join(self.user_data_dir, 'faiss_message_index.bin')
        self.message_data_file = os.path.join(self.user_data_dir, 'message_data.pkl')
        self.personal_info_index_file = os.path.join(self.user_data_dir, 'faiss_personal_info_index.bin')
        self.personal_info_data_file = os.path.join(self.user_data_dir, 'personal_info_data.pkl')
        
        # Set up MongoDB connection (for metadata)
        try:
            from utils.auth import db
            self.db = db
            self.mongodb_available = True
            logger.info(f"MongoDB connection established for user {user_id}")
        except ImportError:
            self.mongodb_available = False
            logger.warning("MongoDB not available, using local files only")
        
        # Initialize or load FAISS indices and data
        self.message_index, self.message_data = self._initialize_faiss_index(
            self.faiss_index_file, self.message_data_file
        )
        
        self.personal_info_index, self.personal_info_data = self._initialize_faiss_index(
            self.personal_info_index_file, self.personal_info_data_file
        )
        
        # Embedding dimension for text-embedding-3-large
        self.embedding_dim = 3072
        
        logger.info(f"Initialized FAISS RAG system for user {user_id}")
        
    def _initialize_faiss_index(self, index_file, data_file):
        """
        Initialize or load FAISS index and data.
        
        Args:
            index_file: Path to FAISS index file
            data_file: Path to data file
            
        Returns:
            tuple: (FAISS index, data dictionary)
        """
        # Initialize empty data structure
        data = {'items': []}
        
        # Try to load existing data
        if os.path.exists(data_file):
            try:
                with open(data_file, 'rb') as f:
                    data = pickle.load(f)
                logger.info(f"Loaded {len(data['items'])} items from {data_file}")
            except Exception as e:
                logger.error(f"Error loading data from {data_file}: {str(e)}")
                data = {'items': []}
        
        # Create or load FAISS index
        if os.path.exists(index_file):
            try:
                index = faiss.read_index(index_file)
                logger.info(f"Loaded FAISS index from {index_file} with {index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Error loading FAISS index from {index_file}: {str(e)}")
                index = faiss.IndexFlatIP(self.embedding_dim)
        else:
            index = faiss.IndexFlatIP(self.embedding_dim)
            logger.info("Created new FAISS index")
            
        # If data is empty or index has no vectors, try to recover from MongoDB
        if (len(data['items']) == 0 or index.ntotal == 0) and hasattr(self, 'mongodb_available') and self.mongodb_available:
            try:
                index, data = self._recover_from_mongodb(index, data, index_file, data_file)
            except Exception as e:
                logger.error(f"Failed to recover from MongoDB: {e}")
        
        return index, data
    
    def _recover_from_mongodb(self, index, data, index_file, data_file):
        """
        Recover FAISS index and data from MongoDB after app reinstall.
        
        This is a critical function that ensures persistence across app reinstalls
        by rebuilding the FAISS index from metadata stored in MongoDB.
        
        Args:
            index: Empty FAISS index to populate
            data: Empty data dictionary to populate
            index_file: Path to save recovered index
            data_file: Path to save recovered data
            
        Returns:
            tuple: (Recovered FAISS index, recovered data)
        """
        logger.info(f"Attempting to recover index from MongoDB for user {self.user_id}")
        
        # Query MongoDB for all metadata for this user
        cursor = self.db.rag_metadata.find({'user_id': self.user_id})
        
        # Group items by their index file
        items_by_index = {}
        for item in cursor:
            index_name = item.get('index_file', '')
            if index_name not in items_by_index:
                items_by_index[index_name] = []
            items_by_index[index_name].append(item)
        
        # Process items for the target index
        target_index_name = os.path.basename(index_file)
        if target_index_name in items_by_index:
            items = items_by_index[target_index_name]
            logger.info(f"Found {len(items)} items in MongoDB for index {target_index_name}")
            
            # Get embeddings for all items
            texts = [item.get('text', '') for item in items]
            metadata_list = [item.get('metadata', {}) for item in items]
            
            # Process in batches to avoid memory issues
            batch_size = 50
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_metadata = metadata_list[i:i+batch_size]
                
                # Add batch to index
                index, data = self._add_to_index(batch_texts, batch_metadata, index, data)
                logger.info(f"Recovered batch {i//batch_size + 1}/{(len(texts)+batch_size-1)//batch_size}")
            
            # Save recovered index and data
            self._save_faiss_index(index, index_file)
            self._save_data(data, data_file)
            
            logger.info(f"Successfully recovered {len(data['items'])} items from MongoDB")
            return index, data
        else:
            logger.warning(f"No items found in MongoDB for index {target_index_name}")
            return index, data
    
    def _save_faiss_index(self, index, index_file):
        """
        Save FAISS index to file.
        
        Args:
            index: FAISS index to save
            index_file: Path to save index to
        """
        try:
            faiss.write_index(index, index_file)
            logger.info(f"Saved FAISS index to {index_file}")
        except Exception as e:
            logger.error(f"Error saving FAISS index to {index_file}: {str(e)}")
    
    def _save_data(self, data, data_file):
        """
        Save data to file.
        
        Args:
            data: Data to save
            data_file: Path to save data to
        """
        try:
            with open(data_file, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"Saved {len(data['items'])} items to {data_file}")
        except Exception as e:
            logger.error(f"Error saving data to {data_file}: {str(e)}")
    
    def _get_embedding(self, text):
        """
        Get embedding for text using OpenAI's embeddings API.
        
        Args:
            text: Text to get embedding for
            
        Returns:
            np.array: Embedding vector
        """
        try:
            # Use text-embedding-3-large for higher quality embeddings
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            # Convert to numpy array for FAISS
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            # Normalize for cosine similarity
            faiss.normalize_L2(embedding.reshape(1, -1))
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None
    
    def _add_to_index(self, texts, metadata_list, index, data):
        """
        Add items to FAISS index with metadata.
        
        Args:
            texts: List of texts to add
            metadata_list: List of metadata dictionaries
            index: FAISS index to add to
            data: Data dictionary to update
            
        Returns:
            Tuple of (updated index, updated data)
        """
        if not texts:
            return index, data
            
        embeddings = []
        for text in texts:
            embedding = self._get_embedding(text)
            if embedding is not None:
                embeddings.append(embedding)
            else:
                # Skip items where embedding generation failed
                logger.warning(f"Skipping item due to embedding generation failure: {text[:50]}...")
                
        if not embeddings:
            return index, data
            
        # Convert to numpy array
        embeddings_array = np.array(embeddings).astype('float32')
        
        # Generate IDs for new items
        start_id = len(data['items'])
        ids = np.array(range(start_id, start_id + len(embeddings)))
        
        # Add to index
        index.add_with_ids(embeddings_array, ids)
        
        # Add items and metadata to data dictionary
        for i, (text, metadata) in enumerate(zip(texts, metadata_list)):
            item_id = start_id + i
            data['items'].append({
                'id': item_id,
                'text': text,
                'metadata': metadata
            })
        
        # Save index and data
        self._save_faiss_index(index, self.faiss_index_file)
        self._save_data(data, self.message_data_file)
        
        # Store metadata in MongoDB if available
        if hasattr(self, 'mongodb_available') and self.mongodb_available:
            try:
                # Store only the metadata in MongoDB (not the embeddings)
                # This is more efficient and keeps the vector search in FAISS
                for i, (text, metadata) in enumerate(zip(texts, metadata_list)):
                    item_id = start_id + i
                    mongo_item = {
                        'user_id': self.user_id,
                        'item_id': item_id,
                        'text': text,
                        'metadata': metadata,
                        'index_file': os.path.basename(self.faiss_index_file),
                        'updated_at': datetime.now().isoformat()
                    }
                    # Upsert the metadata document
                    self.db.rag_metadata.update_one(
                        {'user_id': self.user_id, 'item_id': item_id},
                        {'$set': mongo_item},
                        upsert=True
                    )
                logger.info(f"Stored metadata for {len(texts)} items in MongoDB")
            except Exception as e:
                logger.error(f"Failed to store metadata in MongoDB: {e}")
        
        return index, data
    
    def add_messages_to_index(self, messages):
        """
        Add messages to the FAISS index.
        
        Args:
            messages: List of message dictionaries
        """
        if not messages:
            return
        
        # Process messages in batches to avoid API rate limits
        batch_size = 10
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i+batch_size]
            
            # Process each message in the batch
            texts = []
            metadata_list = []
            for message in batch:
                # Skip if message has no text or is already in the index
                if not message.get('text'):
                    continue
                
                # Check if message is already indexed
                message_id = message.get('id')
                if message_id:
                    # Check if this message ID is already in our data
                    if any(item.get('id') == message_id for item in self.message_data['items']):
                        continue
                
                texts.append(message.get('text', ''))
                metadata_list.append(message)
            
            # Add to index
            self.message_index, self.message_data = self._add_to_index(texts, metadata_list, self.message_index, self.message_data)
            
            logger.info(f"Added batch of {len(batch)} messages to FAISS index")
        
        logger.info(f"FAISS index now contains {self.message_index.ntotal} vectors")
    
    def add_personal_info_to_index(self, personal_info_items):
        """
        Add personal information items to the FAISS index.
        
        Args:
            personal_info_items: List of personal info dictionaries
        """
        if not personal_info_items:
            return
        
        # Clear existing personal info index and data
        self.personal_info_index = faiss.IndexFlatIP(self.embedding_dim)
        self.personal_info_data = {'items': []}
        
        # Process items in batches
        batch_size = 10
        for i in range(0, len(personal_info_items), batch_size):
            batch = personal_info_items[i:i+batch_size]
            
            # Process each item in the batch
            texts = []
            metadata_list = []
            for item in batch:
                # Skip if item has no text
                if not item.get('text'):
                    continue
                
                texts.append(item.get('text', ''))
                metadata_list.append(item)
            
            # Add to index
            self.personal_info_index, self.personal_info_data = self._add_to_index(texts, metadata_list, self.personal_info_index, self.personal_info_data)
            
            logger.info(f"Added batch of {len(batch)} personal info items to FAISS index")
        
        logger.info(f"Personal info FAISS index now contains {self.personal_info_index.ntotal} vectors")
    
    def retrieve_relevant_context(self, query, top_k=5, include_personal_info=True):
        """
        Retrieve relevant context for a query using FAISS.
        
        Args:
            query: Query text
            top_k: Number of results to return
            include_personal_info: Whether to include personal info in results
            
        Returns:
            dict: Retrieved context
        """
        # Get embedding for query
        query_embedding = self._get_embedding(query)
        
        if query_embedding is None:
            logger.error("Failed to get embedding for query")
            return {"messages": [], "personal_info": []}
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        
        # Initialize results
        results = {"messages": [], "personal_info": []}
        
        # Search message index if it has vectors
        if self.message_index.ntotal > 0:
            # Search FAISS index
            D, I = self.message_index.search(query_embedding.reshape(1, -1), min(top_k, self.message_index.ntotal))
            
            # Add results to output
            for i, idx in enumerate(I[0]):
                if idx < len(self.message_data['items']) and D[0][i] > 0.7:  # Similarity threshold
                    results["messages"].append({
                        "item": self.message_data['items'][idx],
                        "score": float(D[0][i])
                    })
        
        # Search personal info index if requested and it has vectors
        if include_personal_info and self.personal_info_index.ntotal > 0:
            # Search FAISS index
            D, I = self.personal_info_index.search(query_embedding.reshape(1, -1), min(top_k, self.personal_info_index.ntotal))
            
            # Add results to output
            for i, idx in enumerate(I[0]):
                if idx < len(self.personal_info_data['items']) and D[0][i] > 0.7:  # Similarity threshold
                    results["personal_info"].append({
                        "item": self.personal_info_data['items'][idx],
                        "score": float(D[0][i])
                    })
        
        return results
    
    def format_context_for_prompt(self, context, max_tokens=1000):
        """
        Format retrieved context for inclusion in a prompt.
        
        Args:
            context: Retrieved context
            max_tokens: Maximum number of tokens to include
            
        Returns:
            str: Formatted context
        """
        formatted_text = "Relevant message history:\n"
        
        # Add messages
        for item in context.get("messages", []):
            message = item.get("item", {})
            score = item.get("score", 0)
            
            sender = message.get("sender", "unknown")
            text = message.get("text", "")
            timestamp = message.get("timestamp", "")
            
            formatted_text += f"- [{timestamp}] {sender}: {text} (relevance: {score:.2f})\n"
        
        # Add personal info
        if context.get("personal_info"):
            formatted_text += "\nRelevant personal information:\n"
            
            for item in context.get("personal_info", []):
                info = item.get("item", {})
                score = item.get("score", 0)
                
                category = info.get("category", "unknown")
                text = info.get("text", "")
                
                formatted_text += f"- {category}: {text} (relevance: {score:.2f})\n"
        
        # Simple token count estimation (can be improved)
        if len(formatted_text.split()) > max_tokens:
            # Truncate to approximate token count
            words = formatted_text.split()
            formatted_text = " ".join(words[:max_tokens]) + "..."
        
        return formatted_text
    
    def migrate_from_embedding_rag(self, embedding_rag):
        """
        Migrate data from the original embedding RAG system.
        
        Args:
            embedding_rag: Original embedding RAG system instance
        """
        # Migrate message data
        if hasattr(embedding_rag, 'message_embeddings'):
            messages = []
            for i, item in enumerate(embedding_rag.message_embeddings.get('items', [])):
                messages.append(item)
            
            # Add messages to FAISS index
            self.add_messages_to_index(messages)
            logger.info(f"Migrated {len(messages)} messages from embedding RAG")
        
        # Migrate personal info data
        if hasattr(embedding_rag, 'personal_info_embeddings'):
            personal_info = []
            for i, item in enumerate(embedding_rag.personal_info_embeddings.get('items', [])):
                personal_info.append(item)
            
            # Add personal info to FAISS index
            self.add_personal_info_to_index(personal_info)
            logger.info(f"Migrated {len(personal_info)} personal info items from embedding RAG")
