"""
Fine-tune with GPT-4o mini

This script handles the fine-tuning process using the OpenAI API with GPT-4o mini.
It's designed to be more cost-effective and faster than using GPT-4.
"""

import os
import json
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import sys

# Add the project root to the path so we can import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.prepare_user_training_data import prepare_fine_tuning_data

# Load environment variables
load_dotenv()

# Set OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")

# Initialize OpenAI client with only the required parameters
import httpx
http_client = httpx.Client()
client = OpenAI(
    api_key=api_key,
    http_client=http_client
)

# Constants
MODEL = "gpt-4o-mini-2024-07-18"  # Use GPT-4o mini with the correct model identifier
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
TRAINING_DATA_PATH = os.path.join(DATA_DIR, 'training_data.json')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

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
            response = client.files.create(
                file=f,
                purpose='fine-tune'
            )
        
        file_id = response.id
        print(f"File uploaded successfully with ID: {file_id}")
        return file_id
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None

def create_fine_tuning_job(training_file_id, validation_file_id=None, model=MODEL):
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
        
        print(f"Creating fine-tuning job with parameters: {params}")
        
        # Handle different API versions
        try:
            response = client.fine_tuning.jobs.create(**params)
        except AttributeError:
            # Fall back to older API format if needed
            print("Falling back to older API format")
            response = client.fine_tuning.create(**params)
        
        job_id = response.id
        print(f"Fine-tuning job created with ID: {job_id}")
        return job_id
    except Exception as e:
        print(f"Error creating fine-tuning job: {e}")
        return None

def check_fine_tuning_status(job_id):
    """Check the status of a fine-tuning job."""
    try:
        # Handle different API versions
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
        except AttributeError:
            # Fall back to older API format
            print("Falling back to older API format for status check")
            response = client.fine_tuning.retrieve(job_id)
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

def update_env_file(model_id):
    """Print a message suggesting how to manually update the .env file with the new model ID."""
    try:
        # Instead of automatically updating the .env file, just print a message
        print(f"\n=== IMPORTANT: New fine-tuned model available ===")
        print(f"To use this model, run: python scripts/update_env.py MODEL_ID {model_id}")
        print(f"===========================================\n")
        
        # Save the model ID to a file for reference
        model_file = os.path.join(MODELS_DIR, 'latest_model_id.txt')
        with open(model_file, 'w') as f:
            f.write(model_id)
        print(f"Model ID saved to {model_file}")
        
        return True
    except Exception as e:
        print(f"Error saving model ID: {e}")
        return False

def run_fine_tuning(training_data_path=TRAINING_DATA_PATH, check_interval=60):
    """Run the complete fine-tuning process."""
    # Create timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_prefix = os.path.join(MODELS_DIR, f"clone_{timestamp}")
    
    # Prepare the training data
    print("Preparing training data...")
    data_info = prepare_fine_tuning_data(training_data_path, output_prefix)
    
    training_file = data_info['train_file']
    validation_file = data_info['val_file']
    
    print(f"Training data: {data_info['train_count']} examples")
    print(f"Validation data: {data_info['val_count']} examples")
    
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
    job_id = create_fine_tuning_job(training_file_id, validation_file_id, MODEL)
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
            
            # Update the .env file with the new model ID
            update_env_file(result)
            
            # Save the model ID to a file
            model_id_file = os.path.join(MODELS_DIR, 'fine_tuned_model.txt')
            with open(model_id_file, 'w') as f:
                f.write(result)
            
            print(f"Model ID saved to {model_id_file}")
            
            # Update training data status
            with open(training_data_path, 'r') as f:
                training_data = json.load(f)
            
            training_data['trained'] = True
            training_data['last_updated'] = datetime.now().isoformat()
            training_data['model_id'] = result
            training_data['system_prompt'] = data_info['system_prompt']
            
            with open(training_data_path, 'w') as f:
                json.dump(training_data, f, indent=2)
            
            print("Training data status updated.")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune a GPT model with OpenAI API")
    parser.add_argument("--training-data", default=TRAINING_DATA_PATH, help=f"Path to the training data JSON file (default: {TRAINING_DATA_PATH})")
    parser.add_argument("--check-interval", type=int, default=60, help="Interval in seconds to check job status (default: 60)")
    
    args = parser.parse_args()
    
    # Check if API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not found in .env file")
    else:
        run_fine_tuning(args.training_data, args.check_interval)
