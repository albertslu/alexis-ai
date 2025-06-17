#!/usr/bin/env python3
"""
Fix Gmail API Authentication for AI Clone

This script helps fix the OAuth issues with Gmail API by:
1. Removing the old token.json file
2. Using a console-based authentication flow that doesn't require redirect URIs
3. Creating a new token.json file with the correct permissions

Usage:
    python fix_gmail_auth.py
"""

import os
import json
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the scopes - we need modify access for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Path to credentials
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')
TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'token.json')

def fix_gmail_auth():
    """Fix Gmail API authentication"""
    print("\n" + "="*80)
    print("Gmail API Authentication Fix")
    print("="*80)
    
    # Check if credentials.json exists
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"\nError: credentials.json not found at {CREDENTIALS_PATH}")
        print("\nPlease make sure you have downloaded your OAuth credentials from Google Cloud Console.")
        return False
    
    # Remove old token if it exists
    if os.path.exists(TOKEN_PATH):
        print(f"\nRemoving old token.json file...")
        os.remove(TOKEN_PATH)
    
    print("\nStarting new authentication flow...")
    
    try:
        # Create flow using credentials
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_PATH, SCOPES)
        
        # Use local server flow which works with web application credentials
        # This will automatically open a browser window
        print("\nA browser window will open. Please log in and authorize the application.")
        print("After authorization, you'll be redirected to localhost.")
        print("The script will automatically detect the authorization code.")
        
        # Use port 8080 to match your configured redirect URI
        creds = flow.run_local_server(port=8080)
        
        # Save the credentials for future use
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
        
        print("\n✅ Authentication successful!")
        print(f"New token saved to {TOKEN_PATH}")
        
        # Test the credentials by listing labels
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        if not labels:
            print("\nNo labels found.")
        else:
            print("\nGmail labels found:")
            for label in labels:
                print(f"- {label['name']}")
        
        print("\n✅ Gmail API connection successful!")
        return True
    
    except Exception as e:
        print(f"\n❌ Error during authentication: {e}")
        return False

def main():
    """Main function"""
    success = fix_gmail_auth()
    
    if success:
        print("\n" + "="*80)
        print("Next Steps")
        print("="*80)
        print("\n1. Now you can run the email auto-response script:")
        print("   python scripts/email_auto_response.py --mode=monitor")
        print("\n2. To list pending responses:")
        print("   python scripts/email_auto_response.py --mode=list")
        print("\n3. To approve a response:")
        print("   python scripts/email_auto_response.py --mode=approve --email_id=<email_id>")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
