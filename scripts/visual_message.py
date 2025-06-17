"""
Visual Message Sender for AI Clone

This module provides functions to visually send messages through the Messages app
using AppleScript, allowing users to see the AI typing and sending messages.
"""

import os
import subprocess
import time
from pathlib import Path

# Get the paths to the AppleScript files
SCRIPT_DIR = Path(__file__).parent.absolute()
APPLESCRIPT_PATH = SCRIPT_DIR / "visual_message_sender.applescript"
TYPE_ONLY_APPLESCRIPT_PATH = SCRIPT_DIR / "visual_message_type_only.applescript"

def send_visual_imessage(recipient, message, chat_id=None):
    """
    Send an iMessage visually through the Messages app using AppleScript.
    
    This function will open the Messages app, navigate to the conversation
    with the recipient, and visually type and send the message.
    
    Args:
        recipient: Phone number or email of the recipient
        message: Message text to send
        chat_id: Optional chat ID from the database for more reliable conversation finding
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure the recipient is a string
        recipient = str(recipient)
        
        # Remove any non-numeric characters if it looks like a phone number
        if recipient.replace('+', '').isdigit():
            # Keep the + if it exists, but remove any other non-numeric characters
            if recipient.startswith('+'):
                recipient = '+' + ''.join(c for c in recipient[1:] if c.isdigit())
            else:
                recipient = ''.join(c for c in recipient if c.isdigit())
        
        # Prepare the arguments for the AppleScript
        applescript_args = ["osascript", str(APPLESCRIPT_PATH), recipient, message]
        
        # If we have a chat_id, add it as an additional argument
        if chat_id is not None:
            applescript_args.append(str(chat_id))
            print(f"Passing chat_id {chat_id} to AppleScript for more reliable conversation finding")
        
        # Run the AppleScript
        result = subprocess.run(
            applescript_args,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Check if the script was successful
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            print(f"Message visually sent to {recipient}")
            return True
        else:
            print(f"Error sending visual message: {result.stderr or result.stdout}")
            return False
    except Exception as e:
        print(f"Exception sending visual message: {e}")
        return False

def type_visual_imessage(recipient, message, chat_id=None):
    """
    Type an iMessage visually in the Messages app without sending it.
    
    This function will open the Messages app, navigate to the conversation
    with the recipient, and visually type the message without pressing Enter.
    
    Args:
        recipient: Phone number or email of the recipient
        message: Message text to type
        chat_id: Optional chat ID from the database for more reliable conversation finding
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure the recipient is a string
        recipient = str(recipient)
        
        # Remove any non-numeric characters if it looks like a phone number
        if recipient.replace('+', '').isdigit():
            # Keep the + if it exists, but remove any other non-numeric characters
            if recipient.startswith('+'):
                recipient = '+' + ''.join(c for c in recipient[1:] if c.isdigit())
            else:
                recipient = ''.join(c for c in recipient if c.isdigit())
        
        # Prepare the arguments for the AppleScript
        applescript_args = ["osascript", str(TYPE_ONLY_APPLESCRIPT_PATH), recipient, message]
        
        # If we have a chat_id, add it as an additional argument
        if chat_id is not None:
            applescript_args.append(str(chat_id))
            print(f"Passing chat_id {chat_id} to AppleScript for more reliable conversation finding")
        
        # Run the AppleScript
        result = subprocess.run(
            applescript_args,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Check if the script was successful
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            print(f"Message visually typed (not sent) to {recipient}")
            return True
        else:
            print(f"Error typing visual message: {result.stderr or result.stdout}")
            return False
    except Exception as e:
        print(f"Exception typing visual message: {e}")
        return False

if __name__ == "__main__":
    # Test the function if run directly
    import sys
    if len(sys.argv) >= 3:
        recipient = sys.argv[1]
        message = sys.argv[2]
        send_visual_imessage(recipient, message)
    else:
        print("Usage: python visual_message.py <recipient> <message>")
