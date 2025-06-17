#!/usr/bin/env python3
"""
Gmail Listener Script for AI Clone Auto-Response System
This script connects to Gmail, monitors for new emails, and processes them through the AI clone.
It filters out subscription and no-reply emails.
"""

import os
import time
import json
import base64
import pickle
import signal
import logging
import datetime
import re
import argparse
from pathlib import Path
from email.mime.text import MIMEText

import google.auth
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Set up logging first so we can use it throughout the file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gmail_listener.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import the response generator
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger.info(f"Python path: {sys.path}")

# Import RAG system from the correct package
try:
    from rag.rag_system import HybridResponseGenerator, MessageRAG
    logger.info("Successfully imported RAG system from rag.rag_system")
except ImportError as e:
    logger.error(f"Error importing RAG system: {e}")
    # Fallback to direct import if package import fails
    try:
        from rag_system import HybridResponseGenerator, MessageRAG
        logger.info("Successfully imported RAG system directly")
    except ImportError as e:
        logger.error(f"Failed to import RAG system using fallback: {e}")

# Add the parent directory to sys.path to import utils
# This is already done above, no need to do it twice
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Constants
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
TOKEN_FILE = Path('token.pickle')
CREDENTIALS_FILE = Path('credentials.json')
PID_FILE = Path('gmail_listener.pid')
CONFIG_FILE = Path('gmail_listener_config.json')

# Default configuration
DEFAULT_CONFIG = {
    'auto_respond': False,
    'check_interval': 60,  # seconds
    'max_emails_per_check': 5,
    'respond_to_all': False,
    'filter_labels': [],
    'filter_from': '',
    'filter_to': '',
    'filter_subject': '',
    'confidence_threshold': 0.7,
    'filter_rules': {
        'ignore_noreply': True,
        'ignore_subscriptions': True,
        'allowed_senders': []  # Empty list means all senders are allowed
    }
}

def get_gmail_service():
    """Authenticate and get the Gmail service."""
    creds = None
    
    # Load existing token if available
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    # Otherwise, get new credentials
    elif not creds:
        if not CREDENTIALS_FILE.exists():
            logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
            raise FileNotFoundError(f"Credentials file not found: {CREDENTIALS_FILE}")
        
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

def get_email_content(service, msg_id):
    """Get the content of an email by its ID."""
    try:
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        
        # Extract headers
        headers = {}
        for header in message['payload']['headers']:
            headers[header['name'].lower()] = header['value']
        
        # Extract subject, from, to
        subject = headers.get('subject', '(No Subject)')
        sender = headers.get('from', '').split('<')[-1].split('>')[0] if '<' in headers.get('from', '') else headers.get('from', '')
        to = headers.get('to', '')
        
        # Extract body
        body = ""
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        return {
            'id': msg_id,
            'subject': subject,
            'from': sender,
            'to': to,
            'body': body,
            'timestamp': datetime.datetime.fromtimestamp(int(message['internalDate'])/1000).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting email content: {e}")
        return None

def should_process_email(email, config):
    """Determine if an email should be processed based on filter rules."""
    # Skip if it's a no-reply email and we're ignoring those
    if config['filter_rules']['ignore_noreply']:
        if 'noreply' in email['from'].lower() or 'no-reply' in email['from'].lower():
            logger.info(f"Skipping no-reply email: {email['subject']}")
            return False
    
    # Skip if it looks like a subscription/newsletter and we're ignoring those
    if config['filter_rules']['ignore_subscriptions']:
        subscription_keywords = ['unsubscribe', 'newsletter', 'subscription', 'marketing']
        if any(keyword in email['body'].lower() for keyword in subscription_keywords):
            logger.info(f"Skipping subscription email: {email['subject']}")
            return False
    
    # Check if sender is in allowed list (if the list is not empty)
    if config['filter_rules']['allowed_senders'] and email['from'] not in config['filter_rules']['allowed_senders']:
        logger.info(f"Skipping email from non-allowed sender: {email['from']}")
        return False
    
    return True

def send_email_response(service, to, subject, body, thread_id=None):
    """Send an email response."""
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
    
    # Convert the message to a base64 encoded string
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    try:
        message = service.users().messages().send(
            userId='me',
            body={'raw': raw, 'threadId': thread_id} if thread_id else {'raw': raw}
        ).execute()
        logger.info(f"Response sent to {to}, message ID: {message['id']}")
        return message
    except Exception as e:
        logger.error(f"Error sending email response: {e}")
        return None

def mark_as_read(service, msg_id):
    """Mark an email as read by removing the UNREAD label."""
    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        logger.info(f"Marked message {msg_id} as read")
    except Exception as e:
        logger.error(f"Error marking message as read: {e}")

def process_emails(service, config):
    """Check for new emails and process them."""
    try:
        # Query for unread emails
        results = service.users().messages().list(
            userId='me', 
            q='is:unread -category:promotions -category:social',
            maxResults=config['max_emails_per_check']
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            logger.info("No new emails to process")
            return
        
        logger.info(f"Found {len(messages)} unread emails")
        
        # Initialize the response generator
        response_generator = HybridResponseGenerator()
        
        for message in messages:
            msg_id = message['id']
            email = get_email_content(service, msg_id)
            
            if not email:
                continue
            
            if should_process_email(email, config):
                logger.info(f"Processing email: {email['subject']} from {email['from']}")
                
                # Generate response
                response_text = response_generator.generate_response(
                    email['body'],
                    channel="email",
                    confidence_threshold=config['confidence_threshold'],
                    metadata={"subject": email['subject']}
                )
                
                # Send response if auto-respond is enabled
                if config['auto_respond'] and response_text:
                    send_email_response(
                        service,
                        email['from'],
                        email['subject'],
                        response_text,
                        message.get('threadId')
                    )
                else:
                    logger.info(f"Auto-respond disabled or no response generated for: {email['subject']}")
                
                # Save to chat history
                save_to_chat_history(email, response_text)
            
            # Mark as read regardless of whether we responded
            mark_as_read(service, msg_id)
            
    except Exception as e:
        logger.error(f"Error processing emails: {e}")

def save_to_chat_history(email, response_text):
    """Save the email and response to chat history."""
    try:
        chat_history_file = Path('data/chat_history.json')
        
        if not chat_history_file.exists():
            logger.error("Chat history file not found")
            return
        
        with open(chat_history_file, 'r') as f:
            chat_history = json.load(f)
        
        # Find the latest conversation or create a new one
        if not chat_history['conversations']:
            conversation = {
                "id": "gmail-" + datetime.datetime.now().isoformat(),
                "messages": [],
                "model_version": os.environ.get('AI_MODEL', 'v1.4')
            }
            chat_history['conversations'].append(conversation)
        else:
            conversation = chat_history['conversations'][0]
        
        # Add the user message
        user_message = {
            "sender": "user",
            "text": email['body'],
            "timestamp": email['timestamp'],
            "channel": "email",
            "id": f"gmail-{email['id']}",
            "model_version": os.environ.get('AI_MODEL', 'v1.4'),
            "subject": email['subject']
        }
        conversation['messages'].append(user_message)
        
        # Add the clone response if there is one
        if response_text:
            clone_message = {
                "sender": "clone",
                "text": response_text,
                "timestamp": datetime.datetime.now().isoformat(),
                "channel": "email",
                "id": f"msg-{int(time.time()*1000)}",
                "model_version": os.environ.get('AI_MODEL', 'v1.4'),
                "subject": email['subject']
            }
            conversation['messages'].append(clone_message)
        
        # Save back to file
        with open(chat_history_file, 'w') as f:
            json.dump(chat_history, f, indent=2)
        
        logger.info(f"Saved email and response to chat history")
    except Exception as e:
        logger.error(f"Error saving to chat history: {e}")

def load_config(user_id=None):
    """Load configuration from MongoDB or use defaults.
    
    Args:
        user_id: The user ID to load the configuration for
        
    Returns:
        dict: The user's Gmail configuration
    """
    if user_id:
        # Load configuration from MongoDB for the specific user
        logger.info(f"Loading configuration for user {user_id} from MongoDB")
        try:
            # Import here to avoid circular imports
            from utils.gmail_config import get_user_gmail_config
            return get_user_gmail_config(user_id)
        except Exception as e:
            logger.error(f"Error loading config from MongoDB: {e}")
            return DEFAULT_CONFIG.copy()
    else:
        # Fall back to file-based configuration for backward compatibility
        logger.warning("No user_id provided, falling back to file-based configuration")
        config = DEFAULT_CONFIG.copy()
        
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    # Update config with loaded values
                    for key, value in loaded_config.items():
                        if key in config:
                            if isinstance(value, dict) and isinstance(config[key], dict):
                                config[key].update(value)
                            else:
                                config[key] = value
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return config

def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved")
    except Exception as e:
        logger.error(f"Error saving config: {e}")

def handle_exit(signum, frame):
    """Handle exit signals gracefully."""
    logger.info("Received exit signal, shutting down...")
    if PID_FILE.exists():
        PID_FILE.unlink()
    sys.exit(0)

def main():
    """Main function to run the Gmail listener."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Gmail Listener for AI Clone')
    parser.add_argument('--user-id', type=str, help='User ID to load configuration from MongoDB')
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # Save PID
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    # Log the user ID
    if args.user_id:
        logger.info(f"Starting Gmail listener for user ID: {args.user_id}")
    else:
        logger.warning("No user ID provided, using default configuration")
    
    # Load configuration using the user ID if provided
    config = load_config(args.user_id)
    logger.info(f"Loaded configuration: {config}")
    
    try:
        # Get Gmail service
        service = get_gmail_service()
        logger.info("Gmail service initialized")
        
        # Main loop
        logger.info(f"Starting Gmail listener with check interval: {config['check_interval']} seconds")
        logger.info(f"Max emails per check: {config.get('max_emails_per_check', 5)}")
        
        while True:
            process_emails(service, config)
            time.sleep(config['check_interval'])
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        # Clean up
        if PID_FILE.exists():
            PID_FILE.unlink()

if __name__ == "__main__":
    main()
