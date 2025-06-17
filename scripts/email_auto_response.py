#!/usr/bin/env python3
"""
Email Auto-Response System for AI Clone

This script monitors your Gmail inbox for new emails, generates responses using your AI clone,
and allows for manual review before sending.

Usage:
    python email_auto_response.py --mode=monitor [--interval=60] [--max_emails=10] [--auto_respond]
    python email_auto_response.py --mode=approve --email_id=<email_id>
    python email_auto_response.py --mode=reject --email_id=<email_id>
"""

import os
import sys
import json
import base64
import argparse
import logging
import time
import requests
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import uuid

# Set up logger
logger = logging.getLogger('email_auto_response')

# Gmail API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Gmail API configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'token.json')

# Directory for pending responses
PENDING_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pending_responses')
os.makedirs(PENDING_DIR, exist_ok=True)

# Backend API URL
BACKEND_URL = "http://localhost:5002"

def authenticate_gmail():
    """
    Authenticate with Gmail API
    
    Returns:
        Gmail API service object
    """
    creds = None
    
    # Check if token.json exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_info(json.load(open(TOKEN_FILE)), SCOPES)
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)
        
        # Save credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    try:
        # Build the Gmail API service
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error building Gmail service: {e}")
        return None

def get_recent_emails(service, minutes=5):
    """
    Get recent emails from Gmail inbox that arrived within the last few minutes
    
    Args:
        service: Gmail API service object
        minutes: How many minutes back to look for emails
        
    Returns:
        List of recent email IDs
    """
    try:
        # Calculate timestamp for recent emails
        now = datetime.now()
        time_threshold = int((now - timedelta(minutes=minutes)).timestamp())
        
        # Query for recent emails
        query = f'after:{time_threshold}'
        logger.info(f"Searching for emails with query: {query}")
        
        results = service.users().messages().list(
            userId='me',
            q=query
        ).execute()
        
        messages = results.get('messages', [])
        logger.info(f"Found {len(messages)} recent emails in the last {minutes} minutes")
        
        return messages
    except HttpError as error:
        logger.error(f"Error retrieving recent emails: {error}")
        return []

def get_email_details(service, email_id):
    """
    Get details of a specific email
    
    Args:
        service: Gmail API service object
        email_id: Email ID
        
    Returns:
        Dictionary with email details
    """
    try:
        # Get the email
        message = service.users().messages().get(userId='me', id=email_id).execute()
        
        # Get email headers
        headers = message['payload']['headers']
        
        # Extract header fields
        subject = ''
        sender = ''
        to = ''
        date = ''
        
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                sender = header['value']
            elif header['name'] == 'To':
                to = header['value']
            elif header['name'] == 'Date':
                date = header['value']
        
        # Get email body
        body = ''
        
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        return {
            'id': email_id,
            'threadId': message['threadId'],
            'subject': subject,
            'sender': sender,
            'to': to,
            'date': date,
            'body': body,
            'snippet': message.get('snippet', ''),
            'timestamp': message.get('internalDate', 0)
        }
    except HttpError as error:
        logger.error(f"Error retrieving email details: {error}")
        return None

def mark_as_read(service, email_id):
    """
    Mark an email as read
    
    Args:
        service: Gmail API service object
        email_id: Email ID
    """
    try:
        service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        logger.info(f"Marked email {email_id} as read")
    except HttpError as error:
        logger.error(f"Error marking email as read: {error}")

def is_automated_email(email_details):
    """
    Determine if an email is automated or personal
    
    Args:
        email_details: Email details dictionary
        
    Returns:
        Boolean indicating if email is automated
    """
    # Extract fields for analysis
    sender = email_details['sender'].lower()
    subject = email_details['subject'].lower()
    body = email_details['body'].lower()
    
    # Check sender for automated keywords
    automated_sender_keywords = [
        'noreply', 'no-reply', 'donotreply', 'do-not-reply', 
        'notification', 'alert', 'updates', 'newsletter',
        'marketing', 'promotions', 'offers', 'deals',
        'support@', 'info@', 'hello@', 'contact@',
        'news@', 'newsletter@', 'team@', 'billing@',
        'service@', 'account@', 'subscription@'
    ]
    
    if any(keyword in sender for keyword in automated_sender_keywords):
        logger.info(f"  Automated sender detected: {sender}")
        return True
    
    # Check for common marketing/newsletter domains
    marketing_domains = [
        'mailchimp.com', 'sendgrid.net', 'amazonses.com', 
        'e.', '.mail.', 'email.', 'marketing.',
        'campaign-', 'newsletter.', 'updates.'
    ]
    
    if any(domain in sender for domain in marketing_domains):
        logger.info(f"  Marketing domain detected: {sender}")
        return True
    
    # Check subject for automated keywords
    automated_subject_keywords = [
        'newsletter', 'update', 'digest', 'weekly', 'monthly',
        'subscription', 'receipt', 'invoice', 'payment',
        'statement', 'report', 'notification', 'alert',
        'confirm', 'verification', 'verify', 'welcome',
        'invitation', 'reminder', 'password', 'security',
        'account', 'offer', 'promotion', 'discount', 'sale',
        'deal', 'special', 'exclusive', 'limited time',
        'free', 'trial', 'upgrade', 'renew', 'expir'
    ]
    
    if any(keyword in subject for keyword in automated_subject_keywords):
        logger.info(f"  Automated subject detected: {subject}")
        return True
    
    # Check for common marketing patterns in subject
    marketing_patterns = [
        '[', ']', '🔥', '💰', '💸', '🎉', '🎊', '🎁',
        '% off', 'last chance', 'final hours', 'don\'t miss',
        'exclusive', 'just for you', 'special offer'
    ]
    
    if any(pattern in subject for pattern in marketing_patterns):
        logger.info(f"  Marketing pattern detected in subject: {subject}")
        return True
    
    # Check for common marketing patterns in body
    if any(pattern in body[:500] for pattern in marketing_patterns):
        logger.info(f"  Marketing pattern detected in body")
        return True
    
    # If none of the above conditions match, likely a personal email
    return False

def generate_response(email_details, user_id=None):
    """
    Generate a response to an email using the AI clone
    
    Args:
        email_details: Email details dictionary
        user_id: User ID for the AI clone (default: None, will be determined from context)
        
    Returns:
        Generated response text
    """
    try:
        # Determine user_id if not provided
        if user_id is None:
            # Try to get user_id from environment or config
            import os
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
            if os.path.exists(config_path):
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    user_id = config.get('default_user_id', 'default')
            else:
                # Use a generic default
                user_id = 'default'
        
        # Prepare the message for the AI clone
        sender_name = email_details.get('sender_name', email_details.get('sender', '').split('@')[0])
        
        # Format the message for the AI clone
        message = f"Email from {sender_name} with subject '{email_details['subject']}':\n\n{email_details['body']}"
        
        # Log the message being sent to the AI clone
        logger.info(f"Sending message to AI clone: {message[:100]}...")
        
        # Use the special endpoint for email listener with correct port (5002)
        response = requests.post(
            "http://localhost:5002/api/email-listener/generate-response",
            json={
                "message": message,
                "addToRag": True,
                "channel": "email",
                "subject": email_details['subject'],
                "saveToHistory": False,  # We'll handle saving to history ourselves when approved
                "user_id": user_id  # Add user_id parameter
            },
            headers={
                "Content-Type": "application/json"
            }
        )
        
        # Log the response status and headers for debugging
        logger.info(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            if "response" in response_data:
                logger.info(f"Received response from AI clone: {response_data['response'][:100]}...")
                return response_data["response"]
            else:
                logger.error(f"Unexpected response format: {response_data}")
                return generate_fallback_response(sender_name, user_name=get_display_name(user_id))
        else:
            logger.error(f"Error from backend API: {response.status_code} - {response.text}")
            return generate_fallback_response(sender_name, user_name=get_display_name(user_id))
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return generate_fallback_response(sender_name, user_name=get_display_name(user_id))

def get_display_name(user_id):
    """Get display name from user_id"""
    try:
        import os
        import json
        
        # Handle None user_id
        if user_id is None:
            return "User"
        
        # Default name from user_id
        default_name = user_id.split('_')[0] if '_' in user_id else user_id
        
        # Path to user memories
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Try memories directory first
        memories_dir = os.path.join(base_dir, 'data', 'memories')
        memory_file = os.path.join(memories_dir, f'user_{user_id}_memories.json')
        
        # If not found, try memory directory
        if not os.path.exists(memory_file):
            memory_dir = os.path.join(base_dir, 'data', 'memory')
            memory_file = os.path.join(memory_dir, f'{user_id}_memory.json')
            
            if not os.path.exists(memory_file):
                return default_name
        
        # Read memory file
        with open(memory_file, 'r') as f:
            memories = json.load(f)
        
        # Look for name in core memories
        if 'core_memory' in memories:
            for memory in memories['core_memory']:
                content = memory.get('content', '').lower()
                if 'my name is' in content or 'name:' in content:
                    # Extract name from memory
                    if 'my name is' in content:
                        name_parts = content.split('my name is', 1)[1].strip().rstrip('.').split()
                    else:
                        name_parts = content.split('name:', 1)[1].strip().rstrip('.').split()
                    
                    # Get first name
                    if name_parts:
                        first_name = name_parts[0].strip().capitalize()
                        return first_name
        
        return default_name
        
    except Exception as e:
        logger.error(f"Error retrieving user display name: {e}")
        # Fall back to default name
        return user_id.split('_')[0] if user_id and '_' in user_id else user_id if user_id else "User"

def generate_fallback_response(sender_name, user_name=None):
    """Generate a fallback response when the AI clone is unavailable"""
    # Extract just the name without email
    if '<' in sender_name:
        sender_name = sender_name.split('<')[0].strip()
    
    # Use a generic name if none provided
    if user_name is None:
        user_name = "User"
    
    return f"Hello {sender_name},\n\nThank you for your email. I've received your message and will get back to you soon.\n\nBest regards,\n{user_name}"

def save_pending_response(email_details, response_text):
    """
    Save a pending response to file for later approval
    
    Args:
        email_details: Email details dictionary
        response_text: Generated response text
        
    Returns:
        Path to the saved file
    """
    email_id = email_details['id']
    file_path = os.path.join(PENDING_DIR, f"{email_id}.json")
    
    data = {
        'email_details': email_details,
        'response': response_text,
        'generated_at': datetime.now().isoformat()
    }
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Saved pending response to {file_path}")
    return file_path

def send_email_response(service, email_details, response_text):
    """
    Send an email response
    
    Args:
        service: Gmail API service object
        email_details: Email details dictionary
        response_text: Response text to send
        
    Returns:
        Boolean indicating success
    """
    try:
        # Extract sender email address
        sender_email = email_details['sender']
        if '<' in sender_email and '>' in sender_email:
            sender_email = sender_email.split('<')[1].split('>')[0]
        
        # Create message
        message = MIMEText(response_text)
        message['to'] = sender_email
        message['subject'] = f"Re: {email_details['subject']}"
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send message
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message, 'threadId': email_details['threadId']}
        ).execute()
        
        logger.info(f"Response sent successfully: {sent_message['id']}")
        
        # Save to chat history - only do this once
        save_to_chat_history(email_details, response_text)
        
        # Delete the pending response file
        pending_file = os.path.join(PENDING_DIR, f"{email_details['id']}.json")
        if os.path.exists(pending_file):
            os.remove(pending_file)
            logger.info(f"Deleted pending response file: {pending_file}")
        
        return True
    
    except HttpError as error:
        logger.error(f"Error sending response: {error}")
        return False

def save_to_chat_history(email_details, response_text, user_id="default"):
    """
    Save the email and response to chat_history.json
    
    Args:
        email_details: Email details dictionary
        response_text: Response text
        user_id: User ID for the chat history (default: default)
    """
    try:
        # Path to user-specific chat history
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        chat_histories_dir = os.path.join(base_dir, 'data', 'chat_histories')
        
        # Ensure the chat_histories directory exists
        os.makedirs(chat_histories_dir, exist_ok=True)
        
        # User-specific chat history path
        chat_history_path = os.path.join(chat_histories_dir, f"user_{user_id}_chat_history.json")
        
        # If user-specific file doesn't exist, fall back to the default
        if not os.path.exists(chat_history_path):
            logger.warning(f"User-specific chat history not found for {user_id}, using default")
            chat_history_path = os.path.join(base_dir, 'data', 'chat_history.json')
            
            # If default doesn't exist either, create a new one
            if not os.path.exists(chat_history_path):
                logger.warning(f"Default chat history not found, creating new file")
                with open(chat_history_path, 'w') as f:
                    json.dump({"conversations": []}, f)
        
        # Read existing chat history
        with open(chat_history_path, 'r') as f:
            chat_history = json.load(f)
        
        # Create a new conversation with this email exchange
        new_conversation = {
            "id": str(uuid.uuid4()),
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "sender": "user",
                    "text": email_details['body'],
                    "timestamp": email_details.get('timestamp', str(int(time.time()))),
                    "channel": "email",
                    "metadata": {
                        "subject": email_details['subject'],
                        "from": email_details['sender'],
                        "to": email_details['to']
                    }
                },
                {
                    "id": str(uuid.uuid4()),
                    "sender": "clone",
                    "text": response_text,
                    "timestamp": str(int(time.time())),
                    "channel": "email",
                    "metadata": {
                        "subject": f"Re: {email_details['subject']}",
                        "from": email_details['to'],  # Clone is responding from the user's email
                        "to": email_details['sender']
                    }
                }
            ],
            "model_version": "gpt-4o-mini"  # Assuming this is the current model
        }
        
        # Add to chat history
        chat_history["conversations"].insert(0, new_conversation)
        
        # Write back to file
        with open(chat_history_path, 'w') as f:
            json.dump(chat_history, f, indent=2)
        
        logger.info(f"Saved email exchange to chat history: {chat_history_path}")
        
        # Also add to RAG system for future context
        try:
            from rag.app_integration import add_interaction_to_rag
            
            # Add the email exchange to RAG
            add_interaction_to_rag(
                email_details['body'],
                response_text,
                user_id=user_id
            )
            
            logger.info(f"Added email exchange to RAG system for user {user_id}")
        
        except Exception as rag_error:
            logger.error(f"Error adding to RAG system: {rag_error}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error saving to chat history: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def process_email(service, email_details, auto_respond=False, user_id=None):
    """
    Process an email by generating a response and saving it for review
    
    Args:
        service: Gmail API service instance
        email_details: Email details dictionary
        auto_respond: Whether to automatically send the response without review
        user_id: User ID for the chat history (default: None, will be determined from context)
    """
    try:
        # Generate response
        logger.info(f"Generating response for email: {email_details['subject']}")
        response = generate_response(email_details, user_id)
        
        # Log response preview
        logger.info(f"Generated response preview: {response[:100]}...")
        
        if auto_respond:
            # Send response automatically
            logger.info("Auto-respond enabled, sending response without review")
            success = send_email_response(service, email_details, response)
            
            if success:
                logger.info(f"Auto-response sent successfully for email: {email_details['id']}")
            else:
                logger.error(f"Failed to send auto-response for email: {email_details['id']}")
                # Save for manual review if auto-send fails
                logger.info("Saving failed auto-response for manual review")
                save_pending_response(email_details, response)
        else:
            # Save for manual review
            logger.info("Auto-respond disabled, saving response for manual review")
            save_pending_response(email_details, response)
        
        # Mark email as read
        mark_as_read(service, email_details['id'])
    
    except Exception as e:
        logger.error(f"Error processing email: {e}")

def monitor_emails(check_interval=60, max_emails=10, auto_respond=False, user_id=None):
    """
    Monitor incoming emails and process them
    
    Args:
        check_interval: How often to check for new emails (in seconds)
        max_emails: Maximum number of emails to process per check
        auto_respond: Whether to automatically send responses without review
        user_id: User ID for the chat history (default: None, will be determined from context)
    """
    try:
        # Authenticate with Gmail API
        service = authenticate_gmail()
        
        logger.info(f"Starting email monitoring (checking every {check_interval} seconds)")
        logger.info(f"Auto-respond: {auto_respond}")
        
        # Keep track of processed emails to avoid duplicates
        processed_emails = set()
        
        while True:
            try:
                # Get recent emails (from the last 5 minutes)
                emails = get_recent_emails(service, minutes=5)
                
                # Limit the number of emails to process
                emails = emails[:max_emails]
                
                # Process each email
                for email in emails:
                    # Skip already processed emails
                    if email['id'] in processed_emails:
                        continue
                    
                    # Add to processed set
                    processed_emails.add(email['id'])
                    
                    # Get email details
                    email_details = get_email_details(service, email['id'])
                    
                    if not email_details:
                        logger.error(f"Failed to get details for email {email['id']}")
                        continue
                    
                    # Get timestamp and format as readable date
                    timestamp = int(email_details.get('timestamp', 0)) / 1000  # Convert to seconds
                    received_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    
                    logger.info(f"Detected new email: {email_details['subject']}")
                    logger.info(f"  Received at: {received_time}")
                    logger.info(f"  From: {email_details['sender']}")
                    logger.info(f"  To: {email_details['to']}")
                    logger.info(f"  Body preview: {email_details['body'][:100]}...")
                    
                    # Check if this is an automated email
                    if is_automated_email(email_details):
                        logger.info("  Classification: Automated/Marketing Email")
                        # Mark as read and skip
                        mark_as_read(service, email['id'])
                        continue
                    
                    # Process personal emails
                    logger.info("  Classification: Personal Email")
                    logger.info(f"  Email ID: {email_details['id']}")
                    logger.info(f"  Thread ID: {email_details['threadId']}")
                    
                    # Process the email
                    process_email(service, email_details, auto_respond, user_id)
                
                # Limit the size of processed_emails to avoid memory issues
                if len(processed_emails) > 1000:
                    # Keep only the most recent 500 emails
                    processed_emails = set(list(processed_emails)[-500:])
                
                # Sleep for the specified interval before checking again
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(check_interval)  # Still sleep on error
                
    except Exception as e:
        logger.error(f"Error in email monitoring: {e}")

def approve_email(service, email_id, user_id):
    """
    Approve and send a pending email response
    
    Args:
        service: Gmail API service object
        email_id: Email ID
        user_id: User ID for the chat history
        
    Returns:
        Boolean indicating success
    """
    try:
        # Check if the pending response exists
        pending_file = os.path.join(PENDING_DIR, f"{email_id}.json")
        
        if not os.path.exists(pending_file):
            logger.error(f"No pending response found for email {email_id}")
            return False
        
        # Load the pending response
        with open(pending_file, 'r') as f:
            data = json.load(f)
        
        # Send the response
        success = send_email_response(service, data['email_details'], data['response'])
        
        if success:
            logger.info(f"Response approved and sent for email {email_id}")
            
            # Note: save_to_chat_history is already called inside send_email_response
            # No need to call it again here
            
            # Delete the pending file
            os.remove(pending_file)
            logger.info(f"Deleted pending response file: {pending_file}")
            
            return True
        else:
            logger.error(f"Failed to send approved response for email {email_id}")
            return False
    
    except Exception as e:
        logger.error(f"Error approving email: {e}")
        return False

def reject_email(email_id, user_id=None):
    """
    Reject a pending email response
    
    Args:
        email_id: Email ID to reject
        user_id: User ID for the AI clone (default: None)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the pending response file path
        pending_file = os.path.join(PENDING_DIR, f"{email_id}.json")
        
        if not os.path.exists(pending_file):
            logger.error(f"Pending response file not found: {pending_file}")
            return False
        
        # Delete the pending response file
        os.remove(pending_file)
        logger.info(f"Rejected response for email {email_id}")
        
        return True
    except Exception as e:
        logger.error(f"Error rejecting email: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Email Auto-Response System')
    parser.add_argument('--mode', choices=['monitor', 'approve', 'reject'], default='monitor',
                        help='Mode to run in (monitor, approve, reject)')
    parser.add_argument('--interval', type=int, default=60,
                        help='Check interval in seconds for monitor mode')
    parser.add_argument('--max_emails', type=int, default=10,
                        help='Maximum number of emails to process per check for monitor mode')
    parser.add_argument('--auto_respond', action='store_true',
                        help='Automatically send responses without review (for monitor mode)')
    parser.add_argument('--email_id', help='Email ID for approve/reject mode')
    parser.add_argument('--user_id', help='User ID for chat history and memories')
    
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs(PENDING_DIR, exist_ok=True)
    
    # Authenticate with Gmail API
    service = authenticate_gmail()
    
    if not service:
        logger.error("Failed to authenticate with Gmail API")
        return
    
    # Execute based on mode
    if args.mode == 'monitor':
        monitor_emails(args.interval, args.max_emails, args.auto_respond, args.user_id)
    elif args.mode == 'approve':
        if not args.email_id:
            logger.error("Email ID is required for approve mode")
            sys.exit(1)
        approve_email(service, args.email_id, args.user_id)
    elif args.mode == 'reject':
        if not args.email_id:
            logger.error("Email ID is required for reject mode")
            sys.exit(1)
        reject_email(args.email_id, args.user_id)

if __name__ == "__main__":
    main()
