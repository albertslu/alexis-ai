"""
Letta-Enhanced Response Generator for AI Clone

This module extends the HybridResponseGenerator with Letta-like memory capabilities.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import the original HybridResponseGenerator
from utils.hybrid_response import HybridResponseGenerator
from rag.rag_system import MessageRAG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LettaMemoryManager:
    """
    Memory manager that implements Letta-like memory capabilities.
    This provides a local implementation of key Letta features without requiring the Letta server.
    """
    
    def __init__(self, user_id: str = "default"):
        """
        Initialize the memory manager.
        
        Args:
            user_id: Identifier for the user
        """
        self.user_id = user_id
        self.memory_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data',
            f'letta_memory_{user_id}.json'
        )
        
        # Initialize memory structure
        self.memory = self._load_memory()
    
    def _load_memory(self) -> Dict:
        """Load memory from file or create new memory structure"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            else:
                # Create default memory structure
                default_memory = {
                    "core_memory": [],      # Essential facts that are always in context
                    "episodic_memory": [],  # Specific conversations and interactions
                    "archival_memory": [],  # Long-term storage for less frequently used information
                    "last_updated": datetime.now().isoformat()
                }
                self._save_memory(default_memory)
                return default_memory
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            # Return empty memory structure
            return {
                "core_memory": [],
                "episodic_memory": [],
                "archival_memory": [],
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_memory(self, memory: Dict = None) -> bool:
        """Save memory to file"""
        try:
            if memory is None:
                memory = self.memory
            
            # Update last_updated timestamp
            memory["last_updated"] = datetime.now().isoformat()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return False
    
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
            for memory in self.memory["core_memory"]:
                if self._is_similar(memory["content"], content):
                    # Update existing memory
                    memory["content"] = content
                    memory["last_accessed"] = datetime.now().isoformat()
                    self._save_memory()
                    return True
            
            # Add new memory
            self.memory["core_memory"].append({
                "id": str(uuid.uuid4()),
                "content": content,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            })
            
            self._save_memory()
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
            self.memory["episodic_memory"].append({
                "id": str(uuid.uuid4()),
                "content": content,
                "context": context,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            })
            
            # Limit episodic memory to 100 items
            if len(self.memory["episodic_memory"]) > 100:
                # Sort by last_accessed and remove oldest
                self.memory["episodic_memory"].sort(
                    key=lambda x: x["last_accessed"]
                )
                # Move oldest to archival memory
                oldest = self.memory["episodic_memory"].pop(0)
                self.memory["archival_memory"].append(oldest)
            
            self._save_memory()
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
            self.memory["archival_memory"].append({
                "id": str(uuid.uuid4()),
                "content": content,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            })
            
            self._save_memory()
            return True
        except Exception as e:
            logger.error(f"Error adding archival memory: {e}")
            return False
    
    def get_relevant_memories(self, query: str, max_core: int = 5, max_episodic: int = 3, max_archival: int = 2) -> Dict:
        """
        Get memories relevant to the current query.
        
        Args:
            query: Query to find relevant memories
            max_core: Maximum number of core memories to return
            max_episodic: Maximum number of episodic memories to return
            max_archival: Maximum number of archival memories to return
            
        Returns:
            Dict: Dictionary of relevant memories
        """
        try:
            # Update access time for all returned memories
            now = datetime.now().isoformat()
            
            # Get all core memories (these are always included)
            core_memories = self.memory["core_memory"][:max_core]
            for memory in core_memories:
                memory["last_accessed"] = now
            
            # Find relevant episodic memories
            episodic_memories = self._find_relevant_memories(
                self.memory["episodic_memory"],
                query,
                max_episodic
            )
            
            # Find relevant archival memories
            archival_memories = self._find_relevant_memories(
                self.memory["archival_memory"],
                query,
                max_archival
            )
            
            # Save updated access times
            self._save_memory()
            
            return {
                "core_memories": [m["content"] for m in core_memories],
                "episodic_memories": [m["content"] for m in episodic_memories],
                "archival_memories": [m["content"] for m in archival_memories]
            }
        except Exception as e:
            logger.error(f"Error getting relevant memories: {e}")
            return {
                "core_memories": [],
                "episodic_memories": [],
                "archival_memories": []
            }
    
    def _find_relevant_memories(self, memories: List[Dict], query: str, max_count: int) -> List[Dict]:
        """
        Find memories relevant to the query using simple keyword matching.
        In a production system, this would use embeddings and semantic search.
        
        Args:
            memories: List of memories to search
            query: Query to find relevant memories
            max_count: Maximum number of memories to return
            
        Returns:
            List[Dict]: List of relevant memories
        """
        # Simple relevance scoring based on keyword matching
        query_words = set(query.lower().split())
        
        scored_memories = []
        for memory in memories:
            content = memory["content"].lower()
            score = sum(1 for word in query_words if word in content)
            if score > 0:
                scored_memories.append((score, memory))
        
        # Sort by relevance score (descending)
        scored_memories.sort(reverse=True)
        
        # Update access time for returned memories
        now = datetime.now().isoformat()
        relevant_memories = []
        for _, memory in scored_memories[:max_count]:
            memory["last_accessed"] = now
            relevant_memories.append(memory)
        
        return relevant_memories
    
    def _is_similar(self, text1: str, text2: str) -> bool:
        """
        Check if two texts are similar.
        This is a simple implementation that could be improved with embeddings.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            bool: True if texts are similar
        """
        # Convert to lowercase and split into words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return False
        
        similarity = intersection / union
        return similarity > 0.5  # Threshold for similarity


class LettaEnhancedGenerator(HybridResponseGenerator):
    """
    Enhanced response generator that combines HybridResponseGenerator with Letta-like memory.
    """
    
    def __init__(self, user_id: str = "default"):
        """
        Initialize the Letta-enhanced generator.
        
        Args:
            user_id: Identifier for the user/agent
        """
        # Initialize the parent class
        super().__init__(user_id)
        
        # Initialize the memory manager
        self.memory_manager = LettaMemoryManager(user_id)
        
        logger.info(f"Initialized LettaEnhancedGenerator for user {user_id}")
    
    def generate_response(self, user_message, conversation_id=None, enhanced_prompt=None, channel=None, metadata=None):
        """
        Generate a response using the hybrid approach with Letta-like memory enhancement.
        
        Args:
            user_message: The user's message
            conversation_id: Optional conversation ID for context
            enhanced_prompt: Optional pre-enhanced system prompt from RAG
            channel: Optional communication channel (text, email, etc.)
            metadata: Optional metadata about the message (e.g., email subject)
            
        Returns:
            str: Generated response
        """
        # Get relevant memories for the current message
        relevant_memories = self.memory_manager.get_relevant_memories(user_message)
        
        # Enhance the prompt with memory context
        memory_context = self._prepare_memory_context(relevant_memories)
        
        # If enhanced_prompt is provided, append memory context to it
        if enhanced_prompt:
            enhanced_prompt = f"{enhanced_prompt}\n\n{memory_context}"
        else:
            # Get identity facts from state manager
            identity_facts = self.agent_state.get_identity_facts(min_confidence=0.6)
            
            # Prepare system message with identity information
            base_system_message = self._prepare_system_message(identity_facts, channel)
            
            # Apply channel-specific instructions to system message
            system_message = self.channel_processor.prepare_channel_specific_prompt(
                channel, base_system_message
            )
            
            # Append memory context to system message
            enhanced_prompt = f"{system_message}\n\n{memory_context}"
        
        # Generate response using the parent class method
        response = super().generate_response(
            user_message, 
            conversation_id, 
            enhanced_prompt, 
            channel, 
            metadata
        )
        
        # Add the interaction to episodic memory
        self._update_memory(user_message, response)
        
        return response
    
    def _prepare_memory_context(self, memories: Dict) -> str:
        """
        Prepare memory context for inclusion in the prompt.
        
        Args:
            memories: Dictionary of relevant memories
            
        Returns:
            str: Formatted memory context
        """
        memory_sections = []
        
        # Add core memories
        if memories["core_memories"]:
            core_memory_text = "\n".join([f"- {memory}" for memory in memories["core_memories"]])
            memory_sections.append(f"CORE FACTS ABOUT ME:\n{core_memory_text}")
        
        # Add episodic memories
        if memories["episodic_memories"]:
            episodic_memory_text = "\n".join([f"- {memory}" for memory in memories["episodic_memories"]])
            memory_sections.append(f"RELEVANT PAST INTERACTIONS:\n{episodic_memory_text}")
        
        # Add archival memories
        if memories["archival_memories"]:
            archival_memory_text = "\n".join([f"- {memory}" for memory in memories["archival_memories"]])
            memory_sections.append(f"ADDITIONAL CONTEXT:\n{archival_memory_text}")
        
        # Combine all memory sections
        if memory_sections:
            return "MEMORY CONTEXT:\n" + "\n\n".join(memory_sections)
        else:
            return ""
    
    def _update_memory(self, user_message: str, response: str) -> None:
        """
        Update memory with the current interaction.
        
        Args:
            user_message: User message
            response: Generated response
        """
        # Add the interaction to episodic memory
        interaction = f"User: {user_message}\nMe: {response}"
        self.memory_manager.add_episodic_memory(interaction)
        
        # Extract potential core memories from the interaction
        self._extract_potential_core_memories(user_message, response)
    
    def _extract_potential_core_memories(self, user_message: str, response: str) -> None:
        """
        Extract potential core memories from the interaction.
        This is a simple implementation that could be improved with NLP.
        
        Args:
            user_message: User message
            response: Generated response
        """
        # Check if the response contains personal information
        personal_indicators = [
            "I am", "I'm", "my name is", "I live in", "I work", 
            "my job", "my hobby", "I enjoy", "I like", "I love"
        ]
        
        # Extract sentences from the response
        sentences = response.split(".")
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if the sentence contains personal information
            if any(indicator in sentence.lower() for indicator in personal_indicators):
                # Add to core memory if it seems like a personal fact
                self.memory_manager.add_core_memory(sentence)
    
    def add_fact_to_memory(self, fact: str, memory_type: str = "core") -> bool:
        """
        Add a fact to memory.
        
        Args:
            fact: Fact to add to memory
            memory_type: Type of memory (core, episodic, archival)
            
        Returns:
            bool: Success status
        """
        if memory_type == "core":
            return self.memory_manager.add_core_memory(fact)
        elif memory_type == "episodic":
            return self.memory_manager.add_episodic_memory(fact)
        elif memory_type == "archival":
            return self.memory_manager.add_archival_memory(fact)
        else:
            logger.error(f"Invalid memory type: {memory_type}")
            return False
