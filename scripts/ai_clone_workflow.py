"""
AI Clone - End-to-End Workflow

This script guides you through the entire process of creating your AI clone:
1. Collecting your Discord messages
2. Processing the data for training
3. Fine-tuning a model
4. Testing the model

Usage:
    python scripts/ai_clone_workflow.py
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime, timedelta

def run_command(command, cwd=None):
    """Run a command and return its output."""
    print(f"\n> {command}")
    result = subprocess.run(command, shell=True, cwd=cwd, 
                           capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.stderr:
        print(f"Error: {result.stderr}")
    
    return result.returncode == 0

def collect_messages(method, your_name):
    """Collect Discord messages using the specified method."""
    print("\n=== Step 1: Collecting Discord Messages ===")
    
    if method == 'bot':
        print("Using Discord bot to collect messages...")
        success = run_command("python scripts/collect_discord_data.py")
        if not success:
            print("Bot collection failed. Try another method.")
            return None
        
        # Find the most recent output file
        files = [f for f in os.listdir('data/raw') if f.startswith('discord_messages_') and f.endswith('.json')]
        if not files:
            print("No output files found.")
            return None
        
        latest_file = max(files, key=lambda x: os.path.getmtime(os.path.join('data/raw', x)))
        return os.path.join('data/raw', latest_file)
    
    elif method == 'personal':
        print("Using personal token to collect messages...")
        success = run_command("python scripts/collect_personal_dms.py")
        if not success:
            print("Personal token collection failed. Try another method.")
            return None
        
        # Find the most recent output file
        files = [f for f in os.listdir('data/raw') if f.startswith('discord_messages_') and f.endswith('.json')]
        if not files:
            print("No output files found.")
            return None
        
        latest_file = max(files, key=lambda x: os.path.getmtime(os.path.join('data/raw', x)))
        return os.path.join('data/raw', latest_file)
    
    elif method == 'manual':
        print("Using manual collection...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"data/raw/conversations_{timestamp}.txt"
        
        success = run_command(f"python scripts/collect_conversations.py --output {output_file} --your-name {your_name}")
        if not success:
            print("Manual collection failed.")
            return None
        
        return output_file
    
    elif method == 'sample':
        print("Using sample conversation...")
        return "data/raw/sample_conversation_recent.txt"
    
    else:
        print(f"Unknown collection method: {method}")
        return None

def process_data(input_file, your_name, model_name):
    """Process the collected data for training."""
    print("\n=== Step 2: Processing Data for Training ===")
    
    # Determine if this is a JSON or text file
    is_json = input_file.endswith('.json')
    
    if is_json:
        # Use prepare_training_data.py for JSON files
        output_prefix = f"models/{model_name}"
        success = run_command(f"python utils/prepare_training_data.py {input_file} {output_prefix} --min-tokens 5")
        if not success:
            print("Data processing failed.")
            return None
        
        return f"{output_prefix}_train.jsonl", f"{output_prefix}_val.jsonl"
    else:
        # Use convert_discord_chat.py for text files
        output_prefix = f"models/{model_name}"
        success = run_command(f"python scripts/convert_discord_chat.py {input_file} {output_prefix} --your-name {your_name}")
        if not success:
            print("Data conversion failed.")
            return None
        
        return f"{output_prefix}_train.jsonl", f"{output_prefix}_val.jsonl"

def fine_tune_model(train_file, val_file, model_name):
    """Fine-tune a model using the processed data."""
    print("\n=== Step 3: Fine-Tuning the Model ===")
    
    success = run_command(f"python scripts/finetune_ai_clone.py {train_file} --validation-file {val_file} --suffix {model_name}")
    if not success:
        print("Fine-tuning failed.")
        return False
    
    return True

def test_model(model_name):
    """Test the fine-tuned model."""
    print("\n=== Step 4: Testing the Model ===")
    
    # Check if we should use the actual fine-tuned model or simulate
    model_file = "models/fine_tuned_model.txt"
    if os.path.exists(model_file):
        with open(model_file, 'r') as f:
            model_id = f.read().strip()
        
        print(f"Testing fine-tuned model: {model_id}")
        run_command(f"python scripts/test_fine_tuned.py")
    else:
        print("No fine-tuned model found. Simulating responses...")
        run_command(f"python scripts/simulate_fine_tuned.py")

def main():
    parser = argparse.ArgumentParser(description="AI Clone Workflow")
    parser.add_argument("--method", choices=['bot', 'personal', 'manual', 'sample'], default='manual',
                       help="Method for collecting Discord messages")
    parser.add_argument("--your-name", default="X", help="Your name in the conversations")
    parser.add_argument("--model-name", default=None, help="Name for your fine-tuned model")
    parser.add_argument("--skip-collection", action="store_true", help="Skip the collection step")
    parser.add_argument("--skip-processing", action="store_true", help="Skip the processing step")
    parser.add_argument("--skip-fine-tuning", action="store_true", help="Skip the fine-tuning step")
    parser.add_argument("--input-file", help="Input file for processing (if skipping collection)")
    parser.add_argument("--train-file", help="Training file for fine-tuning (if skipping processing)")
    parser.add_argument("--val-file", help="Validation file for fine-tuning (if skipping processing)")
    
    args = parser.parse_args()
    
    # Set default model name if not provided
    if args.model_name is None:
        args.model_name = f"clone_{datetime.now().strftime('%Y%m%d')}"
    
    # Create necessary directories
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    # Step 1: Collect messages
    input_file = args.input_file
    if not args.skip_collection:
        input_file = collect_messages(args.method, args.your_name)
        if not input_file:
            print("Message collection failed. Exiting.")
            return
    elif not input_file:
        print("No input file specified. Use --input-file to specify a file.")
        return
    
    # Step 2: Process data
    train_file, val_file = args.train_file, args.val_file
    if not args.skip_processing:
        result = process_data(input_file, args.your_name, args.model_name)
        if not result:
            print("Data processing failed. Exiting.")
            return
        train_file, val_file = result
    elif not (train_file and val_file):
        print("No training/validation files specified. Use --train-file and --val-file.")
        return
    
    # Step 3: Fine-tune model
    if not args.skip_fine_tuning:
        success = fine_tune_model(train_file, val_file, args.model_name)
        if not success:
            print("Fine-tuning failed. Exiting.")
            return
    
    # Step 4: Test model
    test_model(args.model_name)
    
    print("\n=== Workflow Complete ===")
    print(f"Your AI clone '{args.model_name}' has been created and tested.")
    print("You can now use it in your Discord bot or other applications.")

if __name__ == "__main__":
    main()
