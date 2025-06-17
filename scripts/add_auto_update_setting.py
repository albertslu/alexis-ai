#!/usr/bin/env python

import os
import sys

def add_auto_update_setting(value='false'):
    """Add AUTO_UPDATE_MODEL setting to .env file"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    
    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}")
        return False
    
    # Read the current .env file
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    # Check if AUTO_UPDATE_MODEL already exists
    if 'AUTO_UPDATE_MODEL=' in env_content:
        # Replace existing setting
        lines = env_content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith('AUTO_UPDATE_MODEL='):
                new_lines.append(f"AUTO_UPDATE_MODEL={value}")
            else:
                new_lines.append(line)
        new_content = '\n'.join(new_lines)
    else:
        # Add new setting at the end
        new_content = env_content
        if not new_content.endswith('\n'):
            new_content += '\n'
        new_content += f"AUTO_UPDATE_MODEL={value}\n"
    
    # Write the updated content back to .env
    with open(env_path, 'w') as f:
        f.write(new_content)
    
    print(f"Added AUTO_UPDATE_MODEL={value} to .env file")
    return True

if __name__ == "__main__":
    value = 'false'  # Default to false
    if len(sys.argv) > 1:
        value = sys.argv[1].lower()
    
    add_auto_update_setting(value)
