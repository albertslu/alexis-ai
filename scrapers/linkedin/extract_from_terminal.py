#!/usr/bin/env python
"""
Extract LinkedIn profile data from terminal output and save it to a file.

This script is a simple utility to extract JSON data from terminal output
and save it to a file, avoiding the complexity of the main scraper.
"""

import json
import sys
import os
import re
import argparse
from pathlib import Path

def extract_json_from_text(text):
    """
    Extract JSON data from text using regex patterns
    
    Args:
        text (str): Text containing JSON data
        
    Returns:
        dict: Extracted JSON data or None if not found
    """
    # Try to find JSON data in the text using various patterns
    json_patterns = [
        r'```json\s*(.*?)\s*```',  # JSON in code block
        r'\{[\s\S]*"basic_info"[\s\S]*\}',  # Any JSON containing basic_info
        r'\{[\s\S]*"name"[\s\S]*\}'  # Any JSON containing name
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                json_str = match if '{' in match else match
                data = json.loads(json_str)
                # Verify it's a LinkedIn profile by checking for expected keys
                if "basic_info" in data and "experience" in data:
                    return data
            except json.JSONDecodeError:
                continue
    
    return None

def save_profile_data(profile_data, output_path):
    """
    Save profile data to a file
    
    Args:
        profile_data (dict): Profile data to save
        output_path (str): Path to save the data to
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write the data to the file
        with open(output_path, 'w') as f:
            json.dump(profile_data, indent=2, fp=f)
        
        print(f"Profile data saved to {output_path}")
        return True
    except Exception as e:
        print(f"Error saving profile data: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Extract LinkedIn profile data from terminal output")
    parser.add_argument("--input", help="Input file containing terminal output (default: stdin)")
    parser.add_argument("--output", required=True, help="Output file path")
    
    args = parser.parse_args()
    
    # Read input from file or stdin
    if args.input:
        with open(args.input, 'r') as f:
            text = f.read()
    else:
        print("Paste the terminal output containing JSON data (Ctrl+D to finish):")
        text = sys.stdin.read()
    
    # Extract JSON data from the text
    profile_data = extract_json_from_text(text)
    
    if profile_data:
        print("Successfully extracted profile data:")
        print(json.dumps(profile_data, indent=2))
        
        # Save the profile data
        save_profile_data(profile_data, args.output)
    else:
        print("No valid LinkedIn profile data found in the input")
        sys.exit(1)

if __name__ == "__main__":
    main()
