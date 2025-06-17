#!/usr/bin/env python3
"""
Email Response Testing Script for AI Clone

This script tests the AI clone's ability to respond to emails in a way
that matches the user's style and provides appropriate responses for different
types of professional and personal emails.
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

# Test categories for emails
EMAIL_TEST_CATEGORIES = {
    "professional_requests": [
        {
            "subject": "Request for Meeting",
            "body": "Hi Albert,\n\nI hope this email finds you well. I'd like to schedule a meeting to discuss potential collaboration opportunities between our companies. Would you be available sometime next week?\n\nBest regards,\nJohn Smith\nCEO, Tech Innovations"
        },
        {
            "subject": "Interview Invitation",
            "body": "Dear Albert,\n\nThank you for your application to the Software Engineer position at our company. We were impressed with your background and would like to invite you for an interview. Please let me know your availability for next week.\n\nBest,\nSarah Johnson\nHR Manager"
        },
        {
            "subject": "Project Update Request",
            "body": "Hi Albert,\n\nI'm checking in on the status of the website redesign project. Could you provide an update on the timeline and any challenges you're facing?\n\nThanks,\nMichael Chen\nProduct Manager"
        }
    ],
    "follow_up_emails": [
        {
            "subject": "Re: Our Meeting Yesterday",
            "body": "Hi Albert,\n\nThanks for meeting with me yesterday. I wanted to follow up on a few points we discussed:\n\n1. Timeline for the project launch\n2. Budget allocation for marketing\n3. Team responsibilities\n\nCould you clarify these when you get a chance?\n\nBest,\nEmily"
        },
        {
            "subject": "Re: Project Proposal",
            "body": "Albert,\n\nI've reviewed your proposal and have a few questions:\n- What's the expected ROI for this investment?\n- How does this align with our Q3 objectives?\n- Can we accelerate the timeline?\n\nLooking forward to your thoughts.\n\nRegards,\nDavid"
        }
    ],
    "casual_emails": [
        {
            "subject": "Coffee next week?",
            "body": "Hey Albert,\n\nIt's been a while since we caught up. Want to grab coffee next week? I'd love to hear about your new startup.\n\nCheers,\nAlex"
        },
        {
            "subject": "Thoughts on this article?",
            "body": "Hi Albert,\n\nI came across this article about AI personalization and thought of you: https://example.com/ai-trends\n\nWhat do you think? Seems relevant to what you're building.\n\n-Jason"
        }
    ],
    "networking_emails": [
        {
            "subject": "Introduction - Referred by Sarah",
            "body": "Hello Albert,\n\nSarah Johnson suggested I reach out to you. I'm working on an AI project in the personal assistant space and would love to get your insights given your experience.\n\nWould you be open to a brief call in the coming weeks?\n\nBest regards,\nRobert Chen\nFounder, AI Assistants Inc."
        },
        {
            "subject": "Connecting from AI Conference",
            "body": "Hi Albert,\n\nWe briefly met at the AI Summit last month. I was impressed by your insights on personalized AI and would love to continue our conversation.\n\nDo you have time for a virtual coffee in the next couple of weeks?\n\nBest,\nLisa Wang\nAI Research Lead"
        }
    ],
    "complex_inquiries": [
        {
            "subject": "Partnership Opportunity",
            "body": "Dear Albert,\n\nI'm reaching out from TechVentures Capital. We're interested in exploring a potential investment in your AI clone startup.\n\nCould you share more details about your:\n1. Current traction and user metrics\n2. Technology differentiation\n3. Go-to-market strategy\n4. Funding needs and timeline\n\nI'd be happy to sign an NDA if needed before discussing further details.\n\nLooking forward to your response,\nJames Wilson\nPartner, TechVentures Capital"
        },
        {
            "subject": "Speaking Opportunity at AI Summit",
            "body": "Hello Albert,\n\nI'm organizing the upcoming AI Personalization Summit and would like to invite you to speak about your work on AI clones.\n\nThe event will take place on October 15-16 in San Francisco. We can offer:\n- Full travel and accommodation\n- 30-minute speaking slot\n- Participation in a panel discussion\n\nPlease let me know if you're interested, and we can discuss further details.\n\nBest regards,\nNatalie Rodriguez\nEvent Director, AI Summit"
        }
    ]
}

# Load reference responses (if available)
REFERENCE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'email_reference_responses.json')

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
    results_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f'email_test_results_{timestamp}.json')
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Test results saved to {results_file}")
    return results_file

def evaluate_email_response(response, email_type):
    """
    Evaluate the quality of an email response
    
    Args:
        response: The generated response
        email_type: Type of email being tested
        
    Returns:
        dict: Evaluation results
    """
    evaluation = {
        "has_greeting": bool(response.strip().startswith(("Hi", "Hello", "Dear", "Hey"))),
        "has_sign_off": bool(any(sign_off in response.lower() for sign_off in ["best", "regards", "sincerely", "thanks", "cheers", "best regards"])),
        "response_length": len(response.split()),
        "addressed_all_points": True,  # Default, will be manually reviewed
        "tone_appropriate": True,      # Default, will be manually reviewed
        "formatting": "good"           # Default, will be manually reviewed
    }
    
    # Additional checks based on email type
    if email_type == "professional_requests":
        evaluation["professional_tone"] = not any(casual_term in response.lower() for casual_term in ["hey", "yo", "what's up", "btw", "lol"])
    
    if email_type == "complex_inquiries":
        evaluation["structured_response"] = any(marker in response for marker in ["1.", "2.", "3.", "First", "Second", "Third", "•", "-"])
    
    return evaluation

def run_email_tests(categories=None, num_per_category=2):
    """
    Run tests for email responses
    
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
        categories = list(EMAIL_TEST_CATEGORIES.keys())
    
    # Initialize results
    results = {
        "timestamp": datetime.now().isoformat(),
        "categories_tested": categories,
        "tests_per_category": num_per_category,
        "results": []
    }
    
    # Run tests for each category
    for category in categories:
        print(f"\n=== Testing email category: {category} ===")
        
        # Select random emails from the category
        emails = random.sample(EMAIL_TEST_CATEGORIES[category], min(num_per_category, len(EMAIL_TEST_CATEGORIES[category])))
        
        for email in emails:
            subject = email["subject"]
            body = email["body"]
            
            print(f"\nTesting email with subject: {subject}")
            
            # Create metadata for the email
            metadata = {
                "channel": "email",
                "subject": subject
            }
            
            # Generate response
            start_time = time.time()
            response = generator.generate_response(body, conversation_id=conversation_id, channel="email", metadata=metadata)
            end_time = time.time()
            
            # Process the response for email channel
            formatted_response = channel_processor.format_response_for_channel(response, "email")
            
            # Get reference response if available
            reference_key = f"{category}:{subject}"
            reference = reference_responses.get(reference_key, "")
            
            # Evaluate the response
            evaluation = evaluate_email_response(formatted_response, category)
            
            # Print results
            print(f"Response:\n{formatted_response}\n")
            print(f"Time taken: {end_time - start_time:.2f} seconds")
            print(f"Evaluation: {json.dumps(evaluation, indent=2)}")
            
            # Add to conversation history for context in future tests
            generator.add_to_conversation_history("user", body)
            generator.add_to_conversation_history("assistant", formatted_response)
            
            # Save result
            results["results"].append({
                "category": category,
                "subject": subject,
                "email_body": body,
                "response": formatted_response,
                "reference": reference,
                "evaluation": evaluation,
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

def analyze_email_test_results(results_file):
    """
    Analyze email test results and provide insights
    
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
        
        # Calculate success metrics
        greeting_success = sum(1 for r in category_results if r["evaluation"]["has_greeting"]) / len(category_results)
        sign_off_success = sum(1 for r in category_results if r["evaluation"]["has_sign_off"]) / len(category_results)
        avg_length = sum(r["evaluation"]["response_length"] for r in category_results) / len(category_results)
        
        analysis["category_analysis"][category] = {
            "num_tests": len(category_results),
            "avg_response_time": sum(r["time_taken"] for r in category_results) / len(category_results),
            "greeting_success_rate": greeting_success,
            "sign_off_success_rate": sign_off_success,
            "avg_response_length": avg_length,
            "responses": category_results
        }
    
    # Identify improvement areas
    
    # Check for missing greetings
    missing_greetings = [r for r in results["results"] if not r["evaluation"]["has_greeting"]]
    if missing_greetings:
        analysis["improvement_areas"].append({
            "area": "email_greeting",
            "description": "Some emails are missing proper greetings",
            "examples": [{"subject": r["subject"], "response": r["response"]} for r in missing_greetings]
        })
    
    # Check for missing sign-offs
    missing_sign_offs = [r for r in results["results"] if not r["evaluation"]["has_sign_off"]]
    if missing_sign_offs:
        analysis["improvement_areas"].append({
            "area": "email_sign_off",
            "description": "Some emails are missing proper sign-offs",
            "examples": [{"subject": r["subject"], "response": r["response"]} for r in missing_sign_offs]
        })
    
    # Check for very short responses (potentially incomplete)
    short_responses = [r for r in results["results"] if r["evaluation"]["response_length"] < 30]
    if short_responses:
        analysis["improvement_areas"].append({
            "area": "email_completeness",
            "description": "Some email responses are too short for professional communication",
            "examples": [{"subject": r["subject"], "response": r["response"]} for r in short_responses]
        })
    
    # Print analysis summary
    print("\n=== Email Analysis Summary ===")
    print(f"Total tests: {analysis['total_tests']}")
    print(f"Average response time: {analysis['avg_response_time']:.2f} seconds")
    print("\nCategory breakdown:")
    for category, data in analysis["category_analysis"].items():
        print(f"  - {category}: {data['num_tests']} tests, avg time: {data['avg_response_time']:.2f}s")
        print(f"    Greeting success: {data['greeting_success_rate']*100:.1f}%, Sign-off success: {data['sign_off_success_rate']*100:.1f}%")
        print(f"    Avg response length: {data['avg_response_length']:.1f} words")
    
    print("\nImprovement areas:")
    for area in analysis["improvement_areas"]:
        print(f"  - {area['description']}")
    
    return analysis

if __name__ == "__main__":
    # Run all tests
    print("=== Starting Email Response Tests ===")
    results = run_email_tests()
    
    # Analyze results
    results_file = list(results.values())[3][0]["time_taken"]
    analyze_email_test_results(results_file)
