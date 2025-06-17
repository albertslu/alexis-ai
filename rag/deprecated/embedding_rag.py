#!/usr/bin/env python3

"""
Embedding-based RAG System for AI Clone

This module implements semantic retrieval using embeddings instead of keyword matching.
"""

import os
import json
import numpy as np
from datetime import datetime
from pathlib import Path
import pickle
from openai import OpenAI
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class EmbeddingRAG:
    """
    Embedding-based RAG system that uses semantic similarity for retrieval.
    """
    
    def __init__(self, data_dir=None):
        """
        Initialize the embedding-based RAG system.
        
        Args:
            data_dir: Directory for storing data files
        """
        # Set data directory
        if data_dir is None:
            self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        else:
            self.data_dir = data_dir
            
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # File paths
        self.embeddings_file = os.path.join(self.data_dir, 'message_embeddings.pkl')
        self.personal_info_embeddings_file = os.path.join(self.data_dir, 'personal_info_embeddings.pkl')
        
        # Load existing embeddings if available
        self.message_embeddings = self._load_embeddings(self.embeddings_file)
        self.personal_info_embeddings = self._load_embeddings(self.personal_info_embeddings_file)
        
    def _load_embeddings(self, file_path):
        """
        Load embeddings from file.
        
        Args:
            file_path: Path to embeddings file
            
        Returns:
            dict: Loaded embeddings or empty dict if file doesn't exist
        """
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading embeddings from {file_path}: {str(e)}")
        
        return {'items': [], 'embeddings': []}
    
    def _save_embeddings(self, embeddings, file_path):
        """
        Save embeddings to file.
        
        Args:
            embeddings: Embeddings to save
            file_path: Path to save embeddings to
        """
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(embeddings, f)
        except Exception as e:
            print(f"Error saving embeddings to {file_path}: {str(e)}")
    
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
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {str(e)}")
            return None
    
    def _cosine_similarity(self, a, b):
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            a: First vector
            b: Second vector
            
        Returns:
            float: Cosine similarity
        """
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def add_messages_to_index(self, messages):
        """
        Add messages to the embedding index.
        
        Args:
            messages: List of message dictionaries
        """
        if not messages:
            return
            
        # Limit the number of messages to process to avoid too many API calls
        max_messages = 50
        if len(messages) > max_messages:
            print(f"Limiting message processing to {max_messages} messages (out of {len(messages)})")
            messages = messages[:max_messages]
            
        # Process messages in larger batches to reduce API calls
        batch_size = 20
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i+batch_size]
            
            # Collect texts for batch embedding
            texts_to_embed = []
            batch_items = []
            
            for message in batch:
                # Skip if message has no text
                if not message.get('text'):
                    continue
                    
                # Check if message is already indexed
                message_id = message.get('id')
                if message_id:
                    # Check if this message ID is already in our data
                    existing_ids = [item.get('id') for item in self.message_embeddings['items']]
                    if message_id in existing_ids:
                        continue
                
                # Add to batch for embedding
                texts_to_embed.append(message.get('text', ''))
                batch_items.append(message)
            
            if not texts_to_embed:
                continue
                
            try:
                # Get embeddings for the batch in a single API call
                print(f"Getting embeddings for batch of {len(texts_to_embed)} messages")
                
                # Use text-embedding-3-large for higher quality embeddings
                response = client.embeddings.create(
                    input=texts_to_embed,
                    model="text-embedding-3-large"
                )
                
                # Process embeddings
                for i, embedding_data in enumerate(response.data):
                    if i < len(batch_items):
                        # Create item to store
                        item = {
                            'id': batch_items[i].get('id', str(uuid.uuid4())),
                            'text': batch_items[i].get('text', ''),
                            'context': batch_items[i].get('previous_message', ''),
                            'sender': batch_items[i].get('sender', ''),
                            'timestamp': batch_items[i].get('timestamp', datetime.now().isoformat()),
                            'channel': batch_items[i].get('channel', '')
                        }
                        
                        # Get embedding
                        embedding = embedding_data.embedding
                        
                        # Add to embeddings
                        self.message_embeddings['items'].append(item)
                        self.message_embeddings['embeddings'].append(embedding)
            except Exception as e:
                print(f"Error getting embeddings for batch: {str(e)}")
                
        # Save updated embeddings
        self._save_embeddings(self.message_embeddings, self.embeddings_file)
    
    def add_personal_info_to_index(self, personal_info):
        """
        Add personal info to the embedding index.
        
        Args:
            personal_info: Personal info dictionary
        """
        # Clear existing personal info embeddings
        self.personal_info_embeddings = {'items': [], 'embeddings': []}
        
        # Process each category and fact
        for category, facts in personal_info.items():
            if isinstance(facts, list):
                for fact in facts:
                    # Create item with category and fact
                    item = {
                        'category': category,
                        'fact': fact if isinstance(fact, str) else json.dumps(fact)
                    }
                    
                    # Get embedding for fact
                    text = item['fact']
                    embedding = self._get_embedding(text)
                    
                    if embedding:
                        # Add item and embedding to index
                        self.personal_info_embeddings['items'].append(item)
                        self.personal_info_embeddings['embeddings'].append(embedding)
        
        # Save updated embeddings
        self._save_embeddings(self.personal_info_embeddings, self.personal_info_embeddings_file)
    
    def retrieve_relevant_messages(self, query, max_results=5, similarity_threshold=0.5):
        """
        Retrieve messages relevant to the query based on embedding similarity.
        
        Args:
            query: Query text
            max_results: Maximum number of results to return
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            list: Relevant messages with similarity scores
        """
        try:
            # Skip if no embeddings are available
            if not self.message_embeddings['embeddings']:
                print("No embeddings available for retrieval")
                return []
                
            # Get embedding for query
            query_embedding = self._get_embedding(query)
            
            if not query_embedding:
                print("Failed to get embedding for query")
                return []
                
            # Calculate similarity with all message embeddings
            similarities = []
            
            # Limit processing to avoid too many comparisons
            max_messages_to_process = min(100, len(self.message_embeddings['items']))
            
            for i in range(max_messages_to_process):
                item = self.message_embeddings['items'][i]
                embedding = self.message_embeddings['embeddings'][i]
                
                if not embedding:
                    continue
                    
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, embedding)
                
                # Only include items with similarity above threshold
                if similarity > similarity_threshold:
                    # Create a result item with text and metadata
                    result_item = {
                        'text': item.get('text', ''),
                        'similarity': similarity,
                        'sender': item.get('sender', ''),
                        'timestamp': item.get('timestamp', ''),
                        'channel': item.get('channel', '')
                    }
                    
                    similarities.append(result_item)
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Return top results
            return similarities[:max_results]
        except Exception as e:
            print(f"Error retrieving relevant messages: {str(e)}")
            # Return empty list on error
            return []
    
    def retrieve_relevant_personal_info(self, query, top_k=5, threshold=0.7):
        """
        Retrieve relevant personal information based on semantic similarity.
        
        Args:
            query: Query text
            top_k: Maximum number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            list: Relevant personal information
        """
        try:
            # Skip if no personal info is available
            if not self.personal_info_embeddings['items']:
                return []
                
            # Get embedding for query
            query_embedding = self._get_embedding(query)
            
            if not query_embedding:
                return []
                
            # Calculate similarity with all personal info embeddings
            similarities = []
            
            # Limit processing to avoid too many API calls
            max_items_to_process = min(100, len(self.personal_info_embeddings['items']))
            
            for i in range(max_items_to_process):
                item = self.personal_info_embeddings['items'][i]
                embedding = self.personal_info_embeddings['embeddings'][i]
                
                if embedding:
                    similarity = self._cosine_similarity(query_embedding, embedding)
                    
                    # Only include items with similarity above threshold
                    if similarity > threshold:
                        similarities.append({
                            'text': item.get('text', ''),
                            'category': item.get('category', ''),
                            'source': item.get('source', ''),
                            'similarity': similarity
                        })
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Return top results
            return similarities[:top_k]
        except Exception as e:
            print(f"Error retrieving relevant personal info: {str(e)}")
            return []
    
    def enhance_prompt_with_personal_info(self, query, system_prompt):
        """
        Enhance system prompt with relevant personal info.
        
        Args:
            query: User query
            system_prompt: Original system prompt
            
        Returns:
            str: Enhanced system prompt
        """
        # Retrieve relevant personal info
        relevant_info = self.retrieve_relevant_personal_info(query)
        
        if not relevant_info:
            return system_prompt
        
        # Format personal info
        personal_info_text = "Here are some relevant facts about you:\n"
        for info in relevant_info:
            personal_info_text += f"- {info['fact']} (confidence: {info['similarity']:.2f})\n"
        
        # Add to system prompt
        enhanced_prompt = f"{system_prompt}\n\n{personal_info_text}"
        
        return enhanced_prompt
    
    def enhance_prompt_with_message_history(self, query, system_prompt):
        """
        Enhance system prompt with relevant message history.
        
        Args:
            query: User query
            system_prompt: Original system prompt
            
        Returns:
            str: Enhanced system prompt
        """
        # Retrieve relevant messages
        relevant_messages = self.retrieve_relevant_messages(query)
        
        if not relevant_messages:
            return system_prompt
        
        # Format message history
        history_text = "Here are some relevant previous messages:\n"
        for msg in relevant_messages:
            sender = "You" if msg.get('sender') == 'user' else "Your AI clone"
            history_text += f"- {sender}: {msg.get('text')} (relevance: {msg.get('similarity'):.2f})\n"
        
        # Add to system prompt
        enhanced_prompt = f"{system_prompt}\n\n{history_text}"
        
        return enhanced_prompt
