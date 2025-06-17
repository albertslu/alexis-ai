#!/usr/bin/env python
"""
Count tokens in JSONL files for fine-tuning.
"""

import json
import sys
import os

def count_tokens(file_path):
    """Count approximate tokens in a JSONL file."""
    total_tokens = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            for msg in data['messages']:
                # Rough estimate: 1 token ≈ 0.75 words
                words = len(msg['content'].split())
                tokens = int(words / 0.75)  # More accurate estimate
                total_tokens += tokens
    
    return total_tokens

def main():
    if len(sys.argv) < 2:
        print("Usage: python count_tokens.py <jsonl_file>")
        return
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return
    
    tokens = count_tokens(file_path)
    print(f"Estimated tokens in {file_path}: {tokens}")
    
    # Calculate approximate cost for GPT-4 fine-tuning
    # Using $25 per million tokens for training
    cost = (tokens / 1000000) * 25
    print(f"Estimated fine-tuning cost: ${cost:.2f}")

if __name__ == "__main__":
    main()
