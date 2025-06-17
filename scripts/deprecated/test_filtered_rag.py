#!/usr/bin/env python3

"""
Test script to compare responses with different RAG filtering settings.
This helps evaluate the impact of filtering out older, potentially problematic examples.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.app_integration import initialize_rag, enhance_prompt_with_rag

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')
TEST_PROMPTS = [
    "What's your favorite travel destination?",
    "Tell me about your work experience",
    "What kind of music do you like?",
    "How would you respond to an urgent email from a client?",
    "What are your thoughts on AI technology?"
]

def test_rag_filtering(min_date=None, model_version=None, test_prompts=None):
    """
    Test RAG system with different filtering settings.
    
    Args:
        min_date: Minimum date for messages to include (ISO format string)
        model_version: Only include messages from this model version or newer
        test_prompts: List of prompts to test with
        
    Returns:
        dict: Test results
    """
    if test_prompts is None:
        test_prompts = TEST_PROMPTS
        
    # Initialize RAG system with filters
    print(f"Initializing RAG with filters - min_date: {min_date}, model_version: {model_version}")
    rag_system = initialize_rag(min_date=min_date, model_version=model_version)
    
    # Basic system prompt
    base_system_prompt = """You are an AI clone of the user. Respond in a way that accurately represents 
    the user's personality, knowledge, and communication style. Be concise and natural in your responses."""
    
    results = {
        'settings': {
            'min_date': min_date,
            'model_version': model_version,
            'message_count': len(rag_system.messages)
        },
        'prompts': []
    }
    
    # Test each prompt
    for prompt in test_prompts:
        print(f"\nTesting prompt: {prompt}")
        
        # Get enhanced prompt with RAG context
        enhanced_prompt = enhance_prompt_with_rag(base_system_prompt, prompt)
        
        # Record result
        result = {
            'prompt': prompt,
            'enhanced_prompt': enhanced_prompt,
            'rag_examples_count': enhanced_prompt.count("Example from your past messages:")
        }
        
        results['prompts'].append(result)
        
        # Print summary
        print(f"  RAG examples included: {result['rag_examples_count']}")
        
    return results

def main():
    parser = argparse.ArgumentParser(description='Test RAG system with different filtering settings')
    parser.add_argument('--min-date', type=str, help='Minimum date to include (YYYY-MM-DD)')
    parser.add_argument('--model-version', type=str, help='Minimum model version to include')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    parser.add_argument('--compare', action='store_true', help='Compare filtered vs unfiltered')
    
    args = parser.parse_args()
    
    # Format min_date if provided
    min_date = args.min_date
    if min_date and len(min_date) == 10:  # YYYY-MM-DD format
        min_date = f"{min_date}T00:00:00"
    
    results = {}
    
    if args.compare:
        # Test with no filtering
        print("\n=== Testing with NO filtering ===")
        unfiltered_results = test_rag_filtering()
        results['unfiltered'] = unfiltered_results
        
        # Test with filtering
        print("\n=== Testing with filtering ===")
        filtered_results = test_rag_filtering(min_date=min_date, model_version=args.model_version)
        results['filtered'] = filtered_results
        
        # Print comparison
        print("\n=== Comparison ===")
        print(f"Unfiltered RAG size: {unfiltered_results['settings']['message_count']} messages")
        print(f"Filtered RAG size: {filtered_results['settings']['message_count']} messages")
        print(f"Difference: {unfiltered_results['settings']['message_count'] - filtered_results['settings']['message_count']} messages filtered out")
        
        for i, prompt in enumerate(TEST_PROMPTS):
            unfiltered_examples = unfiltered_results['prompts'][i]['rag_examples_count']
            filtered_examples = filtered_results['prompts'][i]['rag_examples_count']
            print(f"\nPrompt: {prompt}")
            print(f"  Unfiltered examples: {unfiltered_examples}")
            print(f"  Filtered examples: {filtered_examples}")
            print(f"  Difference: {unfiltered_examples - filtered_examples}")
    else:
        # Just test with the specified filters
        results = test_rag_filtering(min_date=min_date, model_version=args.model_version)
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    main()
