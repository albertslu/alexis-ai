#!/usr/bin/env python3
"""
Fine-tune GPT-4 Model with OpenAI API (v2)

This script handles the fine-tuning process using the latest OpenAI API.
"""

import os
import json
import time
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

def validate_training_file(file_path):
    """Validate the training file format."""
    with open(file_path, 'r', encoding='utf-8') as f:
        line_count = 0
        for line in f:
            line_count += 1
            try:
                data = json.loads(line)
                # Check if the data has the expected structure
                if 'messages' not in data:
                    print(f"Error in line {line_count}: 'messages' field missing")
                    return False
                
                messages = data['messages']
                if not isinstance(messages, list) or len(messages) < 2:
                    print(f"Error in line {line_count}: 'messages' should be a list with at least 2 items")
                    return False
                
                for msg in messages:
                    if 'role' not in msg or 'content' not in msg:
                        print(f"Error in line {line_count}: message missing 'role' or 'content'")
                        return False
                    
                    if msg['role'] not in ['system', 'user', 'assistant']:
                        print(f"Error in line {line_count}: invalid role '{msg['role']}'")
                        return False
            except json.JSONDecodeError:
                print(f"Error in line {line_count}: Invalid JSON")
                return False
    
    print(f"Training file validated successfully with {line_count} examples")
    return True

def run_fine_tuning(training_file, model="gpt-4o-mini-2024-07-18", check_interval=60):
    """Run the complete fine-tuning process."""
    # Validate the training file
    if not validate_training_file(training_file):
        return
    
    # Initialize OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env file")
        return
    
    client = OpenAI(api_key=api_key)
    
    # Upload the training file
    try:
        with open(training_file, 'rb') as f:
            print("Uploading training file...")
            upload_response = client.files.create(
                file=f,
                purpose="fine-tune"
            )
        file_id = upload_response.id
        print(f"File uploaded successfully with ID: {file_id}")
    except Exception as e:
        print(f"Error uploading file: {e}")
        return
    
    # Wait for the file to be processed
    print("Waiting for file to be processed...")
    time.sleep(30)
    
    # Create the fine-tuning job
    try:
        print(f"Creating fine-tuning job with model: {model}...")
        ft_response = client.fine_tuning.jobs.create(
            training_file=file_id,
            model=model
        )
        job_id = ft_response.id
        print(f"Fine-tuning job created with ID: {job_id}")
    except Exception as e:
        print(f"Error creating fine-tuning job: {e}")
        return
    
    # Check the status until it completes
    print(f"Fine-tuning job started. Checking status every {check_interval} seconds...")
    
    while True:
        try:
            job_response = client.fine_tuning.jobs.retrieve(job_id)
            status = job_response.status
            print(f"Job status: {status}")
            
            if status == 'succeeded':
                fine_tuned_model = job_response.fine_tuned_model
                print(f"Fine-tuning completed successfully!")
                print(f"Your fine-tuned model ID is: {fine_tuned_model}")
                
                # Save the model ID to a file
                with open('fine_tuned_model.txt', 'w') as f:
                    f.write(fine_tuned_model)
                
                print("Model ID saved to fine_tuned_model.txt")
                
                # Print message about manually updating the .env file
                print(f"\n=== IMPORTANT: New fine-tuned model available ===")
                print(f"To use this model, run: python scripts/update_env.py MODEL_ID {fine_tuned_model}")
                print(f"===========================================\n")
                break
            elif status in ['failed', 'cancelled']:
                print("Fine-tuning job failed or was cancelled")
                break
            else:
                # Job still in progress
                print(f"Waiting {check_interval} seconds before checking again...")
                time.sleep(check_interval)
        except Exception as e:
            print(f"Error checking fine-tuning status: {e}")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune a GPT model with OpenAI API")
    parser.add_argument("training_file", help="Path to the JSONL training file")
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18", help="Base model to fine-tune (default: gpt-4o-mini-2024-07-18)")
    parser.add_argument("--check-interval", type=int, default=60, help="Interval in seconds to check job status (default: 60)")
    
    args = parser.parse_args()
    run_fine_tuning(args.training_file, args.model, args.check_interval)
