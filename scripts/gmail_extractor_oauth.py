#!/usr/bin/env python3
"""
Gmail Extraction Script using OAuth Authentication

This script extracts sent emails from Gmail using OAuth authentication,
which works with personal Gmail accounts.

Usage:
    python gmail_extractor_oauth.py --max_emails 100 --output data/email_data.json
"""

import os
import json
import base64
import argparse
import re
from datetime import datetime, timedelta
from tqdm import tqdm

# For handling email data
import email
from email.utils import parsedate_to_datetime

# Gmail API libraries
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Path to credentials and token
CREDENTIALS_PATH = 'credentials.json'
TOKEN_PATH = 'token.json'

# Gmail API scope - read-only access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """
    Get authenticated Gmail API service using OAuth
    
    Returns:
        Gmail API service object
    """
    creds = None
    
    # Check if token.json exists
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_info(
                json.load(open(TOKEN_PATH)), SCOPES)
        except Exception as e:
            print(f"Error loading credentials: {e}")
            creds = None
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                creds = None
        
        if not creds:
            print("\n=== Gmail Authorization Required ===\n")
            print("A browser window will open. Please log in and authorize the application.")
            print("After authorization, you'll be redirected to a localhost page.")
            print("You can close that page once it shows 'The authentication flow has completed.'\n")
            
            try:
                # Check if credentials file exists
                if not os.path.exists(CREDENTIALS_PATH):
                    print(f"Error: {CREDENTIALS_PATH} not found.")
                    print("Please download OAuth credentials from Google Cloud Console.")
                    print("1. Go to APIs & Services > Credentials")
                    print("2. Create an OAuth client ID (Web application type)")
                    print("3. Add http://localhost:8080 as an authorized redirect URI")
                    print("4. Download the JSON and save as 'credentials.json'")
                    return None
                
                # Start OAuth flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES)
                
                # Print instructions for the user
                print("Starting OAuth authentication flow...")
                print("A browser window will open. Please sign in and grant permissions.")
                print("\nIMPORTANT: When the browser opens, you may see a warning that says:")
                print("'This app isn't verified' or 'AI Clone has not completed the Google verification process'")
                print("\nThis is normal for development projects. To proceed:")
                print("1. Click 'Advanced' at the bottom left of the warning screen")
                print("2. Click 'Go to AI Clone (unsafe)' at the bottom")
                print("3. Then click 'Continue' to grant the requested permissions\n")
                
                # Don't set the redirect_uri explicitly - let the library handle it
                creds = flow.run_local_server(
                    port=8080,
                    open_browser=True,
                    authorization_prompt_message='Please complete the authorization flow in your browser',
                    success_message='Authentication successful! You can close this window now.'
                )
                
                # Save credentials for next run
                with open(TOKEN_PATH, 'w') as token:
                    token.write(creds.to_json())
                    
                print("\n✅ Authentication successful! Credentials saved for future use.\n")
            except Exception as e:
                print(f"\n❌ Authentication error: {str(e)}")
                print("Please try again or check your credentials.json file.")
                return None
    
    # Build the service
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building service: {e}")
        return None

def extract_emails(service, max_emails=100, months_back=6):
    """
    Extract sent emails from Gmail
    
    Args:
        service: Gmail API service
        max_emails: Maximum number of emails to extract
        months_back: How many months back to look
        
    Returns:
        List of extracted emails
    """
    if not service:
        return []
    
    print(f"Extracting up to {max_emails} sent emails from the past {months_back} months...")
    
    # Calculate date for query
    date_cutoff = (datetime.now() - timedelta(days=30*months_back))
    date_str = date_cutoff.strftime('%Y/%m/%d')
    
    # Query for sent emails
    query = f'in:sent after:{date_str}'
    
    try:
        # Get list of sent emails
        results = service.users().messages().list(
            userId='me', q=query, maxResults=min(max_emails, 500)).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            print("No sent emails found.")
            return []
        
        print(f"Found {len(messages)} sent emails. Processing...")
        
        # Process emails with progress bar
        extracted_emails = []
        for message in tqdm(messages, desc="Processing emails"):
            try:
                # Get full message
                msg = service.users().messages().get(
                    userId='me', id=message['id'], format='full').execute()
                
                # Extract headers
                headers = {}
                for header in msg['payload']['headers']:
                    headers[header['name'].lower()] = header['value']
                
                # Get message body
                body = extract_message_body(msg['payload'])
                
                # Clean body
                body = clean_email_body(body)
                
                # Get thread to find original message
                thread_id = msg['threadId']
                thread = service.users().threads().get(userId='me', id=thread_id).execute()
                
                # Find the message that came before this one in the thread (if any)
                previous_message = find_previous_message(service, thread, msg['id'])
                
                # Create email object
                email_obj = {
                    'message_id': msg['id'],
                    'thread_id': thread_id,
                    'from': headers.get('from', ''),
                    'to': headers.get('to', ''),
                    'subject': headers.get('subject', ''),
                    'date': headers.get('date', ''),
                    'body': body,
                    'previous_message': previous_message
                }
                
                extracted_emails.append(email_obj)
                
            except Exception as e:
                print(f"Error processing message {message['id']}: {e}")
                continue
        
        return extracted_emails
        
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def extract_message_body(payload):
    """
    Extract the body text from a message payload
    
    Args:
        payload: Message payload from Gmail API
        
    Returns:
        Body text
    """
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                body += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
            elif 'parts' in part:
                body += extract_message_body(part)
    elif 'body' in payload and 'data' in payload['body']:
        body += base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
    
    return body

def find_previous_message(service, thread, current_msg_id):
    """
    Find the message that came before the current one in a thread
    
    Args:
        service: Gmail API service
        thread: Thread object from Gmail API
        current_msg_id: ID of the current message
        
    Returns:
        Previous message object or None
    """
    thread_messages = thread['messages']
    thread_messages.sort(key=lambda x: int(x['internalDate']))
    
    for i, thread_msg in enumerate(thread_messages):
        if thread_msg['id'] == current_msg_id and i > 0:
            # Get the previous message in the thread
            prev_msg = thread_messages[i-1]
            prev_full = service.users().messages().get(
                userId='me', id=prev_msg['id'], format='full').execute()
            
            # Extract headers
            prev_headers = {}
            for header in prev_full['payload']['headers']:
                prev_headers[header['name'].lower()] = header['value']
            
            # Get message body
            prev_body = extract_message_body(prev_full['payload'])
            
            # Clean body
            prev_body = clean_email_body(prev_body)
            
            return {
                'from': prev_headers.get('from', ''),
                'to': prev_headers.get('to', ''),
                'subject': prev_headers.get('subject', ''),
                'date': prev_headers.get('date', ''),
                'body': prev_body
            }
    
    return None

def clean_email_body(body):
    """
    Clean the email body by removing signatures, forwarded content, etc.
    
    Args:
        body: Raw email body
        
    Returns:
        Cleaned email body
    """
    # Remove email signatures
    signature_patterns = [
        r'--\s*\n[\s\S]*',  # Standard signature separator
        r'Sent from my [\w\s]*',  # Mobile signatures
        r'Get Outlook for [\w\s]*',  # Outlook signatures
    ]
    
    cleaned_body = body
    for pattern in signature_patterns:
        cleaned_body = re.sub(pattern, '', cleaned_body)
    
    # Remove quoted content (previous emails)
    quoted_patterns = [
        r'On\s+[\w,\s]+at\s+[\d:]+\s+[AP]M[\s\w]+wrote:',  # Gmail style
        r'From:[\s\S]+Sent:',  # Outlook style
        r'>\s*.*\n',  # Quote markers
    ]
    
    for pattern in quoted_patterns:
        cleaned_body = re.sub(pattern, '', cleaned_body)
    
    # Remove extra whitespace
    cleaned_body = re.sub(r'\n{3,}', '\n\n', cleaned_body)
    cleaned_body = cleaned_body.strip()
    
    return cleaned_body

def format_for_rag(emails):
    """
    Format emails for RAG system
    
    Args:
        emails: List of extracted emails
        
    Returns:
        List of RAG items
    """
    rag_items = []
    
    for email in emails:
        # Calculate formality score
        formality_score = calculate_formality(email['body'])
        
        # Parse date
        try:
            date_obj = parsedate_to_datetime(email['date'])
            timestamp = date_obj.isoformat()
        except:
            timestamp = email['date']
        
        # Create RAG item
        rag_item = {
            'content': email['body'],
            'metadata': {
                'channel': 'email',
                'timestamp': timestamp,
                'sender': email['from'],
                'recipients': email['to'],
                'subject': email['subject'],
                'is_sent': True,
                'thread_id': email['thread_id'],
                'message_id': email['message_id'],
                'formality_score': formality_score
            }
        }
        
        # Add previous message context if available
        if email['previous_message']:
            rag_item['context'] = {
                'previous_message': email['previous_message']['body'],
                'previous_sender': email['previous_message']['from']
            }
        
        rag_items.append(rag_item)
    
    return rag_items

def calculate_formality(text):
    """
    Calculate a simple formality score for text
    
    Args:
        text: Email body text
        
    Returns:
        Formality score (0-1)
    """
    # Simple heuristics for formality
    formal_indicators = [
        len(re.findall(r'[A-Z][a-z]+', text)) / max(len(text.split()), 1),  # Proper capitalization
        len(re.findall(r'[.!?]\s+[A-Z]', text)) / max(len(text.split('.')), 1),  # Complete sentences
        len(re.findall(r'\b(Dear|Sincerely|Regards|Thank you|Please|kindly)\b', text, re.I)) / max(len(text.split()), 1) * 5,  # Formal words
        1 if re.search(r'\b(Hi|Hello|Dear)\b.*,', text) else 0,  # Greeting
        1 if re.search(r'(Sincerely|Best|Regards|Thank you|Thanks)[,\s]*\n[\s\S]*', text) else 0  # Sign-off
    ]
    
    informal_indicators = [
        len(re.findall(r'\b(hey|yeah|cool|awesome|btw|lol|haha)\b', text, re.I)) / max(len(text.split()), 1) * 3,  # Informal words
        len(re.findall(r'[!]{2,}', text)) / max(len(text), 1) * 100,  # Multiple exclamations
        len(re.findall(r'\b(u|r|ur|gonna|wanna|gotta)\b', text)) / max(len(text.split()), 1) * 3,  # Contractions
        len(re.findall(r'[^.!?]\s*\n', text)) / max(len(text.split('\n')), 1)  # Incomplete lines
    ]
    
    formal_score = sum(formal_indicators) / len(formal_indicators)
    informal_score = sum(informal_indicators) / len(informal_indicators)
    
    # Normalize to 0-1 range
    formality = formal_score / (formal_score + informal_score + 0.01)
    return min(max(formality, 0), 1)  # Clamp between 0 and 1

def main():
    parser = argparse.ArgumentParser(description='Extract emails for AI Clone')
    parser.add_argument('--max_emails', type=int, default=100, 
                        help='Maximum number of emails to process')
    parser.add_argument('--months', type=int, default=6,
                        help='How many months back to look for emails')
    parser.add_argument('--output', type=str, default='data/email_data.json',
                        help='Output file path')
    args = parser.parse_args()
    
    # Get Gmail service
    service = get_gmail_service()
    
    if not service:
        print("\nFailed to authenticate with Gmail API. Please check your credentials.")
        return
    
    # Extract emails
    emails = extract_emails(service, args.max_emails, args.months)
    
    if not emails:
        print("No emails extracted.")
        return
    
    # Format for RAG
    rag_items = format_for_rag(emails)
    
    print(f"Extracted {len(rag_items)} email exchanges for RAG.")
    
    # Save to file
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(rag_items, f, indent=2)
    
    print(f"Email data saved to {args.output}")
    print("\nNext steps:")
    print("1. Run the integrate_emails.py script to add this data to your RAG system")
    print("2. Test your AI clone with email-related queries")

if __name__ == "__main__":
    main()
