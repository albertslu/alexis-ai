#!/usr/bin/env python3
"""
Gmail API Authentication Setup Script

This script helps you set up authentication with the Gmail API
for the AI Clone's email auto-response system.

Usage:
    python setup_email_auth.py
"""

import os
import sys
import json
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Gmail API configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials')
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, 'gmail_credentials.json')
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, 'gmail_token.json')

def setup_credentials():
    """
    Set up Gmail API credentials
    """
    # Ensure credentials directory exists
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    
    # Check if credentials file exists
    if not os.path.exists(CREDENTIALS_FILE):
        print("\n" + "="*80)
        print("Gmail API Credentials Not Found")
        print("="*80)
        print("\nTo use the email auto-response system, you need to set up Gmail API credentials:")
        print("\n1. Go to https://console.cloud.google.com/")
        print("2. Create a new project (or select an existing one)")
        print("3. Enable the Gmail API")
        print("4. Create OAuth credentials (Desktop application)")
        print("5. Download the credentials JSON file")
        print(f"6. Save it as: {CREDENTIALS_FILE}")
        print("\nAfter downloading the credentials, run this script again.")
        return False
    
    # Try to authenticate
    creds = None
    
    # Check if token file exists
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_info(
                json.load(open(TOKEN_FILE)), SCOPES)
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing credentials: {e}")
                creds = None
        
        # If still no valid credentials, need to authenticate
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save credentials for future use
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                
                print("\n" + "="*80)
                print("Authentication Successful!")
                print("="*80)
                print("\nYour Gmail API credentials have been saved.")
                return True
            except Exception as e:
                logger.error(f"Error during authentication: {e}")
                print(f"\nError during authentication: {e}")
                return False
    else:
        print("\n" + "="*80)
        print("Already Authenticated!")
        print("="*80)
        print("\nYour Gmail API credentials are valid.")
        return True

def main():
    """Main function"""
    print("\n" + "="*80)
    print("Gmail API Authentication Setup")
    print("="*80)
    
    success = setup_credentials()
    
    if success:
        print("\nYou can now use the email auto-response system with the following commands:")
        print("\n# Monitor your inbox for new emails:")
        print("python scripts/email_auto_response.py --mode=monitor")
        print("\n# List pending responses:")
        print("python scripts/email_auto_response.py --mode=list")
        print("\n# Approve and send a specific response:")
        print("python scripts/email_auto_response.py --mode=approve --email_id=<email_id>")
        print("\n# Generate and review a response for a specific email:")
        print("python scripts/email_auto_response.py --mode=send --email_id=<email_id>")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
