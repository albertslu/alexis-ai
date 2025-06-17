#!/usr/bin/env python3

"""
Test script for feedback-based prompt enhancement.

This script demonstrates how the feedback system enhances prompts
based on rejected and corrected responses.
"""

import os
import json
from utils.feedback_system import FeedbackSystem
from utils.hybrid_response import HybridResponseGenerator

def main():
    """
    Test the feedback-based prompt enhancement.
    """
    print("\n=== Testing Feedback-Based Prompt Enhancement ===\n")
    
    # Initialize feedback system
    feedback_system = FeedbackSystem()
    
    # Initialize hybrid response generator
    hybrid_gen = HybridResponseGenerator()
    
    # Base prompt for testing
    base_prompt = "Respond as the user would in an email. Maintain appropriate formality and structure."
    
    # Get enhanced prompt
    enhanced_prompt = feedback_system.enhance_system_prompt(base_prompt, channel="email")
    
    print("=== Base Prompt ===")
    print(base_prompt)
    print("\n=== Enhanced Prompt ===")
    print(enhanced_prompt)
    
    # Test with a specific example from the feedback
    print("\n=== Testing with Specific Rejection Example ===")
    
    # Example of a rejected response where clone repeated the user's message
    message_id = "19bf45c1-3ca8-45b4-b371-9f446055a133"
    original_message = "are u available for a meeting next tuesday?"
    
    # Print the original system message that would be used
    original_system_message = hybrid_gen._prepare_system_message([], channel="email")
    print("\n=== Original System Message ===")
    print(original_system_message)
    
    # Print what the response would be with this enhancement
    print("\n=== With Feedback Enhancement, the AI would now: ===")
    print("1. Recognize this is a repetition of the user's question")
    print("2. Notice the informal language ('u' instead of 'you') in an email context")
    print("3. Provide a substantive response instead, such as:")
    print("   'Yes, I'm available for a meeting next Tuesday. What time works best for you?'")
    print("   or")
    print("   'I have a conflict on Tuesday morning, but I could meet in the afternoon after 2pm. Would that work for you?'")
    
    print("\n=== How the Feedback Loop Works ===")
    print("1. User rejects or corrects AI responses in the feedback interface")
    print("2. System analyzes patterns in rejected/corrected responses")
    print("3. System enhances prompts with learned patterns and examples")
    print("4. AI generates better responses based on enhanced prompts")
    print("5. Over time, the system accumulates more feedback to further improve")
    
    print("\n=== Next Steps for Continuous Learning ===")
    print("1. Implement automated fine-tuning triggers when enough corrections accumulate")
    print("2. Add analytics to track improvement over time")
    print("3. Consider A/B testing different prompt enhancement strategies")

if __name__ == "__main__":
    main()
