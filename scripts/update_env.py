#!/usr/bin/env python

import os
from dotenv import load_dotenv

# Load current environment variables
load_dotenv()

# Path to .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')

# Get model ID from command line arguments or training_data.json
import sys
import json

if len(sys.argv) >= 3 and sys.argv[1] == "MODEL_ID":
    new_model_id = sys.argv[2]
    print(f"Setting model ID to: {new_model_id}")
else:
    # Read model ID from training_data.json
    try:
        training_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'training_data.json')
        with open(training_data_path, 'r') as f:
            training_data = json.load(f)
            new_model_id = training_data.get('model_id', "ft:gpt-4o-mini-2024-07-18:al43595::B8Z4EXGR")
        print(f"Using model ID from training_data.json: {new_model_id}")
    except Exception as e:
        # Fallback to latest model ID if there's an error
        new_model_id = "ft:gpt-4o-mini-2024-07-18:al43595::B8Z4EXGR"
        print(f"Error reading training_data.json: {e}")
        print(f"Using default model ID: {new_model_id}")

# Read the current .env file
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        env_lines = f.readlines()
    
    # Find and replace AI_MODEL line or add it if not found
    ai_model_found = False
    for i, line in enumerate(env_lines):
        if line.startswith('AI_MODEL='):
            env_lines[i] = f'AI_MODEL={new_model_id}\n'
            ai_model_found = True
            break
    
    if not ai_model_found:
        env_lines.append(f'AI_MODEL={new_model_id}\n')
    
    # Write updated .env file
    try:
        with open(env_path, 'w') as f:
            f.writelines(env_lines)
        # Verify the update was successful
        with open(env_path, 'r') as f:
            content = f.read()
            if f'AI_MODEL={new_model_id}' in content:
                print(f"Verified: .env file now contains the new model ID")
            else:
                print(f"Warning: Failed to verify model ID update in .env file")
                print(f"Current .env content (partial): {content[:100]}...")
        print(f"Updated .env file with new model ID: {new_model_id}")
    except Exception as e:
        print(f"Error updating .env file: {str(e)}")
else:
    print("Error: .env file not found")
