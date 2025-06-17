"""
Test script for the fine-tuned AI Clone

This script allows you to test your fine-tuned model directly.
"""

import os
import asyncio
import uuid
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('OPENAI_API_KEY')

async def test_fine_tuned_model(model_id, system_prompt=None):
    """Test the fine-tuned model with interactive prompts"""
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Use provided model ID or get from environment/file
    if not model_id:
        # Try to get from environment
        model_id = os.getenv('FINE_TUNED_MODEL')
        
        # If not in environment, try to read from file
        if not model_id:
            try:
                with open('fine_tuned_model.txt', 'r') as f:
                    model_id = f.read().strip()
            except FileNotFoundError:
                print("Error: No model ID provided and fine_tuned_model.txt not found")
                return
    
    # Use default system prompt if none provided
    if not system_prompt:
        system_prompt = "You are an AI assistant that responds exactly like the user would respond in a Discord conversation. The user has a casual, concise communication style and rarely uses exclamation marks. Match their tone and writing patterns precisely."
    
    print(f"\n=== Testing Fine-Tuned Model: {model_id} ===")
    print("Type a message to test the AI response (or 'exit' to quit):")
    
    # Store conversation history
    conversation_history = []
    
    while True:
        user_message = input("\nYour message: ")
        if user_message.lower() == 'exit':
            break
        
        print("\nGenerating response...")
        
        # Format messages for the API
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Generate response
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=150,
                temperature=0.7,
            )
            
            # Extract response text
            response_text = response.choices[0].message.content
            
            # Print the response
            print(f"\nAI Response: {response_text}")
            
            # Add to conversation history
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": response_text})
            
            # Keep conversation history manageable (last 10 messages)
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
                
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test a fine-tuned GPT model")
    parser.add_argument("--model", help="ID of the fine-tuned model (default: read from fine_tuned_model.txt)")
    parser.add_argument("--system-prompt", help="Custom system prompt to use")
    
    args = parser.parse_args()
    
    # Check if API key is set
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env file")
    else:
        asyncio.run(test_fine_tuned_model(args.model, args.system_prompt))
