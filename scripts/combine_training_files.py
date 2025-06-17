#!/usr/bin/env python
"""
Combine multiple JSONL training files to meet the minimum example requirement.
"""

import json
import os
import argparse
from datetime import datetime

def combine_jsonl_files(input_files, output_file):
    """Combine multiple JSONL files into one."""
    examples = []
    
    # Read all examples from input files
    for file_path in input_files:
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {file_path}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    example = json.loads(line.strip())
                    examples.append(example)
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON in {file_path}")
    
    print(f"Read {len(examples)} examples from {len(input_files)} files")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write combined examples to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"Combined {len(examples)} examples into {output_file}")
    return len(examples)

def duplicate_examples(input_file, output_file, target_count):
    """Duplicate examples in a file to reach a target count."""
    examples = []
    
    # Read examples from input file
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                example = json.loads(line.strip())
                examples.append(example)
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in {input_file}")
    
    original_count = len(examples)
    print(f"Read {original_count} examples from {input_file}")
    
    if original_count == 0:
        print("Error: No examples found in input file")
        return 0
    
    # Calculate how many duplicates we need
    needed = target_count - original_count
    
    if needed <= 0:
        print(f"Already have {original_count} examples, no duplication needed")
        return original_count
    
    # Duplicate examples until we reach the target count
    duplicated_examples = []
    for i in range(needed):
        # Use modulo to cycle through the original examples
        duplicated_examples.append(examples[i % original_count])
    
    # Combine original and duplicated examples
    all_examples = examples + duplicated_examples
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write all examples to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in all_examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"Duplicated {needed} examples to reach {len(all_examples)} total examples in {output_file}")
    return len(all_examples)

def main():
    parser = argparse.ArgumentParser(description="Combine or duplicate training examples for fine-tuning")
    parser.add_argument("--input", action="append", required=True, help="Input JSONL file(s) (can specify multiple)")
    parser.add_argument("--output", help="Output JSONL file")
    parser.add_argument("--target-count", type=int, default=10, help="Target number of examples (default: 10)")
    parser.add_argument("--duplicate", action="store_true", help="Duplicate examples to reach target count")
    
    args = parser.parse_args()
    
    # Set default output file if not provided
    if args.output is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f"models/clone_combined_{timestamp}.jsonl"
    
    if args.duplicate and len(args.input) == 1:
        # Duplicate examples in a single file
        count = duplicate_examples(args.input[0], args.output, args.target_count)
    else:
        # Combine multiple files
        count = combine_jsonl_files(args.input, args.output)
        
        # If we still don't have enough examples and duplication is enabled
        if count < args.target_count and args.duplicate:
            print(f"Combined file has {count} examples, duplicating to reach {args.target_count}")
            count = duplicate_examples(args.output, args.output, args.target_count)
    
    print(f"Final example count: {count}")
    if count >= args.target_count:
        print("\nNext steps:")
        print(f"Run fine-tuning: python scripts/finetune_ai_clone.py {args.output} --suffix clone")

if __name__ == "__main__":
    main()
