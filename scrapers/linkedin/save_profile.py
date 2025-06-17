#!/usr/bin/env python
"""
Save LinkedIn profile data from terminal output to a file.

This script extracts JSON data from terminal output and saves it to a file.
It's designed to be used after running the LinkedIn scraper, which outputs
profile data to the terminal but may have issues saving it directly.
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
                # Clean up the match to handle potential issues
                json_str = match if '{' in match else match
                # Remove any leading/trailing whitespace or quotes
                json_str = json_str.strip().strip('"\'')
                # Try to parse as JSON
                data = json.loads(json_str)
                # Verify it's a LinkedIn profile by checking for expected keys
                if "basic_info" in data:
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

def extract_from_clipboard():
    """
    Extract profile data from clipboard
    
    Returns:
        dict: Extracted profile data or None if not found
    """
    try:
        import pyperclip
        clipboard_text = pyperclip.paste()
        return extract_json_from_text(clipboard_text)
    except ImportError:
        print("pyperclip not installed. Cannot extract from clipboard.")
        return None

def main():
    parser = argparse.ArgumentParser(description="Save LinkedIn profile data from terminal output")
    parser.add_argument("--input", help="Input file containing terminal output (default: stdin)")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--clipboard", action="store_true", help="Extract from clipboard instead of stdin/file")
    
    args = parser.parse_args()
    
    # Get profile data from clipboard, file, or stdin
    profile_data = None
    
    if args.clipboard:
        print("Extracting profile data from clipboard...")
        profile_data = extract_from_clipboard()
    elif args.input:
        print(f"Reading from file: {args.input}")
        with open(args.input, 'r') as f:
            text = f.read()
        profile_data = extract_json_from_text(text)
    else:
        print("Paste the terminal output containing JSON data (Ctrl+D to finish):")
        text = sys.stdin.read()
        profile_data = extract_json_from_text(text)
    
    # Save the profile data if found
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
