"""
Hybrid Letta Integration for AI Clone
This module integrates Letta's memory capabilities with the existing AI Clone architecture.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

# Import existing AI Clone components
from utils.hybrid_response import HybridResponseGenerator
from rag.rag_system import MessageRAG
from letta_integration import LettaIntegration

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HybridLettaSystem:
    """
    Hybrid system that combines Letta's memory capabilities with the existing
    AI Clone architecture (RAG + fine-tuned model).
    """
    
    def __init__(self, use_letta: bool = True, letta_url: str = "http://localhost:8283"):
        """
        Initialize the hybrid system.
        
        Args:
            use_letta: Whether to use Letta (can be disabled for fallback)
            letta_url: URL of the Letta server
        """
        self.use_letta = use_letta
        
        # Initialize existing components
        self.hybrid_generator = HybridResponseGenerator()
        self.message_rag = MessageRAG(clear_existing=True)
        
        # Initialize Letta integration if enabled
        if self.use_letta:
            try:
                self.letta = LettaIntegration(base_url=letta_url)
                logger.info("Letta integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Letta integration: {e}")
                self.use_letta = False
        
        # Load personal information
        try:
            with open("data/personal_info.json", "r") as f:
                self.personal_info = json.load(f)
        except FileNotFoundError:
            logger.warning("personal_info.json not found, using default values")
            self.personal_info = {
                "name": "Albert Lu",
                "hometown": "Austin",
                "occupation": "Entrepreneur"
            }
        
        # Cache for agent IDs
        self.agent_id_cache = {}
    
    def get_agent_id(self, user_id: str) -> Optional[str]:
        """Get or create a Letta agent for the user"""
        if not self.use_letta:
            return None
            
        # Check cache first
        if user_id in self.agent_id_cache:
            return self.agent_id_cache[user_id]
            
        # Get or create agent
        agent_id = self.letta.get_or_create_agent(user_id, self.personal_info)
        
        if agent_id:
            # Cache the agent ID
            self.agent_id_cache[user_id] = agent_id
            return agent_id
        
        return None
    
    def process_message(self, 
                        user_id: str, 
                        message_text: str, 
                        conversation_id: str = None,
                        channel: str = "text",
                        save_to_history: bool = True,
                        add_to_rag: bool = False,
                        metadata: Dict = None) -> Dict[str, Any]:
        """
        Process a message using the hybrid system.
        
        Args:
            user_id: Unique identifier for the user
            message_text: Message text to process
            conversation_id: Optional conversation ID for context
            channel: Communication channel (text or email)
            save_to_history: Whether to save the message to history
            add_to_rag: Whether to add the message to RAG
            metadata: Optional metadata about the message (e.g., email subject)
            
        Returns:
            Dictionary containing the response and metadata
        """
        # Initialize response dictionary
        response_dict = {
            "text": "",
            "source": "fallback",
            "success": False
        }
        
        # Try Letta first if enabled
        if self.use_letta:
            try:
                # Get or create agent
                agent_id = self.get_agent_id(user_id)
                
                if agent_id:
                    # Process message with Letta
                    letta_response = self.letta.process_message(agent_id, message_text, channel)
                    
                    if letta_response:
                        response_dict["text"] = letta_response
                        response_dict["source"] = "letta"
                        response_dict["success"] = True
                        
                        # If we got a successful response from Letta, also add this interaction
                        # to the RAG system for redundancy
                        if add_to_rag:
                            self._update_rag(user_id, message_text, letta_response, channel)
                        
                        return response_dict
            except Exception as e:
                logger.error(f"Error using Letta: {e}")
                # Fall back to existing system
        
        # Fall back to existing RAG + fine-tuned model system
        try:
            # Generate response using the existing system
            response_text = self.hybrid_generator.generate_response(
                user_message=message_text, 
                conversation_id=conversation_id,
                channel=channel,
                metadata=metadata
            )
            
            response_dict["text"] = response_text
            response_dict["source"] = "hybrid_rag"
            response_dict["success"] = True
            
            # Update RAG if requested
            if add_to_rag:
                self._update_rag(user_id, message_text, response_text, channel)
            
            # If Letta is enabled, also add this interaction to Letta's memory
            if self.use_letta:
                agent_id = self.get_agent_id(user_id)
                if agent_id:
                    # Add the interaction to Letta's memory
                    memory_text = f"User asked: {message_text}. I responded: {response_text}"
                    self.letta.add_memory(agent_id, memory_text, label="conversations")
            
            return response_dict
            
        except Exception as e:
            logger.error(f"Error in fallback system: {e}")
            response_dict["text"] = "I'm sorry, I couldn't process your message at this time."
            return response_dict
    
    def _update_rag(self, user_id: str, message_text: str, response_text: str, channel: str):
        """Update the RAG system with a new message pair"""
        try:
            # Add message pair to RAG
            self.message_rag.add_message_pair(
                user_message=message_text,
                assistant_message=response_text,
                channel=channel
            )
            logger.info("Added message pair to RAG system")
        except Exception as e:
            logger.error(f"Failed to update RAG: {e}")
    
    def add_fact_to_memory(self, user_id: str, fact: str) -> bool:
        """
        Add a new fact to the agent's memory.
        
        Args:
            user_id: Unique identifier for the user
            fact: Fact to add to memory
            
        Returns:
            True if successful, False otherwise
        """
        if not self.use_letta:
            logger.warning("Letta is disabled, cannot add fact to memory")
            return False
            
        try:
            agent_id = self.get_agent_id(user_id)
            if agent_id:
                return self.letta.add_memory(agent_id, fact, label="facts")
            return False
        except Exception as e:
            logger.error(f"Error adding fact to memory: {e}")
            return False

# Example usage
if __name__ == "__main__":
    # Initialize the hybrid system
    hybrid_system = HybridLettaSystem()
    
    # Process a test message
    response = hybrid_system.process_message(
        user_id="albert",
        message_text="What projects am I working on?",
        channel="text",
        add_to_rag=True
    )
    
    print(f"Response: {response['text']}")
    print(f"Source: {response['source']}")
    
    # Add a new fact to memory
    hybrid_system.add_fact_to_memory(
        user_id="albert",
        fact="I recently started learning to play the guitar."
    )
