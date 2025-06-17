"""
Fine-tune an AI Clone

This script streamlines the process of fine-tuning a model on your Discord messages.
It handles the entire pipeline from data preparation to model fine-tuning.
"""

import os
import sys
import json
import time
import argparse
from dotenv import load_dotenv
import openai
from openai import OpenAI
from datetime import datetime

# Load environment variables
load_dotenv()

# Set OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

# Configure OpenAI with custom httpx client to avoid proxy issues
import httpx
http_client = httpx.Client()
client = OpenAI(api_key=api_key, http_client=http_client)

def validate_jsonl_file(file_path):
    """Validate a JSONL file for fine-tuning."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    
    try:
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
        
        print(f"File validated successfully with {line_count} examples")
        return True
    except Exception as e:
        print(f"Error validating file: {e}")
        return False

def upload_file(file_path, purpose="fine-tune"):
    """Upload a file to OpenAI."""
    try:
        with open(file_path, 'rb') as f:
            response = client.files.create(
                file=f,
                purpose=purpose
            )
        
        file_id = response.id
        print(f"File uploaded successfully with ID: {file_id}")
        return file_id
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None

def create_fine_tuning_job(training_file_id, validation_file_id=None, model="gpt-4o-mini-2024-07-18", suffix=None):
    """Create a fine-tuning job."""
    try:
        # Prepare parameters
        params = {
            'training_file': training_file_id,
            'model': model
        }
        
        # Add validation file if provided
        if validation_file_id:
            params['validation_file'] = validation_file_id
            
        # Add suffix if provided
        if suffix:
            params['suffix'] = suffix
            
        response = client.fine_tuning.jobs.create(**params)
        
        job_id = response.id
        print(f"Fine-tuning job created with ID: {job_id}")
        return job_id
    except Exception as e:
        print(f"Error creating fine-tuning job: {e}")
        return None

def check_fine_tuning_status(job_id):
    """Check the status of a fine-tuning job."""
    try:
        response = client.fine_tuning.jobs.retrieve(job_id)
        status = response.status
        
        print(f"Job status: {status}")
        
        if status == 'succeeded':
            fine_tuned_model = response.fine_tuned_model
            print(f"Fine-tuned model ID: {fine_tuned_model}")
            return fine_tuned_model
        elif status in ['failed', 'cancelled']:
            print("Fine-tuning job failed or was cancelled")
            return None
        else:
            return False  # Still in progress
    except Exception as e:
        print(f"Error checking fine-tuning status: {e}")
        return None

def run_fine_tuning(training_file, validation_file=None, model="gpt-4o-mini-2024-07-18", suffix=None, check_interval=60):
    """Run the complete fine-tuning process."""
    # Validate the training file
    if not validate_jsonl_file(training_file):
        return
    
    # Validate the validation file if provided
    if validation_file and not validate_jsonl_file(validation_file):
        print("Warning: Validation file is invalid. Proceeding without validation.")
        validation_file = None
    
    # Upload the training file
    training_file_id = upload_file(training_file)
    if not training_file_id:
        return
        
    # Upload the validation file if provided
    validation_file_id = None
    if validation_file:
        validation_file_id = upload_file(validation_file)
        if not validation_file_id:
            print("Warning: Failed to upload validation file. Proceeding without validation.")
    
    # Wait for the file to be processed
    print("Waiting for file to be processed...")
    time.sleep(30)
    
    # Create the fine-tuning job
    job_id = create_fine_tuning_job(training_file_id, validation_file_id, model, suffix)
    if not job_id:
        return
    
    # Check the status until it completes
    print(f"Fine-tuning job started. Checking status every {check_interval} seconds...")
    
    while True:
        result = check_fine_tuning_status(job_id)
        
        if result is None:
            # Job failed or was cancelled
            break
        elif result is False:
            # Job still in progress
            print(f"Waiting {check_interval} seconds before checking again...")
            time.sleep(check_interval)
        else:
            # Job succeeded, result contains the model ID
            print(f"Fine-tuning completed successfully!")
            print(f"Your fine-tuned model ID is: {result}")
            
            # Save the model ID to a file
            model_file = os.path.join('models', 'fine_tuned_model.txt')
            os.makedirs(os.path.dirname(model_file), exist_ok=True)
            with open(model_file, 'w') as f:
                f.write(result)
            
            # Also update .env file
            update_env_with_model(result)
            
            print(f"Model ID saved to {model_file} and updated in .env file")
            break

def update_env_with_model(model_id):
    """Print a message suggesting how to manually update the .env file with the new model ID."""
    # Instead of automatically updating the .env file, just print a message
    print(f"\n=== IMPORTANT: New fine-tuned model available ===")
    print(f"To use this model, run: python scripts/update_env.py MODEL_ID {model_id}")
    print(f"===========================================\n")
    
    # Save the model ID to a file for reference
    models_dir = os.path.join(os.getcwd(), 'models')
    os.makedirs(models_dir, exist_ok=True)
    model_file = os.path.join(models_dir, 'latest_model_id.txt')
    
    with open(model_file, 'w') as f:
        f.write(model_id)
    
    print(f"Model ID saved to {model_file}")

def main():
    parser = argparse.ArgumentParser(description="Fine-tune an AI Clone")
    parser.add_argument("training_file", help="Path to the JSONL training file")
    parser.add_argument("--validation-file", help="Path to the JSONL validation file (optional)")
    parser.add_argument("--model", default="gpt-4o-2024-08-06", help="Base model to fine-tune (default: gpt-4o-2024-08-06)")
    parser.add_argument("--suffix", help="Suffix for the fine-tuned model name (e.g., 'shaco')")
    parser.add_argument("--check-interval", type=int, default=60, help="Interval in seconds to check job status (default: 60)")
    
    args = parser.parse_args()
    
    # Generate a default suffix if not provided
    if not args.suffix:
        args.suffix = f"clone_{datetime.now().strftime('%Y%m%d')}"
    
    print(f"=== Fine-tuning AI Clone: {args.suffix} ===")
    run_fine_tuning(args.training_file, args.validation_file, args.model, args.suffix, args.check_interval)

if __name__ == "__main__":
    main()
