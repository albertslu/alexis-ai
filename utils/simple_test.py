"""
Simple test script for OpenAI API

This script tests the OpenAI API directly without using the AIService class.
"""

import os
import asyncio
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
model = os.getenv('AI_MODEL', 'gpt-4')

async def test_openai():
    """Test the OpenAI API directly"""
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    print("\n=== OpenAI API Test ===")
    print(f"Using model: {model}")
    print("Type a message to test the AI response (or 'exit' to quit):")
    
    # Keep track of conversation
    messages = [
        {"role": "system", "content": "You are an AI assistant that responds like the user would respond in a Discord conversation. Keep responses conversational and in the style of the user. Respond as if you are the user."}
    ]
    
    while True:
        user_message = input("\nYour message: ")
        if user_message.lower() == 'exit':
            break
        
        # Add user message to conversation
        messages.append({"role": "user", "content": user_message})
        
        print("\nGenerating response...")
        try:
            # Generate response
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=150,
                temperature=0.7,
            )
            
            # Get response text
            response_text = response.choices[0].message.content
            
            # Add response to conversation
            messages.append({"role": "assistant", "content": response_text})
            
            # Print response
            print(f"\nAI Response: {response_text}")
            
            # Keep conversation history limited
            if len(messages) > 10:
                # Keep system message and last 4 exchanges
                messages = [messages[0]] + messages[-8:]
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai())
