"""
Test script for manually triggering the AI Clone

This script allows you to test the AI response generation without running the full bot.
"""

import asyncio
import uuid
from backend.ai_service import AIService
from backend.config import Config

async def test_response():
    """Test the AI response generation with a sample message"""
    # Initialize the AI service
    ai_service = AIService()
    
    # Create a test channel ID
    test_channel_id = str(uuid.uuid4())
    
    # Get user input for the test message
    print("\n=== AI Clone Test ===")
    print(f"Using model: {Config.AI_MODEL}")
    print("Type a message to test the AI response (or 'exit' to quit):")
    
    while True:
        user_message = input("\nYour message: ")
        if user_message.lower() == 'exit':
            break
        
        print("\nGenerating response...")
        
        # Format the message as expected by the AI service
        context_messages = [{
            'author_id': '123456789',  # Some random user ID (not yours)
            'author_name': 'Test User',
            'content': user_message
        }]
        
        # Generate a response
        response = await ai_service.generate_response(test_channel_id, context_messages)
        
        # Print the response
        if response:
            print(f"\nAI Response: {response}")
        else:
            print("\nError: Failed to generate a response")

if __name__ == "__main__":
    asyncio.run(test_response())
