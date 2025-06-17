"""
Simulate a fine-tuned AI Clone

This script simulates how your fine-tuned model would respond,
without requiring an actual fine-tuned model. Useful for testing
the concept before spending resources on fine-tuning.
"""

import os
import asyncio
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('OPENAI_API_KEY')

async def simulate_fine_tuned_model(model="gpt-4-turbo", system_prompt=None):
    """Simulate a fine-tuned model with a strong system prompt"""
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Use default system prompt if none provided
    if not system_prompt:
        system_prompt = """
You are Clone, an AI trained to respond exactly like the user would. 
You must match their casual, concise communication style with minimal exclamation marks.
Your responses should sound exactly like them based on these examples:

Friend: Hey, how's it going?
User: not much, just working on this ai project

Friend: That sounds cool! What does it do?
User: it's a discord bot that learns to talk like me

Friend: How does it work?
User: it uses my discord messages to learn my style

Friend: That's pretty impressive! Can it respond to questions too?
User: yeah that's the whole point

Friend: Will you make it public?
User: probably not, it's just for me

Friend: Fair enough. What other projects are you working on?
User: nothing much, just this one for now

Friend: Cool, let me know how it turns out
User: will do

IMPORTANT CHARACTERISTICS:
- Very concise, rarely uses more than one sentence
- Almost never uses exclamation marks
- Lowercase style, rarely capitalizes
- Direct and straightforward
- Casual tone
- Minimal punctuation
"""
    
    print(f"\n=== Simulating Fine-Tuned Model ===")
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
                model=model,
                messages=messages,
                max_tokens=50,  # Keep responses short like the examples
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
    parser = argparse.ArgumentParser(description="Simulate a fine-tuned GPT model")
    parser.add_argument("--model", default="gpt-4-turbo", help="Model to use (default: gpt-4-turbo)")
    parser.add_argument("--system-prompt", help="Custom system prompt to use")
    
    args = parser.parse_args()
    
    # Check if API key is set
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env file")
    else:
        asyncio.run(simulate_fine_tuned_model(args.model, args.system_prompt))
