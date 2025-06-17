#!/usr/bin/env python
"""
Check the status of a fine-tuning job and get detailed error information.
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from openai import OpenAI
import httpx

# Load environment variables
load_dotenv()

# Set OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

# Configure OpenAI with custom httpx client to avoid proxy issues
http_client = httpx.Client()
client = OpenAI(api_key=api_key, http_client=http_client)

def check_job_status(job_id):
    """Get detailed information about a fine-tuning job."""
    try:
        # Retrieve the job
        job = client.fine_tuning.jobs.retrieve(job_id)
        
        print(f"Job ID: {job.id}")
        print(f"Status: {job.status}")
        print(f"Created at: {job.created_at}")
        print(f"Finished at: {job.finished_at if hasattr(job, 'finished_at') else 'N/A'}")
        print(f"Model: {job.model}")
        print(f"Fine-tuned model: {job.fine_tuned_model if hasattr(job, 'fine_tuned_model') else 'N/A'}")
        
        # Check for errors
        if job.status == 'failed':
            print("\nError information:")
            if hasattr(job, 'error') and job.error:
                print(f"Error code: {job.error.code}")
                print(f"Error message: {job.error.message}")
            else:
                print("No detailed error information available.")
                
            # Get events for more details
            print("\nJob events:")
            events = client.fine_tuning.jobs.list_events(fine_tuning_job_id=job_id)
            for event in events.data:
                print(f"- {event.created_at}: {event.message}")
        
        # Check training details if available
        if hasattr(job, 'training_file'):
            print(f"\nTraining file: {job.training_file}")
        if hasattr(job, 'validation_file'):
            print(f"Validation file: {job.validation_file}")
            
        # Check hyperparameters if available
        if hasattr(job, 'hyperparameters'):
            print("\nHyperparameters:")
            for key, value in job.hyperparameters.items():
                print(f"- {key}: {value}")
                
    except Exception as e:
        print(f"Error retrieving job: {e}")

def main():
    parser = argparse.ArgumentParser(description="Check the status of a fine-tuning job")
    parser.add_argument("job_id", help="The ID of the fine-tuning job to check")
    
    args = parser.parse_args()
    check_job_status(args.job_id)

if __name__ == "__main__":
    main()
