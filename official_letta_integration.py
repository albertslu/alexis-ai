"""
Official Letta Integration for AI Clone
This module provides integration between the AI Clone system and Letta using the official SDK.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from letta_client import Letta

# Import existing AI Clone components
from utils.hybrid_response import HybridResponseGenerator
from rag.rag_system import MessageRAG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OfficialLettaIntegration:
    """Integration with Letta for enhanced memory capabilities in AI Clone using the official SDK"""
    
    def __init__(self, base_url: str = "http://localhost:8283", api_key: Optional[str] = None):
        """
        Initialize the Letta integration.
        
        Args:
            base_url: URL of the Letta server (for local deployment)
            api_key: API key for Letta Cloud (if using cloud deployment)
        """
        # Initialize Letta client
        if api_key:
            self.client = Letta(token=api_key)
            logger.info("Initialized Letta client with API key")
        else:
            self.client = Letta(base_url=base_url)
            logger.info(f"Initialized Letta client with base URL: {base_url}")
        
        # Cache for agent IDs
        self.agent_cache = {}
    
    def get_or_create_agent(self, user_id: str, personal_info: Dict[str, Any]) -> Optional[str]:
        """
        Get an existing agent or create a new one for this user.
        
        Args:
            user_id: Unique identifier for the user
            personal_info: Dictionary containing personal information about the user
            
        Returns:
            Agent ID if successful, None otherwise
        """
        agent_name = f"ai_clone_{user_id}"
        
        # Check cache first
        if user_id in self.agent_cache:
            return self.agent_cache[user_id]
        
        try:
            # List existing agents
            agents = self.client.list_agents()
            
            # Check if agent already exists
            for agent in agents:
                if agent.name == agent_name:
                    logger.info(f"Found existing agent: {agent.id}")
                    self.agent_cache[user_id] = agent.id
                    return agent.id
            
            # Create a new agent
            agent = self.client.create_agent(
                name=agent_name,
                description=f"AI Clone of {personal_info.get('name', 'User')}"
            )
            
            logger.info(f"Created new agent: {agent.id}")
            self.agent_cache[user_id] = agent.id
            
            # Add initial memories
            self._add_initial_memories(agent.id, personal_info)
            
            return agent.id
            
        except Exception as e:
            logger.error(f"Error in get_or_create_agent: {e}")
            return None
    
    def _add_initial_memories(self, agent_id: str, personal_info: Dict[str, Any]):
        """Add initial memories to a newly created agent"""
        try:
            # Add basic identity information
            memories = []
            
            if "name" in personal_info:
                memories.append(f"My name is {personal_info['name']}.")
            
            if "hometown" in personal_info:
                memories.append(f"I am from {personal_info['hometown']}.")
            
            if "occupation" in personal_info:
                memories.append(f"I work as a {personal_info['occupation']}.")
            
            # Add additional facts
            for key, value in personal_info.items():
                if key not in ["name", "hometown", "occupation"] and isinstance(value, str):
                    memories.append(f"{key}: {value}")
            
            # Add each memory individually
            for memory in memories:
                self.add_memory(agent_id, memory)
                
        except Exception as e:
            logger.error(f"Error adding initial memories: {e}")
    
    def add_memory(self, agent_id: str, content: str) -> bool:
        """
        Add a new memory to the agent.
        
        Args:
            agent_id: ID of the Letta agent
            content: Text content of the memory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.create_memory(agent_id=agent_id, content=content)
            logger.info(f"Added memory to agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return False
    
    def process_message(self, agent_id: str, message: str, channel: str = "text") -> Optional[str]:
        """
        Process a message using the Letta agent.
        
        Args:
            agent_id: ID of the Letta agent
            message: Message text to process
            channel: Communication channel (text or email)
            
        Returns:
            Response text if successful, None otherwise
        """
        try:
            # Send message to agent
            response = self.client.send_message(
                agent_id=agent_id,
                messages=[{"role": "user", "content": message}]
            )
            
            # Extract assistant messages
            assistant_messages = [
                msg for msg in response.messages 
                if msg.message_type == "assistant_message"
            ]
            
            if assistant_messages:
                # Get the latest assistant message
                response_text = assistant_messages[-1].content
                
                # Format based on channel
                if channel == "email" and not response_text.startswith("Subject:"):
                    response_text = self._format_as_email(response_text)
                
                return response_text
            else:
                logger.warning("No assistant message found in response")
                return None
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None
    
    def _format_as_email(self, text: str) -> str:
        """Format text as a formal email"""
        # Simple email formatting - you can enhance this based on your needs
        lines = text.split('\n')
        if len(lines) > 2:
            # If it already has some structure, just add formal closing if needed
            if not any(line.strip().startswith("Best,") or 
                      line.strip().startswith("Regards,") or
                      line.strip().startswith("Sincerely,") for line in lines):
                text += "\n\nBest,\nAlbert"
        else:
            # Basic formatting for short responses
            text = f"Hi,\n\n{text}\n\nBest,\nAlbert"
        
        return text


class HybridLettaSystem:
    """
    Hybrid system that combines Letta's memory capabilities with the existing
    AI Clone architecture (RAG + fine-tuned model).
    """
    
    def __init__(self, use_letta: bool = True, letta_url: str = "http://localhost:8283", letta_api_key: Optional[str] = None):
        """
        Initialize the hybrid system.
        
        Args:
            use_letta: Whether to use Letta (can be disabled for fallback)
            letta_url: URL of the Letta server (for local deployment)
            letta_api_key: API key for Letta Cloud (if using cloud deployment)
        """
        self.use_letta = use_letta
        
        # Initialize existing components
        self.hybrid_generator = HybridResponseGenerator()
        self.message_rag = MessageRAG(clear_existing=True)
        
        # Initialize Letta integration if enabled
        if self.use_letta:
            try:
                self.letta = OfficialLettaIntegration(base_url=letta_url, api_key=letta_api_key)
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
    
    def get_agent_id(self, user_id: str) -> Optional[str]:
        """Get or create a Letta agent for the user"""
        if not self.use_letta:
            return None
            
        # Get or create agent
        return self.letta.get_or_create_agent(user_id, self.personal_info)
    
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
                    self.letta.add_memory(agent_id, memory_text)
            
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
                return self.letta.add_memory(agent_id, fact)
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
        channel="text"
    )
    
    print(f"Response: {response['text']}")
    print(f"Source: {response['source']}")
