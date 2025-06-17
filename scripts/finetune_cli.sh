#!/bin/bash

# Fine-tuning script using OpenAI CLI
# This script uses the OpenAI CLI commands directly instead of the Python SDK

# Check if training file is provided
if [ -z "$1" ]; then
  echo "Error: Please provide a training file path"
  echo "Usage: ./finetune_cli.sh <training_file_path> [model_name]"
  exit 1
fi

# Set variables
TRAINING_FILE=$1
MODEL=${2:-"gpt-4o-mini-2024-07-18"}

# Validate that the file exists
if [ ! -f "$TRAINING_FILE" ]; then
  echo "Error: Training file not found at $TRAINING_FILE"
  exit 1
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
  # Try to load from .env file
  if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
  fi
  
  # Check again
  if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY not set. Please set it in your environment or .env file."
    exit 1
  fi
fi

echo "Starting fine-tuning process..."
echo "Training file: $TRAINING_FILE"
echo "Model: $MODEL"

# Upload the file
echo "Uploading training file..."
FILE_UPLOAD_RESPONSE=$(openai api files.create --file "$TRAINING_FILE" --purpose fine-tune)
FILE_ID=$(echo $FILE_UPLOAD_RESPONSE | grep -o '"id": "[^"]*"' | cut -d '"' -f 4)

if [ -z "$FILE_ID" ]; then
  echo "Error: Failed to upload file"
  echo "Response: $FILE_UPLOAD_RESPONSE"
  exit 1
fi

echo "File uploaded successfully with ID: $FILE_ID"

# Wait for the file to be processed
echo "Waiting for file to be processed..."
sleep 30

# Create the fine-tuning job
echo "Creating fine-tuning job..."
JOB_RESPONSE=$(openai api fine_tuning.jobs.create --training_file "$FILE_ID" --model "$MODEL")
JOB_ID=$(echo $JOB_RESPONSE | grep -o '"id": "[^"]*"' | head -1 | cut -d '"' -f 4)

if [ -z "$JOB_ID" ]; then
  echo "Error: Failed to create fine-tuning job"
  echo "Response: $JOB_RESPONSE"
  exit 1
fi

echo "Fine-tuning job created with ID: $JOB_ID"

# Check the status until it completes
echo "Fine-tuning job started. Checking status every 60 seconds..."

while true; do
  JOB_STATUS_RESPONSE=$(openai api fine_tuning.jobs.retrieve --id "$JOB_ID")
  STATUS=$(echo $JOB_STATUS_RESPONSE | grep -o '"status": "[^"]*"' | cut -d '"' -f 4)
  
  echo "Job status: $STATUS"
  
  if [ "$STATUS" == "succeeded" ]; then
    FINE_TUNED_MODEL=$(echo $JOB_STATUS_RESPONSE | grep -o '"fine_tuned_model": "[^"]*"' | cut -d '"' -f 4)
    echo "Fine-tuning completed successfully!"
    echo "Your fine-tuned model ID is: $FINE_TUNED_MODEL"
    
    # Save the model ID to a file
    echo "$FINE_TUNED_MODEL" > fine_tuned_model.txt
    echo "Model ID saved to fine_tuned_model.txt"
    break
  elif [ "$STATUS" == "failed" ] || [ "$STATUS" == "cancelled" ]; then
    echo "Fine-tuning job failed or was cancelled"
    break
  else
    echo "Waiting 60 seconds before checking again..."
    sleep 60
  fi
done
