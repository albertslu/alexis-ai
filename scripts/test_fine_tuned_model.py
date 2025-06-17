#!/usr/bin/env python3

import os
import sys
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# Add parent directory to path for importing model_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model_config import FINE_TUNED_MODEL, DEFAULT_MODEL

# Load environment variables
load_dotenv()

def test_model(prompt, model_id=None, system_message=None):
    """Test the fine-tuned model with a given prompt"""
    # Use specified model or default to fine-tuned model
    model_id = model_id or os.getenv("AI_MODEL", FINE_TUNED_MODEL)
    
    # Default system message if none provided
    if system_message is None:
        system_message = "You are an AI clone trained to mimic a specific person's communication style."
    
    # Initialize OpenAI client - using the latest version of the library
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    print(f"\nUsing model: {model_id}\n")
    print(f"System message: {system_message}\n")
    print(f"Prompt: {prompt}\n")
    print("Generating response...\n")
    
    # Create chat completion
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )
    
    # Print response
    print("Response:")
    print(f"{response.choices[0].message.content}\n")
    
    # Print token usage
    if hasattr(response, 'usage'):
        print(f"Token usage: {response.usage.total_tokens} total tokens")
        print(f"  - Prompt tokens: {response.usage.prompt_tokens}")
        print(f"  - Completion tokens: {response.usage.completion_tokens}")

def main():
    parser = argparse.ArgumentParser(description="Test your fine-tuned model")
    parser.add_argument("prompt", nargs="?", default="Tell me about yourself.", 
                        help="The prompt to send to the model")
    parser.add_argument("--model", "-m", help="Specific model ID to use")
    parser.add_argument("--system", "-s", help="Custom system message")
    parser.add_argument("--compare", "-c", action="store_true", 
                        help="Compare fine-tuned model with base model")
    
    args = parser.parse_args()
    
    if args.compare:
        # Test with base model first
        print("\n=== Testing with BASE model ===")
        test_model(args.prompt, DEFAULT_MODEL, args.system)
        
        # Then test with fine-tuned model
        print("\n=== Testing with FINE-TUNED model ===")
        test_model(args.prompt, FINE_TUNED_MODEL, args.system)
    else:
        # Just test with the specified or default model
        test_model(args.prompt, args.model, args.system)

if __name__ == "__main__":
    main()
