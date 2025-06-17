"""
Prepare User Training Data for GPT Fine-tuning

This script processes user messages from the training chat interface
and prepares them in the format required for OpenAI's fine-tuning.
It ensures that only user messages are used as examples of how the AI should respond.
It can also integrate LinkedIn profile data to enhance the training with professional information.
"""

import os
import json
import random
import argparse
from sklearn.model_selection import train_test_split
from datetime import datetime
from pathlib import Path
from .linkedin_integration import (
    find_latest_linkedin_profile,
    load_linkedin_persona,
    create_professional_context,
    create_linkedin_training_examples,
    enhance_system_prompt_with_linkedin
)

# Minimum number of user messages required for fine-tuning
MIN_USER_MESSAGES = 10  # Reduced from 20 to make it more user-friendly

def analyze_writing_style(messages):
    """
    Analyze the user's writing style to create a better system prompt.
    
    Args:
        messages: List of user message strings
    
    Returns:
        A string describing the user's writing style
    """
    # Count lowercase vs uppercase first letters
    lowercase_starts = sum(1 for msg in messages if msg and len(msg) > 0 and msg[0].islower())
    
    # Check punctuation usage
    periods = sum(msg.count('.') for msg in messages)
    exclamations = sum(msg.count('!') for msg in messages)
    question_marks = sum(msg.count('?') for msg in messages)
    
    # Check for common expressions
    lols = sum(1 for msg in messages if 'lol' in msg.lower())
    
    # Generate style description
    style_traits = []
    if lowercase_starts > len(messages) * 0.7:
        style_traits.append("rarely capitalizes sentences")
    
    if periods < len(messages) * 0.5:
        style_traits.append("uses minimal punctuation")
    
    if exclamations > len(messages) * 0.3:
        style_traits.append("uses exclamation marks frequently")
    else:
        style_traits.append("rarely uses exclamation marks")
        
    if lols > len(messages) * 0.1:
        style_traits.append("occasionally uses 'lol'")
    
    # Return a style description
    style_description = ""
    if style_traits:
        style_description = "The user " + ", ".join(style_traits) + "."
    
    return style_description

def create_training_examples(conversation_pairs, system_prompt):
    """
    Create training examples where the AI learns to respond like the user.
    
    Args:
        conversation_pairs: List of (bot_message, user_response) tuples
        system_prompt: System prompt to use for all examples
    
    Returns:
        List of training examples in the format required for fine-tuning
    """
    examples = []
    
    # Create examples where the AI learns to respond like the user
    for bot_message, user_response in conversation_pairs:
        # Create an example where the AI learns to respond like the user would
        example = {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": bot_message
                },
                {
                    "role": "assistant",
                    "content": user_response
                }
            ]
        }
        examples.append(example)
        
        # We no longer need the additional examples with follow-up questions
        # since we're using actual conversation pairs
    
    return examples

def extract_conversation_pairs(training_data_path):
    """
    Extract conversation pairs from the training data file.
    Only use 'bot' and 'user' pairs, not 'clone' messages which are AI-generated.
    
    Args:
        training_data_path: Path to the training data JSON file
    
    Returns:
        List of (bot_message, user_response) tuples
    """
    with open(training_data_path, 'r') as f:
        training_data = json.load(f)
    
    conversation_pairs = []
    
    # Extract message pairs from conversations
    for conversation in training_data.get('conversations', []):
        messages = conversation.get('messages', [])
        
        # Look for bot message followed by user response
        # Explicitly filter out 'clone' messages which are AI-generated
        for i in range(len(messages) - 1):
            sender = messages[i].get('sender')
            next_sender = messages[i+1].get('sender')
            
            # Only use 'bot' -> 'user' pairs, not 'clone' -> 'user' pairs
            if sender == 'bot' and next_sender == 'user':
                bot_message = messages[i].get('text', '')
                user_response = messages[i+1].get('text', '')
                
                # Only add pairs where both messages are non-empty
                if bot_message and user_response and len(user_response.strip()) >= 5:
                    conversation_pairs.append((bot_message, user_response))
    
    return conversation_pairs

def prepare_fine_tuning_data(input_file, output_prefix, train_size=0.8, val_size=0.2, prompt_for_linkedin=True):
    """
    Prepare user message data for GPT fine-tuning.
    
    Args:
        input_file: Path to the JSON file with collected user messages
        output_prefix: Prefix for output files (will create prefix_train.jsonl, prefix_val.jsonl)
        train_size: Proportion of data to use for training
        val_size: Proportion of data to use for validation
        prompt_for_linkedin: Whether to prompt the user for LinkedIn profile during training
    """
    # Extract conversation pairs
    conversation_pairs = extract_conversation_pairs(input_file)
    
    print(f"Extracted {len(conversation_pairs)} conversation pairs from {input_file}")
    
    # Check if we have enough pairs
    if len(conversation_pairs) < MIN_USER_MESSAGES:
        print(f"Warning: Only {len(conversation_pairs)} conversation pairs found. At least {MIN_USER_MESSAGES} are recommended for effective fine-tuning.")
        
        # If we have fewer than 10 pairs, duplicate them to reach the minimum
        if len(conversation_pairs) < 10:
            print(f"Duplicating pairs to reach the minimum of 10 required for fine-tuning...")
            conversation_pairs = conversation_pairs * (10 // len(conversation_pairs) + 1)
            print(f"Now have {len(conversation_pairs)} pairs after duplication.")
    
    # Extract user responses for style analysis
    user_responses = [response for _, response in conversation_pairs]
    
    # Analyze user writing style
    style_description = analyze_writing_style(user_responses)
    
    # Create system prompt
    system_prompt = f"""You are an AI clone that responds to messages as if you were the user.

You should generate NEW responses to messages as if YOU were the user responding to someone else. {style_description}

For example:
- If someone asks a question, respond as if you were the user answering that question.
- If someone greets you, respond as the user would typically greet someone.
- If someone shares information, respond how the user would typically react to that information.

Your goal is to create original responses in the user's voice and communication style.
Match their typical sentence structures, vocabulary choices, and expression styles.

NEVER respond with a verbatim copy of your LinkedIn profile or previous messages. Always generate a new, natural-sounding response that matches the user's style."""
    
    # Try to incorporate LinkedIn profile data
    professional_context = None
    linkedin_data = None
    
    # First check if we already have LinkedIn data in the training file
    try:
        with open(input_file, 'r') as f:
            training_data = json.load(f)
            if training_data.get('linkedin_integrated', False) and training_data.get('linkedin_context'):
                professional_context = training_data.get('linkedin_context')
                print("Using LinkedIn context from existing training data")
    except Exception as e:
        print(f"Error checking for existing LinkedIn data: {e}")
    
    # If we don't have LinkedIn data and should prompt for it
    if not professional_context and prompt_for_linkedin:
        try:
            # Import the LinkedIn prompt module
            from utils.linkedin_prompt import prompt_for_linkedin
            
            # Try to extract username from the training data
            username = None
            try:
                with open(input_file, 'r') as f:
                    data = json.load(f)
                    if 'user_info' in data and 'name' in data['user_info']:
                        username = data['user_info']['name']
            except Exception:
                pass  # Continue without username if there's an error
            
            # Prompt the user for their LinkedIn profile
            linkedin_data = prompt_for_linkedin(username)
            
            if linkedin_data:
                # Create professional context from LinkedIn data
                professional_context = create_professional_context(linkedin_data)
                print("Successfully extracted professional context from LinkedIn profile")
                
                # Save the LinkedIn context to the training data file for future use
                try:
                    with open(input_file, 'r') as f:
                        training_data = json.load(f)
                    
                    training_data['linkedin_integrated'] = True
                    training_data['linkedin_context'] = professional_context
                    
                    with open(input_file, 'w') as f:
                        json.dump(training_data, f, indent=2)
                    
                    print("Saved LinkedIn context to training data file")
                except Exception as e:
                    print(f"Error saving LinkedIn context to training data: {e}")
        except Exception as e:
            print(f"Error prompting for LinkedIn data: {e}")
            # Continue without LinkedIn data if there's an error
    
    # If we still don't have LinkedIn data, try to find the most recent profile
    if not professional_context:
        try:
            # Find the most recent LinkedIn profile
            linkedin_profile_path = find_latest_linkedin_profile()
            if linkedin_profile_path:
                print(f"Found LinkedIn profile: {linkedin_profile_path}")
                
                # Load the LinkedIn profile data
                linkedin_data = load_linkedin_persona(linkedin_profile_path)
                if linkedin_data:
                    # Create professional context from LinkedIn data
                    professional_context = create_professional_context(linkedin_data)
                    print("Successfully extracted professional context from LinkedIn profile")
        except Exception as e:
            print(f"Error finding LinkedIn profile: {e}")
            # Continue without LinkedIn data if there's an error
    
    # Enhance the system prompt with professional context if available
    if professional_context:
        system_prompt = enhance_system_prompt_with_linkedin(system_prompt, professional_context)
        print("Enhanced system prompt with LinkedIn professional context")
    
    print(f"System prompt: {system_prompt}")
    
    # Create training examples from conversation pairs
    fine_tuning_data = create_training_examples(conversation_pairs, system_prompt)
    
    # Add LinkedIn-specific training examples if professional context is available
    if professional_context:
        linkedin_examples = create_linkedin_training_examples(professional_context, system_prompt)
        fine_tuning_data.extend(linkedin_examples)
        print(f"Added {len(linkedin_examples)} LinkedIn-based training examples with natural responses")
    
    print(f"Created {len(fine_tuning_data)} fine-tuning examples")
    
    # Split the data into training and validation sets
    train_data, val_data = train_test_split(fine_tuning_data, train_size=train_size, random_state=42)
    
    # Save the prepared data
    train_file = f"{output_prefix}_train.jsonl"
    val_file = f"{output_prefix}_val.jsonl"
    
    # Save training data
    with open(train_file, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item) + '\n')
    
    # Save validation data
    with open(val_file, 'w', encoding='utf-8') as f:
        for item in val_data:
            f.write(json.dumps(item) + '\n')
    
    print(f"Saved {len(train_data)} examples to {train_file} (training set)")
    print(f"Saved {len(val_data)} examples to {val_file} (validation set)")
    print("The data is now ready for fine-tuning with OpenAI's API.")
    
    # Return information about the data
    return {
        "train_file": train_file,
        "val_file": val_file,
        "train_count": len(train_data),
        "val_count": len(val_data),
        "system_prompt": system_prompt
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare user message data for GPT fine-tuning")
    parser.add_argument("input_file", help="Path to the JSON file with collected user messages")
    parser.add_argument("output_prefix", help="Prefix for output files (will create prefix_train.jsonl, prefix_val.jsonl)")
    parser.add_argument("--train-size", type=float, default=0.8, help="Proportion of data to use for training (default: 0.8)")
    parser.add_argument("--val-size", type=float, default=0.2, help="Proportion of data to use for validation (default: 0.2)")
    
    args = parser.parse_args()
    
    # Verify that proportions sum to 1
    total = args.train_size + args.val_size
    if abs(total - 1.0) > 0.001:
        print(f"Warning: Train and validation proportions sum to {total}, not 1.0")
        print("Normalizing proportions...")
        args.train_size /= total
        args.val_size /= total
        print(f"Adjusted proportions: train={args.train_size:.2f}, val={args.val_size:.2f}")
    
    prepare_fine_tuning_data(
        args.input_file, 
        args.output_prefix,
        args.train_size,
        args.val_size
    )
