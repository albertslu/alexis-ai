"""
Test script for Letta-Enhanced Generator
"""

import json
import logging
from utils.letta_enhanced_generator import LettaEnhancedGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_letta_enhanced_generator():
    """Test the Letta-Enhanced Generator"""
    print("\n=== Testing Letta-Enhanced Generator ===")
    
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
    
    # Initialize Letta-enhanced generator
    generator = LettaEnhancedGenerator(user_id="albert")
    
    # Add some core memories
    print("\nAdding core memories...")
    generator.add_fact_to_memory("My name is Albert Lu and I'm an entrepreneur based in Austin.")
    generator.add_fact_to_memory("I'm passionate about photography, especially wedding photography.")
    generator.add_fact_to_memory("I'm currently working on an AI startup called AI Clone.")
    generator.add_fact_to_memory("My friend Sharon is a model who recently did a Nike campaign.")
    
    # Test basic message
    print("\nTesting basic message:")
    response = generator.generate_response("Hello, how are you today?")
    print(f"Response: {response}")
    
    # Test memory recall
    print("\nTesting memory recall:")
    response = generator.generate_response("What do you do for work?")
    print(f"Response: {response}")
    
    # Test conversation continuity
    print("\nTesting conversation continuity:")
    response = generator.generate_response("Tell me more about your photography.")
    print(f"Response: {response}")
    
    # Test entity recall
    print("\nTesting entity recall:")
    response = generator.generate_response("How's Sharon doing?")
    print(f"Response: {response}")
    
    # Test adding a new memory during conversation
    print("\nTesting adding a new memory during conversation:")
    response = generator.generate_response("I heard you're learning to play guitar. How's that going?")
    print(f"Response: {response}")
    
    # Add a new fact to memory
    generator.add_fact_to_memory("I recently started learning to play the guitar.")
    
    # Test if the new fact was added
    print("\nTesting new fact recall:")
    response = generator.generate_response("Do you play any musical instruments?")
    print(f"Response: {response}")

if __name__ == "__main__":
    test_letta_enhanced_generator()
