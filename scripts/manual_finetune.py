#!/usr/bin/env python
"""
Manual Fine-tuning Script for AI Clone

This script manually starts the fine-tuning process for the AI clone
using the specified LinkedIn profile data and training messages.
"""

import os
import sys
import json
import time
from datetime import datetime
from threading import Thread
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import necessary modules
from utils.prepare_user_training_data import prepare_fine_tuning_data
from utils.linkedin_integration import load_linkedin_persona, create_professional_context

# Import OpenAI client
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Constants
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
MODELS_DIR = BASE_DIR / 'models'
TRAINING_DATA_PATH = DATA_DIR / 'training_data.json'
LINKEDIN_PROFILE_PATH = BASE_DIR / 'scrapers' / 'data' / 'linkedin_profiles' / 'albertlu_persona.json'

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# Model to use for fine-tuning
MODEL = "gpt-4o-mini-2024-07-18"  # Use GPT-4o mini with the correct model identifier

def run_fine_tuning_process(training_data_path=TRAINING_DATA_PATH, linkedin_profile_path=LINKEDIN_PROFILE_PATH):
    """Run the fine-tuning process with the specified LinkedIn profile"""
    try:
        print("Starting fine-tuning process...")
        
        # Create timestamp for output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_prefix = os.path.join(MODELS_DIR, f"clone_{timestamp}")
        
        # Load LinkedIn profile data
        print(f"Loading LinkedIn profile from {linkedin_profile_path}...")
        linkedin_data = load_linkedin_persona(linkedin_profile_path)
        
        if linkedin_data:
            print("LinkedIn profile loaded successfully.")
            
            # Create professional context from LinkedIn data
            professional_context = create_professional_context(linkedin_data)
            
            # Update training data with LinkedIn context
            with open(training_data_path, 'r') as f:
                training_data = json.load(f)
            
            training_data['linkedin_integrated'] = True
            training_data['linkedin_context'] = professional_context
            
            with open(training_data_path, 'w') as f:
                json.dump(training_data, f, indent=2)
            
            print("LinkedIn context added to training data.")
        else:
            print("Failed to load LinkedIn profile data. Continuing without LinkedIn integration.")
        
        # Prepare the training data
        print("Preparing training data...")
        data_info = prepare_fine_tuning_data(training_data_path, output_prefix, prompt_for_linkedin=False)
        
        training_file = data_info['train_file']
        validation_file = data_info.get('val_file')
        
        print(f"Training data: {data_info.get('train_count', 0)} examples")
        if validation_file:
            print(f"Validation data: {data_info.get('val_count', 0)} examples")
        
        # Upload the training file to OpenAI
        print("Uploading training file to OpenAI...")
        with open(training_file, 'rb') as f:
            response = client.files.create(
                file=f,
                purpose='fine-tune'
            )
            
        training_file_id = response.id
        print(f"Training file uploaded with ID: {training_file_id}")
        
        # Upload validation file if provided
        validation_file_id = None
        if validation_file:
            print("Uploading validation file to OpenAI...")
            with open(validation_file, 'rb') as f:
                response = client.files.create(
                    file=f,
                    purpose='fine-tune'
                )
                
            validation_file_id = response.id
            print(f"Validation file uploaded with ID: {validation_file_id}")
        
        # Wait for the file to be processed
        print("Waiting for file to be processed...")
        time.sleep(30)
        
        # Create the fine-tuning job
        print("Creating fine-tuning job...")
        params = {
            'training_file': training_file_id,
            'model': MODEL
        }
        
        if validation_file_id:
            params['validation_file'] = validation_file_id
            
        response = client.fine_tuning.jobs.create(**params)
        
        job_id = response.id
        print(f"Fine-tuning job created with ID: {job_id}")
        
        # Save the job ID to the training data
        with open(training_data_path, 'r') as f:
            training_data = json.load(f)
            
        training_data['fine_tuning_job_id'] = job_id
        training_data['fine_tuning_in_progress'] = True
        training_data['fine_tuning_started_at'] = datetime.now().isoformat()
        
        with open(training_data_path, 'w') as f:
            json.dump(training_data, f, indent=2)
            
        print("Fine-tuning process started successfully")
        return True
    except Exception as e:
        print(f"Error running fine-tuning process: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_fine_tuning():
    """Start the fine-tuning process"""
    # Check if the LinkedIn profile exists
    if not os.path.exists(LINKEDIN_PROFILE_PATH):
        print(f"LinkedIn profile not found at {LINKEDIN_PROFILE_PATH}")
        return False
    
    # Check if the training data exists
    if not os.path.exists(TRAINING_DATA_PATH):
        print(f"Training data not found at {TRAINING_DATA_PATH}")
        return False
    
    # Load training data to check message count
    with open(TRAINING_DATA_PATH, 'r') as f:
        training_data = json.load(f)
    
    # Count user messages
    user_message_count = 0
    for conversation in training_data.get('conversations', []):
        for message in conversation.get('messages', []):
            if message.get('sender') == 'user':
                user_message_count += 1
    
    print(f"Found {user_message_count} user messages in training data")
    
    if user_message_count < 10:
        print(f"Not enough user messages for fine-tuning. You have {user_message_count} messages, but at least 10 are required.")
        return False
    
    # Check if fine-tuning is already in progress
    if training_data.get('fine_tuning_in_progress', False):
        print("Fine-tuning is already in progress. Canceling previous job...")
        
        # Cancel the previous job if it exists
        job_id = training_data.get('fine_tuning_job_id')
        if job_id:
            try:
                client.fine_tuning.jobs.cancel(job_id)
                print(f"Canceled previous fine-tuning job with ID: {job_id}")
            except Exception as e:
                print(f"Error canceling previous fine-tuning job: {e}")
    
    # Start fine-tuning in the current thread (not background)
    print("Starting fine-tuning process...")
    success = run_fine_tuning_process(TRAINING_DATA_PATH, LINKEDIN_PROFILE_PATH)
    
    if success:
        print("Fine-tuning process started successfully")
        return True
    else:
        print("Failed to start fine-tuning process")
        return False

if __name__ == '__main__':
    print("Starting manual fine-tuning process...")
    success = start_fine_tuning()
    if success:
        print("Fine-tuning process initiated successfully. You can check the status in the training interface.")
    else:
        print("Failed to start fine-tuning process. Please check the logs for details.")
