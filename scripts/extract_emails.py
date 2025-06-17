#!/usr/bin/env python3
"""
Email Extraction Script for AI Clone

This script extracts sent emails from Gmail, capturing both the original emails
and your responses to provide context for the RAG system.

Usage:
    python extract_emails.py --max_emails 500 --output ../data/email_data.json
"""

import os
import json
import base64
import argparse
import email
import re
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from tqdm import tqdm

# Gmail API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Path to store credentials
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'credentials.json'

def authenticate_gmail():
    """
    Authenticate with Gmail API
    
    Returns:
        Gmail API service object
    """
    creds = None
    
    # Check if token.json exists
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_info(
            json.load(open(TOKEN_PATH)), SCOPES)
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("\n=== Gmail Authorization Required ===")
            print("A browser window will open. Please log in and authorize the application.")
            print("After authorization, you'll be redirected to a localhost page.")
            print("You can close that page once it shows 'The authentication flow has completed.'\n")
            
            try:
                # Try with InstalledAppFlow's authorization code flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES)
                
                # Use the authorization URL approach which is more reliable
                auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')
                print(f"Please go to this URL in your browser: {auth_url}")
                print("After authorization, copy the authorization code from the URL and paste it below.")
                code = input("Enter the authorization code: ")
                
                # Exchange authorization code for credentials
                flow.fetch_token(code=code)
                creds = flow.credentials
                
                # Save credentials for next run
                with open(TOKEN_PATH, 'w') as token:
                    token.write(creds.to_json())
                    
                print("\n✅ Authentication successful! Credentials saved for future use.\n")
            except Exception as e:
                print(f"\n❌ Authentication error: {str(e)}")
                print("Please try again or check your credentials.json file.")
                raise
    
    # Build the service
    service = build('gmail', 'v1', credentials=creds)
    return service

def get_sent_emails(service, max_emails=500, months_back=6):
    """
    Get sent emails from Gmail
    
    Args:
        service: Gmail API service object
        max_emails: Maximum number of emails to retrieve
        months_back: How many months back to look for emails
        
    Returns:
        List of sent email IDs
    """
    # Calculate date for query
    date_cutoff = (datetime.now() - timedelta(days=30*months_back))
    date_str = date_cutoff.strftime('%Y/%m/%d')
    
    # Query for sent emails after the cutoff date
    query = f'in:sent after:{date_str}'
    
    try:
        # Get list of sent emails
        results = service.users().messages().list(
            userId='me', q=query, maxResults=max_emails).execute()
        
        messages = results.get('messages', [])
        
        # Get next page if available and we need more emails
        while 'nextPageToken' in results and len(messages) < max_emails:
            page_token = results['nextPageToken']
            results = service.users().messages().list(
                userId='me', q=query, pageToken=page_token, 
                maxResults=max_emails - len(messages)).execute()
            messages.extend(results.get('messages', []))
        
        return messages
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def get_email_thread(service, thread_id):
    """
    Get all messages in a thread
    
    Args:
        service: Gmail API service object
        thread_id: Thread ID
        
    Returns:
        List of messages in the thread
    """
    try:
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        return thread['messages']
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def decode_body(payload):
    """
    Decode the email body
    
    Args:
        payload: Email payload
        
    Returns:
        Decoded email body
    """
    if 'parts' in payload:
        # Multipart email
        body = ""
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    body += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            elif 'parts' in part:
                # Recursive for nested parts
                for subpart in part['parts']:
                    if subpart['mimeType'] == 'text/plain':
                        if 'data' in subpart['body']:
                            body += base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8')
        return body
    else:
        # Single part email
        if 'data' in payload['body']:
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        return ""

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

def extract_header_value(headers, name):
    """
    Extract a specific header value
    
    Args:
        headers: Email headers
        name: Header name
        
    Returns:
        Header value or empty string
    """
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return ""

def process_email_thread(service, thread_id):
    """
    Process an email thread to extract the conversation
    
    Args:
        service: Gmail API service object
        thread_id: Thread ID
        
    Returns:
        Processed thread with original emails and responses
    """
    messages = get_email_thread(service, thread_id)
    
    if not messages:
        return None
    
    # Sort messages by date
    messages.sort(key=lambda x: int(x['internalDate']))
    
    thread_data = {
        'thread_id': thread_id,
        'subject': '',
        'messages': []
    }
    
    # Process each message in the thread
    for message in messages:
        msg_data = service.users().messages().get(
            userId='me', id=message['id'], format='full').execute()
        
        headers = msg_data['payload']['headers']
        
        # Get headers
        from_header = extract_header_value(headers, 'From')
        to_header = extract_header_value(headers, 'To')
        subject = extract_header_value(headers, 'Subject')
        date_str = extract_header_value(headers, 'Date')
        
        # Set thread subject from first message
        if not thread_data['subject'] and subject:
            thread_data['subject'] = subject
        
        # Get message body
        body = decode_body(msg_data['payload'])
        cleaned_body = clean_email_body(body)
        
        # Determine if this is a sent message
        is_sent = 'SENT' in msg_data['labelIds']
        
        # Parse date
        try:
            date = parsedate_to_datetime(date_str)
        except:
            date = datetime.fromtimestamp(int(msg_data['internalDate'])/1000)
        
        # Add message to thread
        thread_data['messages'].append({
            'message_id': message['id'],
            'from': from_header,
            'to': to_header,
            'date': date.isoformat(),
            'body': cleaned_body,
            'is_sent': is_sent
        })
    
    return thread_data

def format_for_rag(thread_data):
    """
    Format thread data for RAG system
    
    Args:
        thread_data: Processed thread data
        
    Returns:
        List of formatted messages for RAG
    """
    rag_items = []
    
    # Only process threads with at least one sent message
    sent_messages = [m for m in thread_data['messages'] if m['is_sent']]
    if not sent_messages:
        return rag_items
    
    # Process each sent message with context
    for i, message in enumerate(thread_data['messages']):
        if message['is_sent']:
            # Find the previous message (if any) for context
            prev_message = None
            if i > 0:
                prev_message = thread_data['messages'][i-1]
            
            # Create RAG item
            rag_item = {
                'content': message['body'],
                'metadata': {
                    'channel': 'email',
                    'timestamp': message['date'],
                    'sender': message['from'],
                    'recipients': message['to'],
                    'subject': thread_data['subject'],
                    'is_sent': True,
                    'thread_id': thread_data['thread_id'],
                    'message_id': message['message_id']
                }
            }
            
            # Add previous message context if available
            if prev_message:
                rag_item['context'] = {
                    'previous_message': prev_message['body'],
                    'previous_sender': prev_message['from']
                }
                
                # Calculate formality score (simple heuristic)
                formality_score = calculate_formality(message['body'])
                rag_item['metadata']['formality_score'] = formality_score
            
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
    parser.add_argument('--max_emails', type=int, default=500, 
                        help='Maximum number of emails to process')
    parser.add_argument('--months', type=int, default=6,
                        help='How many months back to look for emails')
    parser.add_argument('--output', type=str, default='../data/email_data.json',
                        help='Output file path')
    args = parser.parse_args()
    
    print(f"Authenticating with Gmail...")
    service = authenticate_gmail()
    
    print(f"Fetching up to {args.max_emails} sent emails from the past {args.months} months...")
    sent_emails = get_sent_emails(service, args.max_emails, args.months)
    
    if not sent_emails:
        print("No sent emails found.")
        return
    
    print(f"Found {len(sent_emails)} sent emails. Processing threads...")
    
    # Process unique threads (to avoid duplicates)
    processed_threads = set()
    all_rag_items = []
    
    for email in tqdm(sent_emails):
        thread_id = email.get('threadId')
        
        # Skip already processed threads
        if thread_id in processed_threads:
            continue
        
        processed_threads.add(thread_id)
        
        # Process the thread
        thread_data = process_email_thread(service, thread_id)
        if thread_data:
            # Format for RAG
            rag_items = format_for_rag(thread_data)
            all_rag_items.extend(rag_items)
    
    print(f"Extracted {len(all_rag_items)} email exchanges for RAG.")
    
    # Save to file
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(all_rag_items, f, indent=2)
    
    print(f"Email data saved to {args.output}")

if __name__ == "__main__":
    main()
