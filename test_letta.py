"""
Test script for Letta integration
"""

import json
import logging
from letta_integration import LettaIntegration
from hybrid_letta_integration import HybridLettaSystem

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_letta_direct():
    """Test direct Letta integration"""
    print("\n=== Testing Direct Letta Integration ===")
    
    # Load personal information
    try:
        with open("data/personal_info.json", "r") as f:
            personal_info = json.load(f)
            print(f"Loaded personal info: {personal_info.keys()}")
    except FileNotFoundError:
        personal_info = {
            "name": "Albert Lu",
            "hometown": "Austin",
            "occupation": "Entrepreneur",
            "interests": ["photography", "startups", "AI"]
        }
        print(f"Using default personal info: {personal_info}")
    
    # Initialize Letta integration
    letta = LettaIntegration()
    
    # Get or create agent
    agent_id = letta.get_or_create_agent("albert", personal_info)
    print(f"Agent ID: {agent_id}")
    
    if agent_id:
        # Add some memories
        letta.add_memory(agent_id, "I enjoy photography, especially wedding photography.")
        letta.add_memory(agent_id, "I'm currently working on an AI startup.")
        letta.add_memory(agent_id, "My friend Sharon is a model who recently did a Nike campaign.")
        
        # Process a test message
        print("\nTesting basic message:")
        response = letta.process_message(agent_id, "Hello, how are you today?")
        print(f"Response: {response}")
        
        # Test memory recall
        print("\nTesting memory recall:")
        response = letta.process_message(agent_id, "What do you do for work?")
        print(f"Response: {response}")
        
        # Test conversation continuity
        print("\nTesting conversation continuity:")
        response = letta.process_message(agent_id, "Tell me more about your photography.")
        print(f"Response: {response}")
        
        # Test entity recall
        print("\nTesting entity recall:")
        response = letta.process_message(agent_id, "How's Sharon doing?")
        print(f"Response: {response}")
    else:
        print("Failed to create or retrieve agent")

def test_hybrid_system():
    """Test hybrid Letta + RAG system"""
    print("\n=== Testing Hybrid Letta + RAG System ===")
    
    # Initialize the hybrid system
    hybrid_system = HybridLettaSystem()
    
    # Process test messages
    print("\nTesting basic message:")
    response = hybrid_system.process_message(
        user_id="albert",
        message_text="Hello, how are you today?",
        channel="text"
    )
    print(f"Response: {response['text']}")
    print(f"Source: {response['source']}")
    
    # Test memory recall
    print("\nTesting memory recall:")
    response = hybrid_system.process_message(
        user_id="albert",
        message_text="What projects are you working on?",
        channel="text"
    )
    print(f"Response: {response['text']}")
    print(f"Source: {response['source']}")
    
    # Test email formatting
    print("\nTesting email formatting:")
    response = hybrid_system.process_message(
        user_id="albert",
        message_text="Can you send me an update on the project status?",
        channel="email",
        metadata={"subject": "Project Update Request"}
    )
    print(f"Response: {response['text']}")
    print(f"Source: {response['source']}")
    
    # Add a new fact to memory
    hybrid_system.add_fact_to_memory(
        user_id="albert",
        fact="I recently started learning to play the guitar."
    )
    
    # Test if the new fact was added
    print("\nTesting new fact recall:")
    response = hybrid_system.process_message(
        user_id="albert",
        message_text="Do you play any musical instruments?",
        channel="text"
    )
    print(f"Response: {response['text']}")
    print(f"Source: {response['source']}")

if __name__ == "__main__":
    # Test direct Letta integration
    test_letta_direct()
    
    # Test hybrid system
    test_hybrid_system()
