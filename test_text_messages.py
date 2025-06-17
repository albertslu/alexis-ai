#!/usr/bin/env python3
"""
Text Message Testing Script for AI Clone

This script tests the AI clone's ability to respond to text messages in a way
that matches the user's style and provides accurate information.
"""

import os
import json
import time
import sys
from datetime import datetime
import random

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the hybrid response generator
from utils.hybrid_response import HybridResponseGenerator
from utils.channel_processor import ChannelProcessor

# Test categories
TEST_CATEGORIES = {
    "greetings": [
        "hey",
        "hello",
        "what's up",
        "yo",
        "hi there"
    ],
    "personal_info": [
        "what do you do for work?",
        "where are you living now?",
        "what are your hobbies?",
        "tell me about your startup",
        "what's your background?"
    ],
    "follow_up_questions": [
        "how's that going?",
        "can you tell me more?",
        "when did you start that?",
        "why did you choose that?",
        "how does that work?"
    ],
    "opinions": [
        "what do you think about AI?",
        "do you like traveling?",
        "what's your favorite food?",
        "are you a morning person?",
        "what kind of music do you like?"
    ],
    "complex_questions": [
        "can you help me understand how your startup works?",
        "what are your plans for the next few months?",
        "how do you balance work and personal life?",
        "what's the most challenging part of your current project?",
        "how would you approach building an AI product from scratch?"
    ],
    "casual_chat": [
        "did you see that new movie?",
        "how was your weekend?",
        "have you tried that new restaurant downtown?",
        "are you watching any good shows lately?",
        "what have you been up to?"
    ]
}

# Load reference responses (if available)
REFERENCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'reference_responses.json')

def load_reference_responses():
    """Load reference responses from file if available"""
    if os.path.exists(REFERENCE_FILE):
        try:
            with open(REFERENCE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading reference responses: {str(e)}")
    return {}

def save_test_results(results):
    """Save test results to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f'test_results_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Test results saved to {results_file}")
    return results_file

def run_text_message_tests(categories=None, num_per_category=3):
    """
    Run tests for text message responses
    
    Args:
        categories: List of categories to test (None for all)
        num_per_category: Number of tests per category
    
    Returns:
        dict: Test results
    """
    # Initialize the hybrid response generator
    generator = HybridResponseGenerator()
    channel_processor = ChannelProcessor()
    
    # Start a conversation
    conversation_id = generator.start_conversation()
    
    # Load reference responses
    reference_responses = load_reference_responses()
    
    # Select categories to test
    if categories is None:
        categories = list(TEST_CATEGORIES.keys())
    
    # Initialize results
    results = {
        "timestamp": datetime.now().isoformat(),
        "categories_tested": categories,
        "tests_per_category": num_per_category,
        "results": []
    }
    
    # Run tests for each category
    for category in categories:
        print(f"\n=== Testing category: {category} ===")
        
        # Select random questions from the category
        questions = random.sample(TEST_CATEGORIES[category], min(num_per_category, len(TEST_CATEGORIES[category])))
        
        for question in questions:
            print(f"\nTesting: {question}")
            
            # Generate response
            start_time = time.time()
            response = generator.generate_response(question, conversation_id=conversation_id, channel="text")
            end_time = time.time()
            
            # Process the response for text channel
            formatted_response = channel_processor.format_response_for_channel(response, "text")
            
            # Get reference response if available
            reference = reference_responses.get(question, "")
            
            # Print results
            print(f"Response: {formatted_response}")
            print(f"Time taken: {end_time - start_time:.2f} seconds")
            
            # Add to conversation history for context in future tests
            generator.add_to_conversation_history("user", question)
            generator.add_to_conversation_history("assistant", formatted_response)
            
            # Save result
            results["results"].append({
                "category": category,
                "question": question,
                "response": formatted_response,
                "reference": reference,
                "time_taken": end_time - start_time
            })
    
    # Save test results
    results_file = save_test_results(results)
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Categories tested: {len(categories)}")
    print(f"Total tests: {len(results['results'])}")
    print(f"Results saved to: {results_file}")
    
    return results

def analyze_test_results(results_file):
    """
    Analyze test results and provide insights
    
    Args:
        results_file: Path to the results file
        
    Returns:
        dict: Analysis results
    """
    # Load results
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    # Initialize analysis
    analysis = {
        "total_tests": len(results["results"]),
        "avg_response_time": sum(r["time_taken"] for r in results["results"]) / len(results["results"]),
        "category_analysis": {},
        "improvement_areas": []
    }
    
    # Analyze by category
    for category in results["categories_tested"]:
        category_results = [r for r in results["results"] if r["category"] == category]
        
        analysis["category_analysis"][category] = {
            "num_tests": len(category_results),
            "avg_response_time": sum(r["time_taken"] for r in category_results) / len(category_results),
            "responses": category_results
        }
    
    # Identify improvement areas
    slow_responses = [r for r in results["results"] if r["time_taken"] > 2.0]
    if slow_responses:
        analysis["improvement_areas"].append({
            "area": "response_time",
            "description": "Some responses are taking too long",
            "examples": slow_responses
        })
    
    # Check for very short responses (potentially incomplete)
    short_responses = [r for r in results["results"] if len(r["response"].split()) < 5]
    if short_responses:
        analysis["improvement_areas"].append({
            "area": "response_completeness",
            "description": "Some responses are too short",
            "examples": short_responses
        })
    
    # Print analysis summary
    print("\n=== Analysis Summary ===")
    print(f"Total tests: {analysis['total_tests']}")
    print(f"Average response time: {analysis['avg_response_time']:.2f} seconds")
    print("\nCategory breakdown:")
    for category, data in analysis["category_analysis"].items():
        print(f"  - {category}: {data['num_tests']} tests, avg time: {data['avg_response_time']:.2f}s")
    
    print("\nImprovement areas:")
    for area in analysis["improvement_areas"]:
        print(f"  - {area['description']}")
    
    return analysis

if __name__ == "__main__":
    # Run all tests
    print("=== Starting Text Message Tests ===")
    results = run_text_message_tests()
    
    # Analyze results
    results_file = list(results.values())[3][0]["time_taken"]
    analyze_test_results(results_file)
