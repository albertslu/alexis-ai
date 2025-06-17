"""
Letta Integration for AI Clone
This module provides integration between the AI Clone system and Letta for enhanced memory capabilities.
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LettaIntegration:
    """Integration with Letta for enhanced memory capabilities in AI Clone"""
    
    def __init__(self, base_url: str = "http://localhost:8283"):
        """
        Initialize the Letta integration.
        
        Args:
            base_url: URL of the Letta server
        """
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        
        # Test connection to Letta server
        try:
            response = requests.get(f"{self.base_url}/v1/health")
            if response.status_code == 200:
                logger.info("Successfully connected to Letta server")
            else:
                logger.warning(f"Letta server responded with status code {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to Letta server: {e}")
    
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
        
        # Check if agent already exists
        try:
            response = requests.get(f"{self.base_url}/v1/agents/")
            if response.status_code == 200:
                agents = response.json()
                for agent in agents:
                    if agent.get("name") == agent_name:
                        logger.info(f"Found existing agent: {agent['id']}")
                        return agent["id"]
            
            # Create a simpler agent creation payload that matches Letta's API requirements
            payload = {
                "name": agent_name,
                "description": f"AI Clone of {personal_info.get('name', 'User')}"
            }
            
            response = requests.post(
                f"{self.base_url}/v1/agents/",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                agent_data = response.json()
                agent_id = agent_data['id']
                logger.info(f"Created new agent: {agent_id}")
                
                # Now add memories to the agent in a separate call
                self._add_initial_memories(agent_id, personal_info)
                
                return agent_id
            else:
                logger.error(f"Failed to create agent: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error in get_or_create_agent: {e}")
            return None
    
    def _add_initial_memories(self, agent_id: str, personal_info: Dict[str, Any]) -> bool:
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
                
            return True
            
        except Exception as e:
            logger.error(f"Error adding initial memories: {e}")
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
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            }
            
            response = requests.post(
                f"{self.base_url}/v1/agents/{agent_id}/messages",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract the assistant's response
                assistant_messages = [
                    msg for msg in response_data.get("messages", [])
                    if msg.get("message_type") == "assistant_message"
                ]
                
                if assistant_messages:
                    # Get the latest assistant message
                    response_text = assistant_messages[-1].get("content", "")
                    
                    # Format based on channel (text vs email)
                    if channel == "email" and not response_text.startswith("Subject:"):
                        # Add formal email formatting if not already formatted
                        response_text = self._format_as_email(response_text)
                    
                    return response_text
                else:
                    logger.warning("No assistant message found in response")
                    return None
            else:
                logger.error(f"Failed to process message: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error in process_message: {e}")
            return None
    
    def add_memory(self, agent_id: str, memory_text: str, label: str = "facts") -> bool:
        """
        Add a new memory to the agent.
        
        Args:
            agent_id: ID of the Letta agent
            memory_text: Text content of the memory
            label: Label for the memory (persona, facts, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Simplified memory addition to match Letta's API
            payload = {
                "content": memory_text
            }
            
            response = requests.post(
                f"{self.base_url}/v1/agents/{agent_id}/memories",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"Added memory to agent {agent_id}")
                return True
            else:
                logger.error(f"Failed to add memory: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error in add_memory: {e}")
            return False
    
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

# Example usage
if __name__ == "__main__":
    # Load personal information
    try:
        with open("data/personal_info.json", "r") as f:
            personal_info = json.load(f)
    except FileNotFoundError:
        personal_info = {
            "name": "Albert Lu",
            "hometown": "Austin",
            "occupation": "Entrepreneur"
        }
    
    # Initialize Letta integration
    letta = LettaIntegration()
    
    # Get or create agent
    agent_id = letta.get_or_create_agent("albert", personal_info)
    
    if agent_id:
        # Process a test message
        response = letta.process_message(agent_id, "Hello, how are you today?")
        print(f"Response: {response}")
        
        # Add a new memory
        letta.add_memory(agent_id, "I enjoy photography, especially wedding photography.")
