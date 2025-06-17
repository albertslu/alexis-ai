#!/usr/bin/env python3

"""
Memory-Enhanced RAG System for AI Clone

This module extends the enhanced RAG system with Letta-like memory capabilities,
organizing memories into core, episodic, and archival categories for better recall.
"""

import os
import json
import sys
import uuid
import logging
from datetime import datetime as dt
from typing import Dict, List, Any, Optional
import hashlib
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.enhanced_rag_integration import similarity_score
# Deprecated: MessageRAG is no longer used as we use Pinecone exclusively
# from rag.rag_system import MessageRAG
from rag.pinecone_rag import PineconeRAGSystem

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
PERSONAL_INFO_PATH = os.path.join(DATA_DIR, 'personal_info.json')
MEMORY_DIR = os.path.join(DATA_DIR, 'memory')

# Ensure memory directory exists
os.makedirs(MEMORY_DIR, exist_ok=True)

class MemoryEnhancedRAG:
    """
    Memory-enhanced RAG system that stores and retrieves memories.
    This system enhances the standard RAG with long-term memory storage.
    """
    
    def __init__(self, user_id="default"):
        """
        Initialize the memory-enhanced RAG system.
        
        Args:
            user_id: User identifier for user-specific memories
        """
        self.user_id = user_id
        self.memory_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       'data', 'memory', f'{user_id}_memory.json')
        
        # Initialize memory storage
        self.core_memories = []
        self.episodic_memories = []
        self.archival_memories = []
        
        # Embedding cache to avoid repeated API calls
        self.embedding_cache = {}
        
        # Load existing memories if available
        self.load_memory()
        
        # Initialize OpenAI client for embeddings
        self.client = OpenAI()
        
        # Patch the enhance_prompt method
        self.original_enhance_prompt = None
        
        logging.info(f"Initializing memory integration - patching enhance_prompt_with_rag")
        
        # Set maximum memory retrieval limits
        self.max_core = 3      # Reduced from 7
        self.max_episodic = 2  # Reduced from 5
        self.max_archival = 1  # Reduced from 3
    
    def load_memory(self):
        """
        Load memory from MongoDB or file
        
        Args:
            user_id: User ID
            
        Returns:
            dict: Memory data
        """
        # First try to load from MongoDB
        try:
            mongodb_uri = os.getenv("MONGODB_URI")
            mongodb_database = os.getenv("MONGODB_DATABASE")
            
            if mongodb_uri and mongodb_database:
                from pymongo import MongoClient
                
                client = MongoClient(mongodb_uri)
                db = client.get_database(mongodb_database)
                
                memory_data = db.user_memories.find_one({"user_id": self.user_id})
                
                if memory_data:
                    # Convert MongoDB _id to string for JSON serialization
                    memory_data["_id"] = str(memory_data["_id"])
                    
                    logger.info(f"Memory loaded from MongoDB for user {self.user_id}")
                    self.core_memories = memory_data.get("core_memory", [])
                    self.episodic_memories = memory_data.get("episodic_memory", [])
                    self.archival_memories = memory_data.get("archival_memory", [])
                    return True
        except Exception as mongo_error:
            logger.error(f"Error loading memory from MongoDB: {mongo_error}")
            # Fall back to file-based memory
        
        # If MongoDB load failed or is not configured, try loading from file
        memory_file = self.memory_path
        
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r') as f:
                    memory_data = json.load(f)
                logger.info(f"Memory loaded from file: {memory_file}")
                self.core_memories = memory_data.get("core_memory", [])
                self.episodic_memories = memory_data.get("episodic_memory", [])
                self.archival_memories = memory_data.get("archival_memory", [])
                return True
            except Exception as e:
                logger.error(f"Error loading memory from file: {e}")
        
        # If no memory exists, create a new one
        logger.info(f"No memory found for user {self.user_id}, creating new memory")
        self.core_memories = []
        self.episodic_memories = []
        self.archival_memories = []
        return True
    
    def save_memory(self, memory: Dict = None) -> bool:
        """
        Save memory to MongoDB and file
        
        Args:
            memory: Memory data (optional)
            
        Returns:
            bool: Success status
        """
        try:
            # Prepare memory data
            if memory is None:
                memory = {
                    "core_memory": self.core_memories,
                    "episodic_memory": self.episodic_memories,
                    "archival_memory": self.archival_memories,
                    "last_updated": dt.now().isoformat()
                }
            
            # First try to save to MongoDB
            try:
                mongodb_uri = os.getenv("MONGODB_URI")
                mongodb_database = os.getenv("MONGODB_DATABASE")
                
                if mongodb_uri and mongodb_database:
                    from pymongo import MongoClient
                    
                    client = MongoClient(mongodb_uri)
                    db = client.get_database(mongodb_database)
                    
                    # Check if memory exists for this user
                    existing_memory = db.user_memories.find_one({"user_id": self.user_id})
                    
                    if existing_memory:
                        # Update existing memory
                        db.user_memories.update_one(
                            {"user_id": self.user_id},
                            {"$set": {
                                "core_memory": memory.get("core_memory", []),
                                "episodic_memory": memory.get("episodic_memory", []),
                                "archival_memory": memory.get("archival_memory", []),
                                "last_updated": memory.get("last_updated", dt.now().isoformat())
                            }}
                        )
                    else:
                        # Create new memory
                        db.user_memories.insert_one({
                            "user_id": self.user_id,
                            "core_memory": memory.get("core_memory", []),
                            "episodic_memory": memory.get("episodic_memory", []),
                            "archival_memory": memory.get("archival_memory", []),
                            "created_at": dt.now().isoformat(),
                            "last_updated": memory.get("last_updated", dt.now().isoformat())
                        })
                    
                    logger.info(f"Memory saved to MongoDB for user {self.user_id}")
            except Exception as mongo_error:
                logger.error(f"Error saving memory to MongoDB: {mongo_error}")
                # Continue even if MongoDB save fails - we'll still save to file
            
            # Also save to file as backup
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
                
                with open(self.memory_path, 'w') as f:
                    json.dump(memory, f, indent=2)
                
                logger.info(f"Memory saved to file: {self.memory_path}")
            except Exception as file_error:
                logger.error(f"Error saving memory to file: {file_error}")
                # If MongoDB save succeeded but file save failed, we still return True
                return True
            
            return True
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return False
    
    def get_embedding(self, text):
        """Get embedding for text with caching to avoid repeated API calls"""
        if not text:
            return None
            
        # Use a hash of the text as the cache key
        cache_key = hashlib.md5(text.encode()).hexdigest()
        
        # Check if we already have this embedding cached
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
            
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            embedding = response.data[0].embedding
            
            # Cache the embedding
            self.embedding_cache[cache_key] = embedding
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
            
    def get_batch_embeddings(self, texts):
        """Get embeddings for multiple texts in a single API call"""
        if not texts:
            return []
            
        # Filter out empty texts and texts that are already cached
        texts_to_embed = []
        cache_keys = []
        cached_embeddings = {}
        result_embeddings = [None] * len(texts)
        
        for i, text in enumerate(texts):
            if not text:
                continue
                
            cache_key = hashlib.md5(text.encode()).hexdigest()
            
            if cache_key in self.embedding_cache:
                result_embeddings[i] = self.embedding_cache[cache_key]
                cached_embeddings[i] = self.embedding_cache[cache_key]
            else:
                texts_to_embed.append(text)
                cache_keys.append((i, cache_key))
        
        # If all embeddings are cached, return them
        if not texts_to_embed:
            return result_embeddings
            
        try:
            # Make a single API call for all texts that need embeddings
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts_to_embed
            )
            
            # Process the response and update the cache
            for j, embedding_data in enumerate(response.data):
                i, cache_key = cache_keys[j]
                embedding = embedding_data.embedding
                self.embedding_cache[cache_key] = embedding
                result_embeddings[i] = embedding
                
            return result_embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            # Fall back to individual embedding calls for robustness
            for i, text in enumerate(texts):
                if result_embeddings[i] is None and text:
                    result_embeddings[i] = self.get_embedding(text)
            return result_embeddings
    
    def add_core_memory(self, content: str) -> bool:
        """
        Add a fact to core memory.
        Core memory is always included in the context.
        
        Args:
            content: Memory content
            
        Returns:
            bool: Success status
        """
        try:
            # Check if similar memory already exists
            for memory in self.core_memories:
                if self._is_similar(memory["content"], content):
                    # Update existing memory
                    memory["content"] = content
                    memory["last_accessed"] = dt.now().isoformat()
                    self.save_memory()
                    return True
            
            # Add new memory
            self.core_memories.append({
                "id": str(uuid.uuid4()),
                "content": content,
                "created_at": dt.now().isoformat(),
                "last_accessed": dt.now().isoformat()
            })
            
            self.save_memory()
            return True
        except Exception as e:
            logger.error(f"Error adding core memory: {e}")
            return False
    
    def add_episodic_memory(self, content: str, context: str = None) -> bool:
        """
        Add an episodic memory.
        Episodic memories are specific interactions or events.
        
        Args:
            content: Memory content
            context: Optional context information
            
        Returns:
            bool: Success status
        """
        try:
            self.episodic_memories.append({
                "id": str(uuid.uuid4()),
                "content": content,
                "context": context,
                "created_at": dt.now().isoformat(),
                "last_accessed": dt.now().isoformat()
            })
            
            # Limit episodic memory to 100 items
            if len(self.episodic_memories) > 100:
                # Sort by last_accessed and remove oldest
                self.episodic_memories.sort(
                    key=lambda x: x["last_accessed"]
                )
                # Move oldest to archival memory
                oldest = self.episodic_memories.pop(0)
                self.archival_memories.append(oldest)
            
            self.save_memory()
            return True
        except Exception as e:
            logger.error(f"Error adding episodic memory: {e}")
            return False
    
    def add_archival_memory(self, content: str) -> bool:
        """
        Add an archival memory.
        Archival memories are stored for long-term reference but not always in context.
        
        Args:
            content: Memory content
            
        Returns:
            bool: Success status
        """
        try:
            self.archival_memories.append({
                "id": str(uuid.uuid4()),
                "content": content,
                "created_at": dt.now().isoformat(),
                "last_accessed": dt.now().isoformat()
            })
            
            self.save_memory()
            return True
        except Exception as e:
            logger.error(f"Error adding archival memory: {e}")
            return False
    
    def retrieve_relevant_memories(self, query, conversation_history=None):
        """Retrieve memories relevant to the query using Pinecone vector search"""
        # Check if this is a simple greeting
        simple_greetings = ["hello", "hi", "hey", "what's up", "sup", "yo", "hola", "howdy"]
        if query.lower().strip() in simple_greetings:
            logging.info("Detected simple greeting, using minimal context")
            # For simple greetings, just return a minimal set of core memories
            return {
                "core_memories": self.core_memories[:1] if self.core_memories else [],
                "episodic_memories": [],
                "archival_memories": []
            }
            
        try:
            # Import Pinecone RAG system
            from rag.pinecone_rag import PineconeRAGSystem
            
            # Initialize Pinecone RAG with the same user ID
            pinecone_rag = PineconeRAGSystem(user_id=self.user_id)
            
            # Generate embedding for the query
            query_embedding = self.get_embedding(query)
            
            if not query_embedding:
                logging.warning("Failed to generate embedding for query, using keyword fallback")
                # Fallback to keyword matching if embedding fails
                return self.retrieve_memories_by_keywords(query)
            
            # Sync memories to Pinecone if needed
            self._sync_memories_to_pinecone(pinecone_rag)
            
            # Use Pinecone for vector search
            logging.info("Using Pinecone vector search for memory retrieval")
            
            # Search for relevant memories in Pinecone
            search_results = pinecone_rag.search(query, top_k=10)
            
            # Process search results
            result = {
                "core_memories": [],
                "episodic_memories": [],
                "archival_memories": []
            }
            
            # Extract memories from search results
            for item in search_results:
                metadata = item.get('metadata', {})
                memory_type = metadata.get('memory_type')
                content = metadata.get('content')
                
                if memory_type and content:
                    if memory_type == 'core' and len(result["core_memories"]) < self.max_core:
                        result["core_memories"].append(content)
                    elif memory_type == 'episodic' and len(result["episodic_memories"]) < self.max_episodic:
                        result["episodic_memories"].append(content)
                    elif memory_type == 'archival' and len(result["archival_memories"]) < self.max_archival:
                        result["archival_memories"].append(content)
            
            # Update access time for returned memories
            for memory in result["core_memories"]:
                for core_memory in self.core_memories:
                    if core_memory["content"] == memory:
                        core_memory["last_accessed"] = dt.now().isoformat()
            for memory in result["episodic_memories"]:
                for episodic_memory in self.episodic_memories:
                    if episodic_memory["content"] == memory:
                        episodic_memory["last_accessed"] = dt.now().isoformat()
            for memory in result["archival_memories"]:
                for archival_memory in self.archival_memories:
                    if archival_memory["content"] == memory:
                        archival_memory["last_accessed"] = dt.now().isoformat()
            
            self.save_memory()
            
            return result
            
        except Exception as e:
            logging.error(f"Error using Pinecone for memory retrieval: {e}")
            logging.info("Falling back to local memory retrieval")
            
            # Fall back to the original implementation if Pinecone fails
            return self._retrieve_relevant_memories_local(query)
    
    def _retrieve_relevant_memories_local(self, query):
        """Original local implementation of memory retrieval as fallback"""
        # Generate embedding for the query
        query_embedding = self.get_embedding(query)
        
        if not query_embedding:
            logging.warning("Failed to generate embedding for query, using keyword fallback")
            # Fallback to keyword matching if embedding fails
            return self.retrieve_memories_by_keywords(query)
            
        # Prepare all memories for batch embedding
        all_memories = []
        memory_texts = []
        
        # Add core memories
        for memory in self.core_memories:
            all_memories.append(("core", memory))
            memory_texts.append(memory.get("content", ""))
            
        # Add episodic memories
        for memory in self.episodic_memories:
            all_memories.append(("episodic", memory))
            memory_texts.append(memory.get("content", ""))
            
        # Add archival memories
        for memory in self.archival_memories:
            all_memories.append(("archival", memory))
            memory_texts.append(memory.get("content", ""))
            
        # Get embeddings for all memories in a single batch
        memory_embeddings = self.get_batch_embeddings(memory_texts)
        
        # Calculate scores for all memories
        scored_memories = {
            "core_memories": [],
            "episodic_memories": [],
            "archival_memories": []
        }
        
        for i, (memory_type, memory) in enumerate(all_memories):
            if memory_embeddings[i] is None:
                continue
                
            # Convert to numpy arrays if they're lists
            if isinstance(query_embedding, list):
                query_embedding = np.array(query_embedding)
            if isinstance(memory_embeddings[i], list):
                memory_embeddings[i] = np.array(memory_embeddings[i])
                
            # Calculate embedding similarity
            query_embedding_2d = query_embedding.reshape(1, -1)
            memory_embedding_2d = memory_embeddings[i].reshape(1, -1)
            embedding_similarity = cosine_similarity(query_embedding_2d, memory_embedding_2d)[0][0]
            
            # Intent matching (using existing method)
            intent_match_score = 0
            query_intent = self._analyze_message_intent(query)
            memory_intent = self._analyze_message_intent(memory.get("content", ""))
            
            if query_intent.get('is_question') and memory_intent.get('is_question'):
                intent_match_score = 0.1
            elif query_intent.get('is_greeting') and memory_intent.get('is_greeting'):
                intent_match_score = 0.1
            
            # Topic matching
            topic_match_score = self.calculate_topic_match(query, memory.get("content", ""))
            
            # Keyword matching
            keyword_match_score = self.calculate_keyword_match(query, memory.get("content", ""))
            
            # Calculate final score with weights
            final_score = (
                0.7 * embedding_similarity +
                0.1 * intent_match_score +
                0.1 * topic_match_score +
                0.1 * keyword_match_score
            )
            
            # Add memory with score to appropriate category
            if memory_type == "core":
                scored_memories["core_memories"].append((memory, final_score))
            elif memory_type == "episodic":
                scored_memories["episodic_memories"].append((memory, final_score))
            elif memory_type == "archival":
                scored_memories["archival_memories"].append((memory, final_score))
        
        # Sort memories by score and take top N
        scored_memories["core_memories"].sort(key=lambda x: x[1], reverse=True)
        scored_memories["episodic_memories"].sort(key=lambda x: x[1], reverse=True)
        scored_memories["archival_memories"].sort(key=lambda x: x[1], reverse=True)
        
        # Extract just the content for the result
        result = {
            "core_memories": [memory[0]["content"] for memory in scored_memories["core_memories"][:self.max_core]],
            "episodic_memories": [memory[0]["content"] for memory in scored_memories["episodic_memories"][:self.max_episodic]],
            "archival_memories": [memory[0]["content"] for memory in scored_memories["archival_memories"][:self.max_archival]]
        }
        
        # Update access time for returned memories
        for memory in result["core_memories"]:
            for core_memory in self.core_memories:
                if core_memory["content"] == memory:
                    core_memory["last_accessed"] = dt.now().isoformat()
        for memory in result["episodic_memories"]:
            for episodic_memory in self.episodic_memories:
                if episodic_memory["content"] == memory:
                    episodic_memory["last_accessed"] = dt.now().isoformat()
        for memory in result["archival_memories"]:
            for archival_memory in self.archival_memories:
                if archival_memory["content"] == memory:
                    archival_memory["last_accessed"] = dt.now().isoformat()
        
        self.save_memory()
        
        return result
        
    def _sync_memories_to_pinecone(self, pinecone_rag):
        """Sync memories from MongoDB to Pinecone"""
        try:
            # Prepare memories for syncing
            all_memories = []
            
            # Add core memories
            for memory in self.core_memories:
                all_memories.append({
                    "content": memory.get("content", ""),
                    "memory_type": "core",
                    "created_at": memory.get("created_at", ""),
                    "last_accessed": memory.get("last_accessed", "")
                })
            
            # Add episodic memories
            for memory in self.episodic_memories:
                all_memories.append({
                    "content": memory.get("content", ""),
                    "memory_type": "episodic",
                    "created_at": memory.get("created_at", ""),
                    "last_accessed": memory.get("last_accessed", "")
                })
            
            # Add archival memories
            for memory in self.archival_memories:
                all_memories.append({
                    "content": memory.get("content", ""),
                    "memory_type": "archival",
                    "created_at": memory.get("created_at", ""),
                    "last_accessed": memory.get("last_accessed", "")
                })
            
            # Sync memories to Pinecone
            if all_memories:
                pinecone_rag.add_memories_to_index(all_memories)
                logging.info(f"Synced {len(all_memories)} memories to Pinecone")
            
        except Exception as e:
            logging.error(f"Error syncing memories to Pinecone: {e}")
    
    def _update_memory_access_time(self, memory_id: str, access_time: str) -> None:
        """
        Update the access time for a memory.
        
        Args:
            memory_id: ID of the memory to update
            access_time: New access time
        """
        try:
            # Update access time for core memories
            for memory in self.core_memories:
                if memory["id"] == memory_id:
                    memory["last_accessed"] = access_time
                    self.save_memory()
                    return
            
            # Update access time for episodic memories
            for memory in self.episodic_memories:
                if memory["id"] == memory_id:
                    memory["last_accessed"] = access_time
                    self.save_memory()
                    return
            
            # Update access time for archival memories
            for memory in self.archival_memories:
                if memory["id"] == memory_id:
                    memory["last_accessed"] = access_time
                    self.save_memory()
                    return
        except Exception as e:
            logger.error(f"Error updating memory access time: {e}")
    
    def _find_relevant_memories(self, memories: List[Dict], query: str, max_count: int, threshold: float = 0.1) -> List[Dict]:
        """
        Find memories relevant to the query using similarity scoring.
        
        Args:
            memories: List of memories to search
            query: Query to find relevant memories
            max_count: Maximum number of memories to return
            threshold: Minimum similarity threshold
            
        Returns:
            List[Dict]: List of relevant memories
        """
        # Extract key terms from the query
        query_terms = set(query.lower().split())
        
        # Calculate similarity scores
        scored_memories = []
        for memory in memories:
            content = memory["content"]
            
            # Calculate similarity score
            score = similarity_score(query, content)
            
            # Boost score for keyword matches
            memory_terms = set(content.lower().split())
            term_overlap = query_terms.intersection(memory_terms)
            if term_overlap:
                score += 0.1 * len(term_overlap) / len(query_terms)
            
            # Check for category matches in the query
            lower_query = query.lower()
            if "education" in lower_query and "education" in content.lower():
                score += 0.2
            elif "work" in lower_query and "work" in content.lower():
                score += 0.2
            elif "hobby" in lower_query and "interest" in content.lower():
                score += 0.2
            elif "interest" in lower_query and "interest" in content.lower():
                score += 0.2
            elif "location" in lower_query and "location" in content.lower():
                score += 0.2
            elif "travel" in lower_query and ("travel" in content.lower() or "thailand" in content.lower()):
                score += 0.2
            
            if score > threshold:  # Minimum similarity threshold
                scored_memories.append((score, memory))
        
        # Sort by relevance score (descending)
        scored_memories.sort(reverse=True, key=lambda x: x[0])
        
        # Update access time for returned memories
        now = dt.now().isoformat()
        result_memories = []
        for _, memory in scored_memories[:max_count]:
            memory["last_accessed"] = now
            result_memories.append(memory)
        
        return result_memories
    
    def _is_similar(self, text1: str, text2: str) -> bool:
        """
        Check if two texts are similar using the similarity_score function.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            bool: True if texts are similar
        """
        score = similarity_score(text1, text2)
        return score > 0.5  # Threshold for similarity
    
    def enhance_prompt_with_rag(self, system_prompt, query, conversation_history=None):
        """
        Enhance the system prompt with relevant memories from the RAG system.
        
        Args:
            system_prompt: The original system prompt
            query: The user query
            conversation_history: Optional conversation history
            
        Returns:
            Enhanced system prompt with memory context
        """
        try:
            # Check if this is a simple greeting or short query
            simple_greetings = ["hello", "hi", "hey", "what's up", "sup", "yo", "hola", "howdy"]
            
            # Determine if this is a simple query (greeting or very short)
            is_simple_query = query.lower().strip() in simple_greetings or len(query.split()) <= 3
            
            # For simple queries, use minimal context
            if is_simple_query:
                logging.info("Detected simple query, using minimal context")
                enhanced_prompt = system_prompt + "\n\nNote: This appears to be a simple greeting or short query. Respond naturally and briefly."
                return enhanced_prompt
            
            # For complex queries, determine whether to use keyword or embedding RAG
            is_complex_query = len(query.split()) > 8 or "?" in query
            
            # Get relevant memories using the appropriate method
            if is_complex_query:
                logging.info("Using embedding-based RAG for complex query")
                memory_context = self.retrieve_relevant_memories(query)
            else:
                logging.info("Using keyword-based RAG for standard query")
                memory_context = self.retrieve_memories_by_keywords(query)
            
            # Format memories naturally
            formatted_memories = self._format_memories_naturally(memory_context)
            
            # Enhance the prompt with memory context
            if formatted_memories:
                enhanced_prompt = system_prompt + "\n\n" + formatted_memories
                logging.info("Enhanced prompt with memory context")
            else:
                enhanced_prompt = system_prompt
                logging.info("No relevant memories found, using original prompt")
            
            return enhanced_prompt
        except Exception as e:
            logger.error(f"Error enhancing prompt with RAG: {e}")
            return system_prompt
            
    def retrieve_memories_by_keywords(self, query):
        """Retrieve memories based on keyword matching for faster processing"""
        try:
            # Initialize result
            result = {
                "core_memories": [],
                "episodic_memories": [],
                "archival_memories": []
            }
            
            # Extract keywords from query
            query_words = set(query.lower().split())
            
            # Score core memories by keyword matches
            scored_core = []
            for memory in self.core_memories:
                content = memory.get("content", "")
                memory_words = set(content.lower().split())
                
                # Calculate keyword match score
                overlap = query_words.intersection(memory_words)
                if overlap:
                    score = len(overlap) / len(query_words)
                    
                    # Boost score for important keywords
                    for word in overlap:
                        if word in ["name", "job", "work", "live", "from", "education", "school", "hobby", "interest"]:
                            score += 0.2
                    
                    scored_core.append((memory, score))
            
            # Sort and take top N core memories
            scored_core.sort(key=lambda x: x[1], reverse=True)
            result["core_memories"] = [memory[0]["content"] for memory, _ in scored_core[:self.max_core]]
            
            # Score episodic memories by keyword matches
            scored_episodic = []
            for memory in self.episodic_memories:
                content = memory.get("content", "")
                memory_words = set(content.lower().split())
                
                # Calculate keyword match score
                overlap = query_words.intersection(memory_words)
                if overlap:
                    score = len(overlap) / len(query_words)
                    scored_episodic.append((memory, score))
            
            # Sort and take top N episodic memories
            scored_episodic.sort(key=lambda x: x[1], reverse=True)
            result["episodic_memories"] = [memory[0]["content"] for memory, _ in scored_episodic[:self.max_episodic]]
            
            # Score archival memories by keyword matches
            scored_archival = []
            for memory in self.archival_memories:
                content = memory.get("content", "")
                memory_words = set(content.lower().split())
                
                # Calculate keyword match score
                overlap = query_words.intersection(memory_words)
                if overlap:
                    score = len(overlap) / len(query_words)
                    scored_archival.append((memory, score))
            
            # Sort and take top N archival memories
            scored_archival.sort(key=lambda x: x[1], reverse=True)
            result["archival_memories"] = [memory[0]["content"] for memory, _ in scored_archival[:self.max_archival]]
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving memories by keywords: {e}")
            return {
                "core_memories": [],
                "episodic_memories": [],
                "archival_memories": []
            }
    
    def enhance_prompt(self, query: str, system_prompt: str, conversation_history: List = None, channel: str = "text", user_id: str = None) -> str:
        """
        Enhance the system prompt with memory context and conversation history.
        
        Args:
            query: User query
            system_prompt: System prompt
            conversation_history: Recent conversation history
            channel: Communication channel (text, email, etc.)
            user_id: User ID for retrieving user-specific memories
            
        Returns:
            str: Enhanced system prompt
        """
        try:
            # Define simple greetings that don't need complex RAG
            simple_greetings = {"hi", "hello", "hey", "yo", "sup", "what's up", "whats up", "hiya", "howdy"}
            
            # Check if this is a simple greeting or very short query
            is_simple_query = query.lower().strip() in simple_greetings or len(query.split()) <= 3
            
            # For simple queries, use minimal context
            if is_simple_query:
                logging.info("Detected simple query, using minimal context")
                # Preserve email formatting instructions for email channel
                if channel == "email":
                    enhanced_prompt = f"{system_prompt}\n\nThe user has sent a simple greeting: '{query}'. Respond naturally with a friendly greeting without adding unrelated information or asking unexpected questions. Keep your response short and casual, similar to how a person would respond to a greeting. Remember to format your response as an email with appropriate greeting and signature."
                else:
                    enhanced_prompt = f"{system_prompt}\n\nThe user has sent a simple greeting: '{query}'. Respond naturally with a friendly greeting without adding unrelated information or asking unexpected questions. Keep your response short and casual, similar to how a person would respond to a greeting."
                return enhanced_prompt
            
            # MODIFIED: Always use embedding-based RAG with Pinecone for all queries
            logging.info(f"{channel} message processing")
            
            # Get relevant memories using embedding-based RAG
            logging.info("Using embedding-based RAG for all queries")
            memory_context = self.retrieve_relevant_memories(query)
            
            # Format memories naturally
            formatted_memories = self._format_memories_naturally(memory_context)
            
            # Enhance the prompt with memory context
            if formatted_memories:
                enhanced_prompt = system_prompt + "\n\n" + formatted_memories
                logging.info("Enhanced prompt with memory context")
            else:
                enhanced_prompt = system_prompt
                logging.info("No relevant memories found, using original prompt")
            
            # Add guidance based on message intent
            query_intent = self._analyze_message_intent(query)
            if query_intent.get('is_question'):
                enhanced_prompt += "\n\nThe current message is a question, so provide a helpful and informative response based on your knowledge and memories."
            elif query_intent.get('is_greeting'):
                enhanced_prompt += "\n\nThe current message is a greeting, so respond in a friendly and casual way without adding unrelated information."
            elif query_intent.get('is_opinion'):
                enhanced_prompt += "\n\nThe current message is asking for your opinion, so provide a thoughtful response that reflects your personality."
            
            # Add guidance for emotional tone
            if query_intent.get('emotional_tone') == 'positive':
                enhanced_prompt += "\nThe message has a positive tone, so match that in your response."
            elif query_intent.get('emotional_tone') == 'negative':
                enhanced_prompt += "\nThe message has a negative tone, so be empathetic in your response."
            
            # Add context about the current conversation topics
            query_topics = self._extract_topics(query)
            if query_topics:
                enhanced_prompt += f"\n\nThe current conversation is about: {', '.join(query_topics)}"
            
            # Add channel-specific formatting instructions
            if channel == "email":
                enhanced_prompt += "\n\nIMPORTANT: Format your response as an email with an appropriate greeting and signature. Make sure to include a greeting at the beginning (like 'Hi [Name],' or 'Hello,') and a signature at the end (like 'Best regards,' or 'Cheers,')."
            
            logger.info("Enhanced prompt with memory context and intent guidance")
            return enhanced_prompt
        except Exception as e:
            logger.error(f"Error enhancing prompt with memory: {e}")
            # Return original system prompt if there's an error
            return system_prompt
    
    def _format_memories_naturally(self, memories: Dict) -> str:
        """
        Format memories in a natural way for inclusion in the prompt.
        
        Args:
            memories: Dictionary of memories by category
            
        Returns:
            str: Formatted memories
        """
        # Start with a header that frames these as the AI's knowledge and memories
        formatted_memories = "My Personal Knowledge and Memories:\n\n"
        
        # Add core memories as "Things I know"
        if memories.get("core_memories"):
            formatted_memories += "About Me:\n"
            for memory in memories["core_memories"]:
                # Format as "I know that..." statements
                formatted_memories += f"- I know that {memory}\n"
            formatted_memories += "\n"
        
        # Add episodic memories with temporal context
        if memories.get("episodic_memories"):
            formatted_memories += "My Recent Experiences and Plans:\n"
            
            # Separate future and past memories
            future_memories = []
            past_memories = []
            
            for memory in memories["episodic_memories"]:
                # Check if this is about a future event
                is_future = False
                
                # Look for future indicators in the memory
                future_indicators = ["Future", "Planning", "Will", "Going to", "Scheduled", "Upcoming", "Next"]
                for indicator in future_indicators:
                    if indicator.lower() in memory.lower():
                        is_future = True
                        break
                
                # Add to appropriate list
                if is_future:
                    future_memories.append(memory)
                else:
                    past_memories.append(memory)
            
            # Add past memories first
            for memory in past_memories:
                formatted_memories += f"- I recall that {memory}\n"
            
            # Add future memories
            for memory in future_memories:
                formatted_memories += f"- I'm planning that {memory}\n"
                
            formatted_memories += "\n"
        
        # Add archival memories as "Things I remember"
        if memories.get("archival_memories"):
            formatted_memories += "Additional Things I Remember:\n"
            for memory in memories["archival_memories"]:
                formatted_memories += f"- I remember that {memory}\n"
            formatted_memories += "\n"
        
        # Add a natural approach to memory prioritization
        formatted_memories += """
These memories represent my actual experiences, knowledge, and plans. When responding, I should naturally incorporate relevant memories into my answers. If I'm unsure about something, I can acknowledge that rather than making up information.
"""
        
        return formatted_memories
    
    def update_from_conversation(self, user_message: str, ai_response: str) -> None:
        """
        Update memory with a new conversation interaction.
        
        Args:
            user_message: User message
            ai_response: AI response
        """
        # Add the interaction to episodic memory
        interaction = f"User: {user_message}\nMe: {ai_response}"
        self.add_episodic_memory(interaction)
        
        # Extract potential core memories from the interaction
        self._extract_potential_core_memories(user_message, ai_response)
    
    def _extract_potential_core_memories(self, user_message: str, ai_response: str) -> None:
        """
        Extract potential core memories from the interaction.
        This looks for personal information in the AI's responses.
        
        Args:
            user_message: User message
            ai_response: AI response
        """
        # Check if the response contains personal information
        personal_indicators = [
            "I am", "I'm", "my name is", "I live in", "I work", 
            "my job", "my hobby", "I enjoy", "I like", "I love"
        ]
        
        # Extract sentences from the response
        sentences = ai_response.split(".")
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if the sentence contains personal information
            if any(indicator in sentence.lower() for indicator in personal_indicators):
                # Add to core memory if it seems like a personal fact
                self.add_core_memory(sentence)

    def _get_relevant_memories(self, query):
        """
        Get memories relevant to the query.
        
        Args:
            query: The user query
            
        Returns:
            dict: Relevant memories from different categories
        """
        try:
            # Analyze query intent and topics
            query_intent = self._analyze_message_intent(query)
            query_topics = self._extract_topics(query)
            
            logger.info(f"Getting relevant memories for query: {query[:20]}...")
            logger.info(f"Query intent: {query_intent}, topics: {query_topics}")
            
            # For simple greetings, return minimal or no memories to prevent hallucinations
            simple_greetings = ["hello", "hi", "hey", "what's up", "sup", "yo", "hola", "howdy"]
            if query.lower().strip() in simple_greetings:
                logger.info("Detected simple greeting, returning minimal memories")
                return {
                    "core_memories": [],
                    "episodic_memories": [],
                    "archival_memories": []
                }
            
            result = {
                "core_memories": [],
                "episodic_memories": [],
                "archival_memories": []
            }
            
            # Get memory file path
            memory_file = self.memory_path
            logger.info(f"Using memory file: {memory_file}")
            
            if not os.path.exists(memory_file):
                logger.warning(f"Memory file not found: {memory_file}")
                return result
                
            # Load memory if not already loaded
            if not self.core_memories:
                self.load_memory()
                
            # Log available memories
            core_count = len(self.core_memories)
            episodic_count = len(self.episodic_memories)
            archival_count = len(self.archival_memories)
            logger.info(f"Available memories: {core_count} core, {episodic_count} episodic, {archival_count} archival")
            
            # Helper function to get embeddings for a single text
            def get_embedding(self, text):
                try:
                    # Import here to avoid circular imports
                    import openai
                    from openai import OpenAI
                    
                    try:
                        # Try with new OpenAI client API (>=1.0.0)
                        client = OpenAI()
                        response = client.embeddings.create(
                            model="text-embedding-3-small",
                            input=text
                        )
                        return response.data[0].embedding
                    except (ImportError, AttributeError):
                        # Fall back to older OpenAI API (<1.0.0)
                        openai.api_key = os.getenv("OPENAI_API_KEY")
                        response = openai.Embedding.create(
                            model="text-embedding-3-small",
                            input=text
                        )
                        return response["data"][0]["embedding"]
                except Exception as e:
                    logger.error(f"Error getting embedding: {e}")
                    return None
            
            # Helper function to get embeddings for multiple texts in a batch
            def get_embeddings_batch(self, texts):
                try:
                    # Import here to avoid circular imports
                    import openai
                    from openai import OpenAI
                    
                    try:
                        # Try with new OpenAI client API (>=1.0.0)
                        client = OpenAI()
                        response = client.embeddings.create(
                            model="text-embedding-3-small",
                            input=texts
                        )
                        return [item.embedding for item in response.data]
                    except (ImportError, AttributeError):
                        # Fall back to older OpenAI API (<1.0.0)
                        openai.api_key = os.getenv("OPENAI_API_KEY")
                        response = openai.Embedding.create(
                            model="text-embedding-3-small",
                            input=texts
                        )
                        return [item["embedding"] for item in response["data"]]
                except Exception as e:
                    logger.error(f"Error getting batch embeddings: {e}")
                    return [None] * len(texts)
            
            # Get embedding for the query
            query_embedding = get_embedding(self, query)
            
            # If embedding fails, fall back to keyword matching
            if not query_embedding:
                logger.warning("Embedding failed, falling back to keyword matching")
                return {
                    "core_memories": self._get_keyword_matches(query, self.core_memories, self.max_core),
                    "episodic_memories": self._get_keyword_matches(query, self.episodic_memories, self.max_episodic),
                    "archival_memories": []
                }
            
            # Get current time for updating access times
            now = dt.now().isoformat()
            
            # Helper function for cosine similarity
            def cosine_similarity(embedding1, embedding2):
                dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
                magnitude1 = sum(a * a for a in embedding1) ** 0.5
                magnitude2 = sum(b * b for b in embedding2) ** 0.5
                return dot_product / (magnitude1 * magnitude2) if magnitude1 * magnitude2 > 0 else 0
            
            # Process core memories with multi-factor scoring
            core_memories = []
            for memory in self.core_memories:
                content = memory.get("content", "")
                memory_embedding = get_embedding(self, content)
                
                if memory_embedding:
                    # Convert to numpy arrays if they're lists
                    if isinstance(query_embedding, list):
                        query_embedding = np.array(query_embedding)
                    if isinstance(memory_embedding, list):
                        memory_embedding = np.array(memory_embedding)
                        
                    # Calculate base similarity score
                    query_embedding_2d = query_embedding.reshape(1, -1)
                    memory_embedding_2d = memory_embedding.reshape(1, -1)
                    embedding_similarity = cosine_similarity(query_embedding_2d, memory_embedding_2d)[0][0]
                    
                    # Initialize additional score components
                    intent_match_score = 0
                    topic_match_score = 0
                    keyword_match_score = 0
                    
                    # Intent matching (using existing method)
                    query_intent = self._analyze_message_intent(query)
                    memory_intent = self._analyze_message_intent(content)
                    
                    if query_intent.get('is_question') and memory_intent.get('is_question'):
                        intent_match_score = 0.1
                    elif query_intent.get('is_greeting') and memory_intent.get('is_greeting'):
                        intent_match_score = 0.1
                    
                    # Topic matching
                    memory_topics = self._extract_topics(content)
                    if query_topics and memory_topics:
                        common_topics = set(query_topics).intersection(set(memory_topics))
                        topic_match_score = len(common_topics) * 0.1
                    
                    # Keyword matching
                    query_words = set(query.lower().split())
                    memory_words = set(content.lower().split())
                    common_words = query_words.intersection(memory_words)
                    if common_words:
                        keyword_match_score = len(common_words) / len(query_words) * 0.1
                    
                    # Calculate final composite score
                    final_score = embedding_similarity + intent_match_score + topic_match_score + keyword_match_score
                    
                    # Apply minimum threshold
                    min_score_threshold = 0.3
                    
                    # Add memory with final score if it meets the threshold
                    if final_score > min_score_threshold or len(core_memories) < self.max_core // 2:
                        core_memories.append({
                            "content": content,
                            "similarity": final_score,
                            "id": memory.get("id"),
                            "score_components": {
                                "embedding_similarity": embedding_similarity,
                                "intent_match": intent_match_score,
                                "topic_match": topic_match_score,
                                "keyword_match": keyword_match_score
                            }
                        })
            
            # Sort core memories by similarity and take top N
            core_memories.sort(key=lambda x: x["similarity"], reverse=True)
            core_memories = core_memories[:self.max_core]
            
            # Log score components for debugging
            for i, memory in enumerate(core_memories):
                components = memory.get("score_components", {})
                logger.info(f"Core memory {i+1} score: {memory['similarity']:.2f} (Embedding: {components.get('embedding_similarity', 0):.2f}, "
                          f"Intent: {components.get('intent_match', 0):.2f}, Topic: {components.get('topic_match', 0):.2f}, "
                          f"Keyword: {components.get('keyword_match', 0):.2f})")
            
            # Extract just the content for the result
            result["core_memories"] = [memory["content"] for memory in core_memories]
            
            # Update access time for returned core memories
            for memory in core_memories:
                memory_id = memory.get("id")
                if memory_id:
                    self._update_memory_access_time(memory_id, now)
            
            # Process episodic memories with multi-factor scoring (similar approach)
            episodic_memories = []
            for memory in self.episodic_memories:
                content = memory.get("content", "")
                memory_embedding = get_embedding(self, content)
                
                if memory_embedding:
                    # Convert to numpy arrays if they're lists
                    if isinstance(query_embedding, list):
                        query_embedding = np.array(query_embedding)
                    if isinstance(memory_embedding, list):
                        memory_embedding = np.array(memory_embedding)
                        
                    # Calculate base similarity score
                    query_embedding_2d = query_embedding.reshape(1, -1)
                    memory_embedding_2d = memory_embedding.reshape(1, -1)
                    embedding_similarity = cosine_similarity(query_embedding_2d, memory_embedding_2d)[0][0]
                    
                    # Initialize additional score components
                    intent_match_score = 0
                    topic_match_score = 0
                    keyword_match_score = 0
                    
                    # Intent matching (using existing method)
                    query_intent = self._analyze_message_intent(query)
                    memory_intent = self._analyze_message_intent(content)
                    
                    if query_intent.get('is_question') and memory_intent.get('is_question'):
                        intent_match_score = 0.1
                    elif query_intent.get('is_greeting') and memory_intent.get('is_greeting'):
                        intent_match_score = 0.1
                    
                    # Topic matching
                    memory_topics = self._extract_topics(content)
                    if query_topics and memory_topics:
                        common_topics = set(query_topics).intersection(set(memory_topics))
                        topic_match_score = len(common_topics) * 0.1
                    
                    # Keyword matching
                    query_words = set(query.lower().split())
                    memory_words = set(content.lower().split())
                    common_words = query_words.intersection(memory_words)
                    if common_words:
                        keyword_match_score = len(common_words) / len(query_words) * 0.1
                    
                    # Calculate final composite score
                    final_score = embedding_similarity + intent_match_score + topic_match_score + keyword_match_score
                    
                    # Apply stricter threshold for episodic memories
                    min_score_threshold = 0.35
                    
                    # Add memory with final score if it meets the threshold
                    if final_score > min_score_threshold:
                        episodic_memories.append({
                            "content": content,
                            "similarity": final_score,
                            "id": memory.get("id"),
                            "score_components": {
                                "embedding_similarity": embedding_similarity,
                                "intent_match": intent_match_score,
                                "topic_match": topic_match_score,
                                "keyword_match": keyword_match_score
                            }
                        })
            
            # Sort episodic memories by similarity and take top N
            episodic_memories.sort(key=lambda x: x["similarity"], reverse=True)
            episodic_memories = episodic_memories[:self.max_episodic]
            
            # Log score components for debugging
            for i, memory in enumerate(episodic_memories):
                components = memory.get("score_components", {})
                logger.info(f"Episodic memory {i+1} score: {memory['similarity']:.2f} (Embedding: {components.get('embedding_similarity', 0):.2f}, "
                          f"Intent: {components.get('intent_match', 0):.2f}, Topic: {components.get('topic_match', 0):.2f}, "
                          f"Keyword: {components.get('keyword_match', 0):.2f})")
            
            # Extract just the content for the result
            result["episodic_memories"] = [memory["content"] for memory in episodic_memories]
            
            # Update access time for returned episodic memories
            for memory in episodic_memories:
                memory_id = memory.get("id")
                if memory_id:
                    self._update_memory_access_time(memory_id, now)
            
            # Process archival memories with multi-factor scoring (similar approach)
            archival_memories = []
            for memory in self.archival_memories:
                content = memory.get("content", "")
                memory_embedding = get_embedding(self, content)
                
                if memory_embedding:
                    # Convert to numpy arrays if they're lists
                    if isinstance(query_embedding, list):
                        query_embedding = np.array(query_embedding)
                    if isinstance(memory_embedding, list):
                        memory_embedding = np.array(memory_embedding)
                        
                    # Calculate similarity score
                    query_embedding_2d = query_embedding.reshape(1, -1)
                    memory_embedding_2d = memory_embedding.reshape(1, -1)
                    similarity = cosine_similarity(query_embedding_2d, memory_embedding_2d)[0][0]
                    
                    # Add memory with similarity score if relevant
                    if similarity > 0.4:  # Higher threshold for archival memories
                        archival_memories.append({
                            "content": content,
                            "similarity": similarity,
                            "id": memory.get("id")
                        })
            
            # Sort archival memories by similarity and take top N
            archival_memories.sort(key=lambda x: x["similarity"], reverse=True)
            archival_memories = archival_memories[:self.max_archival]
            
            # Extract just the content for the result
            result["archival_memories"] = [memory["content"] for memory in archival_memories]
            
            # Update access time for returned archival memories
            for memory in archival_memories:
                memory_id = memory.get("id")
                if memory_id:
                    self._update_memory_access_time(memory_id, now)
            
            # Log the number of memories retrieved
            logger.info(f"Retrieved {len(result['core_memories'])} core, {len(result['episodic_memories'])} episodic, and {len(result['archival_memories'])} archival memories")
            
            return result
        except Exception as e:
            logger.error(f"Error getting relevant memories: {e}")
            return {
                "core_memories": [],
                "episodic_memories": [],
                "archival_memories": []
            }
    
    def _analyze_message_intent(self, message):
        """
        Analyze the intent of a message.
        
        Args:
            message: Message to analyze
            
        Returns:
            dict: Intent analysis results
        """
        # Initialize intent analysis
        intent = {
            "is_question": False,
            "is_greeting": False,
            "is_opinion": False,
            "emotional_tone": "neutral"
        }
        
        # Convert to lowercase for analysis
        message_lower = message.lower()
        
        # Check if it's a question
        if "?" in message or message_lower.startswith(("what", "who", "when", "where", "why", "how", "can", "could", "would", "should", "is", "are", "do", "does")):
            intent["is_question"] = True
            
        # Check if it's a greeting
        greeting_phrases = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "what's up", "howdy"]
        if any(phrase in message_lower for phrase in greeting_phrases):
            intent["is_greeting"] = True
            
        # Check if it's an opinion
        opinion_phrases = ["i think", "i believe", "in my opinion", "i feel", "i prefer", "i like", "i don't like", "i hate", "i love"]
        if any(phrase in message_lower for phrase in opinion_phrases):
            intent["is_opinion"] = True
            
        # Analyze emotional tone
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "happy", "love", "like", "enjoy", "positive"]
        negative_words = ["bad", "terrible", "awful", "horrible", "sad", "hate", "dislike", "negative", "angry", "upset"]
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            intent["emotional_tone"] = "positive"
        elif negative_count > positive_count:
            intent["emotional_tone"] = "negative"
            
        return intent
        
    def _extract_topics(self, text):
        """
        Extract topics from text.
        
        Args:
            text: The text to extract topics from
            
        Returns:
            list: Topics extracted from the text
        """
        # Define topic categories and their associated keywords
        topic_categories = {
            'work': ['work', 'job', 'career', 'company', 'startup', 'business', 'office', 'project', 'team', 'meeting'],
            'technology': ['tech', 'ai', 'code', 'programming', 'software', 'app', 'computer', 'algorithm', 'data', 'website'],
            'personal': ['family', 'friend', 'relationship', 'feel', 'life', 'hobby', 'weekend', 'home', 'personal', 'health'],
            'education': ['school', 'college', 'university', 'class', 'course', 'learn', 'study', 'education', 'student', 'teacher'],
            'entertainment': ['movie', 'show', 'music', 'game', 'book', 'play', 'watch', 'read', 'listen', 'entertainment'],
            'travel': ['travel', 'trip', 'vacation', 'visit', 'country', 'city', 'place', 'flight', 'hotel', 'destination']
        }
        
        # Convert to lowercase for analysis
        text_lower = text.lower()
        
        # Identify topics based on keyword presence
        detected_topics = []
        for topic, keywords in topic_categories.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_topics.append(topic)
                
        return detected_topics

    def calculate_topic_match(self, text1, text2):
        """
        Calculate the topic match score between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            float: Topic match score between 0 and 1
        """
        # Extract topics from both texts
        topics1 = self._extract_topics(text1)
        topics2 = self._extract_topics(text2)
        
        # If either has no topics, return 0
        if not topics1 or not topics2:
            return 0.0
        
        # Calculate the overlap
        common_topics = set(topics1).intersection(set(topics2))
        
        # Calculate the Jaccard similarity
        if len(common_topics) == 0:
            return 0.0
        
        return len(common_topics) / len(set(topics1).union(set(topics2)))

    def calculate_keyword_match(self, text1, text2):
        """
        Calculate the keyword match score between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            float: Keyword match score between 0 and 1
        """
        # Simple word overlap approach
        if not isinstance(text1, str) or not isinstance(text2, str):
            return 0.0
            
        # Tokenize and clean
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were", 
                     "in", "on", "at", "to", "for", "with", "by", "about", "against", "between", "into", "through", 
                     "during", "before", "after", "above", "below", "from", "up", "down", "of", "off", "over", "under"}
        
        words1 = words1.difference(stop_words)
        words2 = words2.difference(stop_words)
        
        # Calculate overlap
        if not words1 or not words2:
            return 0.0
        
        common_words = words1.intersection(words2)
        
        # Jaccard similarity
        return len(common_words) / len(words1.union(words2))

# Initialize the memory-enhanced RAG system with default user
# This will be replaced with user-specific instances in the app
memory_rag = MemoryEnhancedRAG(user_id="default")

# Dictionary to store user-specific memory RAG instances
user_memory_rags = {}

def enhance_prompt_with_memory(system_prompt: str, user_message: str, conversation_history: List = None, user_id: str = "default", channel: str = "text") -> str:
    """
    Enhance the system prompt with memory context.
    This function can be used as a drop-in replacement for enhance_prompt_with_rag.
    
    Args:
        system_prompt: Original system prompt
        user_message: Current user message
        conversation_history: Recent conversation history
        user_id: User identifier for user-specific memories
        channel: Communication channel (text, email, etc.)
        
    Returns:
        str: Enhanced system prompt
    """
    # Get or create user-specific memory RAG instance
    if user_id != "default" and user_id not in user_memory_rags:
        logger.info(f"Creating new memory RAG instance for user: {user_id}")
        user_memory_rags[user_id] = MemoryEnhancedRAG(user_id=user_id)
    
    # Use user-specific memory RAG if available, otherwise use default
    if user_id != "default" and user_id in user_memory_rags:
        return user_memory_rags[user_id].enhance_prompt(user_message, system_prompt, conversation_history, channel, user_id)
    else:
        return memory_rag.enhance_prompt(user_message, system_prompt, conversation_history, channel, user_id)

def update_memory_from_conversation(user_message: str, ai_response: str, user_id: str = "default") -> None:
    """
    Update memory with a new conversation interaction.
    This should be called after generating a response.
    
    Args:
        user_message: User message
        ai_response: AI response
        user_id: User identifier for user-specific memories
    """
    # Get or create user-specific memory RAG instance
    if user_id != "default" and user_id not in user_memory_rags:
        logger.info(f"Creating new memory RAG instance for user: {user_id}")
        user_memory_rags[user_id] = MemoryEnhancedRAG(user_id=user_id)
    
    # Use user-specific memory RAG if available, otherwise use default
    if user_id != "default" and user_id in user_memory_rags:
        user_memory_rags[user_id].update_from_conversation(user_message, ai_response)
    else:
        memory_rag.update_from_conversation(user_message, ai_response)

def add_fact_to_memory(fact: str, memory_type: str = "core", user_id: str = "default") -> bool:
    """
    Add a fact to memory.
    
    Args:
        fact: Fact to add to memory
        memory_type: Type of memory (core, episodic, archival)
        user_id: User identifier for user-specific memories
        
    Returns:
        bool: Success status
    """
    # Get or create user-specific memory RAG instance
    if user_id != "default" and user_id not in user_memory_rags:
        logger.info(f"Creating new memory RAG instance for user: {user_id}")
        user_memory_rags[user_id] = MemoryEnhancedRAG(user_id=user_id)
    
    # Use user-specific memory RAG if available, otherwise use default
    memory_instance = user_memory_rags.get(user_id, memory_rag) if user_id != "default" else memory_rag
    
    if memory_type == "core":
        return memory_instance.add_core_memory(fact)
    elif memory_type == "episodic":
        return memory_instance.add_episodic_memory(fact)
    elif memory_type == "archival":
        return memory_instance.add_archival_memory(fact)
    else:
        logger.error(f"Invalid memory type: {memory_type}")
        return False

# Monkey patch the original enhance_prompt_with_rag function
# This will replace it with our memory-enhanced version
import rag.app_integration
import rag.enhanced_rag_integration

# First, save the original function before it gets patched by enhanced_rag_integration
original_enhance_prompt = rag.app_integration.enhance_prompt_with_rag

# Make sure our memory-enhanced version is the one that gets used
# This needs to happen AFTER enhanced_rag_integration has done its patching
def initialize_memory_integration():
    """Initialize memory integration by patching the enhance_prompt_with_rag function"""
    logger.info("Initializing memory integration - patching enhance_prompt_with_rag")
    rag.app_integration.enhance_prompt_with_rag = enhance_prompt_with_memory
    return True

# Call this function to ensure our patch takes effect
initialize_memory_integration()
