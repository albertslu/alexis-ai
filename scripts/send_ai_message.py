#!/usr/bin/env python3

import subprocess
import sys
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Backend API URL
API_URL = os.environ.get('API_URL', 'http://localhost:5002')

def send_imessage_visual(recipient, message):
    """
    Send an iMessage using AppleScript with visual control of the Messages app
    for screen recording purposes.
    
    Args:
        recipient: Phone number or email associated with iMessage
        message: Text content to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Escape double quotes in the message for AppleScript
    message = message.replace('"', '\\"')
    # Replace newlines with spaces
    message = message.replace('\n', ' ')
    
    # Format the recipient properly (ensure it has the country code if it's a phone number)
    if recipient.isdigit() and len(recipient) == 10:
        # Add US country code if it's a 10-digit number without country code
        formatted_recipient = "+1" + recipient
    else:
        formatted_recipient = recipient
    
    print(f"Using recipient: {formatted_recipient}")
    
    # This script will:
    # 1. Activate the Messages app (brings it to the foreground)
    # 2. Create a new message to the recipient if not already open
    # 3. Type the message character by character (with a slight delay for visual effect)
    # 4. Send the message
    applescript = f'''
    tell application "Messages"
        activate
        delay 1 -- Wait for app to come to foreground
        
        -- Create a new message using the New Message button
        tell application "System Events"
            tell process "Messages"
                -- Click the compose button (new message)
                click button 1 of window 1
                delay 1
                
                -- Type the recipient
                keystroke "{formatted_recipient}"
                delay 1
                keystroke return
                delay 1
            end tell
        end tell
        
        -- Type the message character by character with slight delay
        tell application "System Events"
            set messageText to "{message}"
            repeat with i from 1 to length of messageText
                keystroke (character i of messageText)
                delay 0.05 -- Slightly slower typing speed to make it more visible
            end repeat
            delay 0.5 -- Pause before sending
            keystroke return -- Send the message
        end tell
    end tell
    '''
    
    try:
        result = subprocess.run(['osascript', '-e', applescript], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        print("Message sent successfully with visual control!")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr
        print(f"Error sending message: {error_msg}")
        
        # Check for common accessibility permission errors
        if "is not allowed to send keystrokes" in error_msg:
            print("\nMacOS Security Permission Error: Terminal needs Accessibility permissions")
            print("To fix this:\n1. Go to System Preferences > Security & Privacy > Privacy > Accessibility")
            print("2. Click the lock icon to make changes (enter your password)")
            print("3. Add Terminal to the list of allowed apps")
            print("\nAlternatively, you can use background mode which doesn't require these permissions:")
            print("python scripts/send_ai_message.py <recipient> \"<context>\" background")
            
            # Try to fall back to background mode
            print("Attempting to fall back to background mode...")
            return send_imessage_background(recipient, message)
            
        return False
        
def send_imessage_background(recipient, message):
    """
    Send an iMessage using AppleScript in the background (no visual)
    
    Args:
        recipient: Phone number or email associated with iMessage
        message: Text content to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Escape double quotes in the message for AppleScript
    message = message.replace('"', '\\"')
    
    # Format the recipient properly (ensure it has the country code if it's a phone number)
    if recipient.isdigit() and len(recipient) == 10:
        # Add US country code if it's a 10-digit number without country code
        formatted_recipient = "+1" + recipient
    else:
        formatted_recipient = recipient
    
    print(f"Using recipient: {formatted_recipient}")
    
    # Simple background mode that won't interfere with other applications
    applescript = f'''
    tell application "Messages"
        -- Send the message without activating the app
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{formatted_recipient}" of targetService
        send "{message}" to targetBuddy
    end tell
    '''
    
    try:
        result = subprocess.run(['osascript', '-e', applescript], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        print("Message sent successfully in background!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error sending message: {e.stderr}")
        return False
        


# Default function to use for sending messages
send_imessage = send_imessage_visual  # Change to send_imessage_background if you don't want visual

def generate_message(context, recipient=None):
    """
    Generate a message using your AI clone API
    
    Args:
        context: The context or subject of the message
        recipient: Optional recipient information
    
    Returns:
        str: Generated message text
    """
    # Check if backend is running
    try:
        # Use the draft-message endpoint specifically for text messages
        response = requests.post(f"{API_URL}/api/draft-message", json={
            'context': context,
            'recipient': recipient or '',
            'formality': 'casual',  # casual, professional, formal
        }, timeout=10)
        
        if response.status_code == 200:
            return response.json()['draft']
        else:
            print(f"Error from API: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to backend at {API_URL}")
        print("Make sure the backend server is running.")
        return None

def main():
    # Check if backend is running
    try:
        requests.get(f"{API_URL}/api", timeout=2)
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to backend at {API_URL}")
        print("Please start the backend server first with:")
        print("cd backend && python app.py")
        return
    
    # Declare global variable at the beginning of the function
    global send_imessage
    
    # Interactive mode if no arguments provided
    if len(sys.argv) < 3:
        print("AI Clone iMessage Sender")
        print("=======================")
        print("This tool allows your AI clone to send iMessages on your behalf.")
        print("Perfect for screen recording demos of AI controlling your Messages app!\n")
        
        # Choose visual or background mode
        mode = input("Choose mode (visual/background) [visual]: ").lower()
        
        # Check if user accidentally entered a phone number instead of mode
        if mode.isdigit() and len(mode) >= 10:
            print(f"\nNOTE: It looks like you entered a phone number ({mode}) for the mode.\n")
            print("Let's use that as your recipient and default to visual mode.\n")
            recipient = mode
            send_imessage = send_imessage_visual
            print("Using visual mode - Messages app will open and type visibly\n")
            print("TIP: Start your screen recording now to capture the AI typing!\n")
        elif mode == "background":
            send_imessage = send_imessage_background
            print("Using background mode - no visual typing\n")
        else:
            send_imessage = send_imessage_visual
            print("Using visual mode - Messages app will open and type visibly\n")
            print("TIP: Start your screen recording now to capture the AI typing!\n")
        
        # Only ask for recipient if not already set from phone number detection
        if 'recipient' not in locals():
            recipient = input("Enter recipient (phone or email): ")
        context = input("What do you want to message about? ")
    else:
        # Command line arguments
        recipient = sys.argv[1]
        context = sys.argv[2]
        
        # Check for visual/background flag
        if len(sys.argv) > 3 and sys.argv[3].lower() == "background":
            send_imessage = send_imessage_background
            print("Using background mode - no visual typing")
        else:
            send_imessage = send_imessage_visual
            print("Using visual mode - Messages app will open and type visibly")
            print("TIP: Start your screen recording now to capture the AI typing!\n")
    
    print(f"Generating message to {recipient} about: {context}")
    print("Please wait...")
    
    # Generate message using AI clone
    message = generate_message(context, recipient)
    
    if not message:
        print("Failed to generate message. Exiting.")
        return
    
    # Show the generated message
    print("\n----- Generated Message -----")
    print(message)
    print("-----------------------------\n")
    
    # Ask for confirmation
    confirm = input("Send this message? (y/n): ")
    if confirm.lower() in ['y', 'yes']:
        print("\nSending message...")
        if send_imessage == send_imessage_visual:
            print("Messages app will now open and the AI will type your message.")
            print("Make sure your screen recording is active!")
        send_imessage(recipient, message)
    else:
        print("Message not sent.")
        
        # Ask if user wants to edit the message
        edit = input("Do you want to edit the message before sending? (y/n): ")
        if edit.lower() in ['y', 'yes']:
            print("\nEdit the message below:")
            edited_message = input("> ")
            
            # Confirm edited message
            confirm = input("Send edited message? (y/n): ")
            if confirm.lower() in ['y', 'yes']:
                print("\nSending edited message...")
                if send_imessage == send_imessage_visual:
                    print("Messages app will now open and the AI will type your message.")
                    print("Make sure your screen recording is active!")
                send_imessage(recipient, edited_message)
            else:
                print("Message not sent.")

if __name__ == "__main__":
    main()
