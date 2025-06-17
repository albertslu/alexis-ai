#!/usr/bin/env python3

"""
Training Data Enhancement Tool for AI Clone

This script enhances the training data for the AI clone by adding more diverse examples
and removing repetitive patterns that might lead to the AI repeating user messages.
"""

import os
import json
import re
from datetime import datetime
import argparse
import random

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
TRAINING_DATA_PATH = os.path.join(DATA_DIR, 'training_data.json')
MODEL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_config.json')

def is_repetitive_example(user_message, assistant_message):
    """
    Check if an example shows repetition between user and assistant messages.
    
    Args:
        user_message: User message
        assistant_message: Assistant message
        
    Returns:
        bool: True if repetitive, False otherwise
    """
    # Convert to lowercase
    user_lower = user_message.lower()
    assistant_lower = assistant_message.lower()
    
    # Check for exact repetition
    if user_lower == assistant_lower:
        return True
        
    # Check if assistant message contains the entire user message
    if len(user_message.split()) > 2 and user_lower in assistant_lower:
        return True
        
    # Check if assistant message starts with the user message
    if assistant_lower.startswith(user_lower) and len(user_message.split()) > 1:
        return True
        
    # Calculate word overlap
    user_words = set(re.sub(r'[^\w\s]', '', user_lower).split())
    assistant_words = set(re.sub(r'[^\w\s]', '', assistant_lower).split())
    
    if user_words and assistant_words:
        overlap = len(user_words.intersection(assistant_words))
        similarity = overlap / min(len(user_words), len(assistant_words))
        
        # High similarity threshold
        if similarity > 0.8:
            return True
    
    return False

def enhance_training_data(training_data_path=TRAINING_DATA_PATH, dry_run=True):
    """
    Enhance training data by removing repetitive examples and adding diverse examples.
    
    Args:
        training_data_path: Path to training data JSON file
        dry_run: If True, don't actually modify the file
        
    Returns:
        dict: Enhancement results
    """
    try:
        with open(training_data_path, 'r') as f:
            training_data = json.load(f)
    except Exception as e:
        print(f"Error loading training data: {str(e)}")
        return {}
        
    # Results tracking
    results = {
        'original_example_count': 0,
        'removed_examples': 0,
        'added_examples': 0,
        'final_example_count': 0
    }
    
    # Process each message type
    for message_type in training_data.get('message_types', []):
        examples = message_type.get('examples', [])
        results['original_example_count'] += len(examples)
        
        # Filter out repetitive examples
        filtered_examples = []
        for example in examples:
            user_message = example.get('user_message', '')
            assistant_message = example.get('assistant_message', '')
            
            if not is_repetitive_example(user_message, assistant_message):
                filtered_examples.append(example)
            else:
                results['removed_examples'] += 1
                
        # Add new diverse examples for text messages
        if message_type.get('type') == 'text':
            new_examples = generate_diverse_text_examples()
            filtered_examples.extend(new_examples)
            results['added_examples'] += len(new_examples)
            
        # Update examples
        message_type['examples'] = filtered_examples
        results['final_example_count'] += len(filtered_examples)
    
    # Save enhanced training data if not dry run
    if not dry_run:
        # Create backup
        backup_path = f"{training_data_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            with open(backup_path, 'w') as f:
                json.dump(training_data, f, indent=2)
            print(f"Created backup at {backup_path}")
        except Exception as e:
            print(f"Error creating backup: {str(e)}")
            return results
            
        # Save enhanced training data
        try:
            with open(training_data_path, 'w') as f:
                json.dump(training_data, f, indent=2)
            print(f"Saved enhanced training data with {results['final_example_count']} examples")
        except Exception as e:
            print(f"Error saving enhanced training data: {str(e)}")
    else:
        print(f"Dry run: Would save enhanced training data with {results['final_example_count']} examples")
    
    return results

def generate_diverse_text_examples():
    """
    Generate diverse text message examples that demonstrate good responses.
    
    Returns:
        list: New examples
    """
    # Examples focusing on follow-up questions and avoiding repetition
    examples = [
        {
            "user_message": "why?",
            "assistant_message": "i thought it would be more efficient that way",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "how?",
            "assistant_message": "just using that new api they released",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "when?",
            "assistant_message": "probably tomorrow afternoon",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "who?",
            "assistant_message": "alex from the design team",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "what?",
            "assistant_message": "that new project we discussed last week",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "where?",
            "assistant_message": "at the coffee shop on 5th street",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "really?",
            "assistant_message": "yeah i was surprised too",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "how are you?",
            "assistant_message": "doing pretty good! just finished a project. you?",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "what are you up to?",
            "assistant_message": "just working on some code and grabbing coffee",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "hey",
            "assistant_message": "what's up!",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "hi",
            "assistant_message": "hey there! how's it going",
            "timestamp": datetime.now().isoformat()
        },
        {
            "user_message": "hello",
            "assistant_message": "hey! what's new",
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    return examples

def update_model_config(model_config_path=MODEL_CONFIG_PATH, dry_run=True):
    """
    Update model configuration to ensure it's using the text message model.
    
    Args:
        model_config_path: Path to model config JSON file
        dry_run: If True, don't actually modify the file
        
    Returns:
        bool: True if updated, False otherwise
    """
    try:
        with open(model_config_path, 'r') as f:
            model_config = json.load(f)
    except Exception as e:
        print(f"Error loading model config: {str(e)}")
        return False
        
    # Check if already using text message model
    if model_config.get('fine_tuned_model') == "ft:gpt-4o-mini-2024-07-18:al43595::B8xsWQwN":
        print("Model config already using text message model")
        return True
        
    # Update to use text message model
    model_config['fine_tuned_model'] = "ft:gpt-4o-mini-2024-07-18:al43595::B8xsWQwN"
    
    # Save updated config if not dry run
    if not dry_run:
        # Create backup
        backup_path = f"{model_config_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            with open(backup_path, 'w') as f:
                json.dump(model_config, f, indent=2)
            print(f"Created backup at {backup_path}")
        except Exception as e:
            print(f"Error creating backup: {str(e)}")
            return False
            
        # Save updated config
        try:
            with open(model_config_path, 'w') as f:
                json.dump(model_config, f, indent=2)
            print(f"Updated model config to use text message model")
        except Exception as e:
            print(f"Error saving model config: {str(e)}")
            return False
    else:
        print(f"Dry run: Would update model config to use text message model")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Training Data Enhancement Tool for AI Clone')
    parser.add_argument('--enhance', action='store_true', help='Enhance training data')
    parser.add_argument('--update-config', action='store_true', help='Update model config')
    parser.add_argument('--no-dry-run', action='store_true', help='Actually modify the files (not just simulate)')
    parser.add_argument('--training-data', type=str, default=TRAINING_DATA_PATH, help='Path to training data')
    parser.add_argument('--model-config', type=str, default=MODEL_CONFIG_PATH, help='Path to model config')
    
    args = parser.parse_args()
    
    # Default to enhance if no action specified
    if not (args.enhance or args.update_config):
        args.enhance = True
        args.update_config = True
        
    # Enhance training data
    if args.enhance:
        print(f"Enhancing training data at {args.training_data}...")
        results = enhance_training_data(args.training_data, dry_run=not args.no_dry_run)
        
        print(f"\nEnhancement Results:")
        print(f"Original example count: {results.get('original_example_count', 0)}")
        print(f"Removed repetitive examples: {results.get('removed_examples', 0)}")
        print(f"Added diverse examples: {results.get('added_examples', 0)}")
        print(f"Final example count: {results.get('final_example_count', 0)}")
    
    # Update model config
    if args.update_config:
        print(f"\nUpdating model config at {args.model_config}...")
        update_model_config(args.model_config, dry_run=not args.no_dry_run)

if __name__ == "__main__":
    main()
