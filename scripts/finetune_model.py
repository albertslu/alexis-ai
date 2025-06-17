"""
Fine-tune GPT-4 Model with OpenAI API

This script handles the fine-tuning process using the OpenAI API.
"""

import os
import json
import time
import argparse
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    print("Error: OPENAI_API_KEY not found in .env file")
    exit(1)

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

def upload_training_file(file_path):
    """Upload the training file to OpenAI."""
    try:
        with open(file_path, 'rb') as f:
            response = openai.File.create(
                file=f,
                purpose='fine-tune'
            )
        
        file_id = response.id
        print(f"File uploaded successfully with ID: {file_id}")
        return file_id
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None

def create_fine_tuning_job(training_file_id, validation_file_id=None, model="gpt-4o-mini-2024-07-18"):
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
            
        response = openai.FineTuningJob.create(**params)
        
        job_id = response.id
        print(f"Fine-tuning job created with ID: {job_id}")
        return job_id
    except Exception as e:
        print(f"Error creating fine-tuning job: {e}")
        return None

def check_fine_tuning_status(job_id):
    """Check the status of a fine-tuning job."""
    try:
        response = openai.FineTuningJob.retrieve(job_id)
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

def run_fine_tuning(training_file, validation_file=None, model="gpt-4o-mini-2024-07-18", check_interval=60):
    """Run the complete fine-tuning process."""
    # Validate the training file
    if not validate_training_file(training_file):
        return
    
    # Upload the training file
    training_file_id = upload_training_file(training_file)
    if not training_file_id:
        return
        
    # Upload the validation file if provided
    validation_file_id = None
    if validation_file:
        validation_file_id = upload_training_file(validation_file)
        if not validation_file_id:
            print("Warning: Failed to upload validation file. Proceeding without validation.")
    
    # Wait for the file to be processed
    print("Waiting for file to be processed...")
    time.sleep(30)
    
    # Create the fine-tuning job
    job_id = create_fine_tuning_job(training_file_id, validation_file_id, model)
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
            with open('fine_tuned_model.txt', 'w') as f:
                f.write(result)
            
            print("Model ID saved to fine_tuned_model.txt")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune a GPT model with OpenAI API")
    parser.add_argument("training_file", help="Path to the JSONL training file")
    parser.add_argument("--validation-file", help="Path to the JSONL validation file (optional)")
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18", help="Base model to fine-tune (default: gpt-4o-mini-2024-07-18)")
    parser.add_argument("--check-interval", type=int, default=60, help="Interval in seconds to check job status (default: 60)")
    
    args = parser.parse_args()
    
    # Check if API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not found in .env file")
    else:
        run_fine_tuning(args.training_file, args.validation_file, args.model, args.check_interval)
