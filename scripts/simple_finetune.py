#!/usr/bin/env python3
"""
Simple Fine-tuning Script for OpenAI API

This script uses minimal dependencies to start a fine-tuning job.
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

# Set up headers for API requests
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

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

def upload_file(file_path):
    """Upload a file to OpenAI API."""
    print(f"Uploading file: {file_path}")
    
    url = "https://api.openai.com/v1/files"
    
    with open(file_path, 'rb') as f:
        files = {
            'file': (os.path.basename(file_path), f, 'application/json'),
            'purpose': (None, 'fine-tune')
        }
        
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            files=files
        )
    
    if response.status_code == 200:
        data = response.json()
        file_id = data['id']
        print(f"File uploaded successfully with ID: {file_id}")
        return file_id
    else:
        print(f"Error uploading file: {response.status_code}")
        print(response.text)
        return None

def create_fine_tuning_job(file_id, model="gpt-4o-mini-2024-07-18"):
    """Create a fine-tuning job."""
    print(f"Creating fine-tuning job with model: {model}")
    
    url = "https://api.openai.com/v1/fine_tuning/jobs"
    
    payload = {
        "training_file": file_id,
        "model": model
    }
    
    response = requests.post(
        url,
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        job_id = data['id']
        print(f"Fine-tuning job created with ID: {job_id}")
        return job_id
    else:
        print(f"Error creating fine-tuning job: {response.status_code}")
        print(response.text)
        return None

def check_fine_tuning_status(job_id):
    """Check the status of a fine-tuning job."""
    url = f"https://api.openai.com/v1/fine_tuning/jobs/{job_id}"
    
    response = requests.get(
        url,
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        status = data['status']
        
        print(f"Job status: {status}")
        
        if status == 'succeeded':
            fine_tuned_model = data['fine_tuned_model']
            print(f"Fine-tuned model ID: {fine_tuned_model}")
            return fine_tuned_model
        elif status in ['failed', 'cancelled']:
            print("Fine-tuning job failed or was cancelled")
            if 'error' in data:
                print(f"Error: {data['error']}")
            return None
        else:
            return False  # Still in progress
    else:
        print(f"Error checking fine-tuning status: {response.status_code}")
        print(response.text)
        return None

def main():
    """Main function to run the fine-tuning process."""
    if len(sys.argv) < 2:
        print("Usage: python simple_finetune.py <training_file> [model]")
        sys.exit(1)
    
    training_file = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "gpt-4o-mini-2024-07-18"
    
    # Validate the training file
    if not validate_training_file(training_file):
        sys.exit(1)
    
    # Upload the file
    file_id = upload_file(training_file)
    if not file_id:
        sys.exit(1)
    
    # Wait for the file to be processed
    print("Waiting for file to be processed...")
    time.sleep(30)
    
    # Create the fine-tuning job
    job_id = create_fine_tuning_job(file_id, model)
    if not job_id:
        sys.exit(1)
    
    # Check the status until it completes
    print("Fine-tuning job started. Checking status every 60 seconds...")
    
    while True:
        result = check_fine_tuning_status(job_id)
        
        if result is None:
            # Job failed or was cancelled
            break
        elif result is False:
            # Job still in progress
            print("Waiting 60 seconds before checking again...")
            time.sleep(60)
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
    main()
