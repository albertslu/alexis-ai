#!/usr/bin/env python3

"""
Email Integration for AI Clone

This module provides functionality for receiving and sending emails
using the Gmail API as part of the automated response system.
"""

import os
import json
import base64
import logging
import re
import threading
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify, redirect, url_for
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

# Import the OAuth handler
from utils.oauth_handler import OAuthHandler

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Gmail API configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify']

# Create blueprint for routes
email_bp = Blueprint('email', __name__)

class EmailIntegration:
    """
    Integration with Gmail API for handling emails.
    
    This class provides functionality for receiving incoming emails via the Gmail API
    and sending outgoing emails as part of the automated response system.
    """
    
    def __init__(self, message_listener_service=None, user_id='default', token=None):
        """
        Initialize the email integration.
        
        Args:
            message_listener_service: Instance of MessageListenerService for handling messages
            user_id: User identifier for OAuth credentials
            token: Optional direct token to use for authentication
        """
        self.message_listener_service = message_listener_service
        self.service = None
        self.user_id = user_id  # 'me' refers to the authenticated user in Gmail API
        self.watch_active = False
        self.last_history_id = None
        self.polling_thread = None
        self.stop_polling = threading.Event()
        self.token = token  # Store the token if provided directly
        
        # Try to initialize the Gmail API service with the provided user_id
        self._initialize_service(user_id)
    
    def _initialize_service(self, user_id='default'):
        """
        Initialize the Gmail API service.
        
        Args:
            user_id: User identifier for OAuth credentials
            
        Returns:
            bool: True if service was initialized successfully, False otherwise
        """
        try:
            # If we have a direct token, use it
            if self.token:
                logger.info(f"Initializing Gmail API service with direct token for user_id: {user_id}")
                
                # Create credentials from the token
                creds = Credentials.from_authorized_user_info(self.token)
                
                # Build the service
                self.service = build('gmail', 'v1', credentials=creds)
                logger.info("Successfully initialized Gmail API service with direct token")
                return True
            
            # Otherwise use the OAuth handler to get credentials
            logger.info(f"Getting credentials for user_id: {user_id}")
            credentials = OAuthHandler.get_credentials(user_id, 'gmail')
            
            if not credentials:
                logger.warning(f"No Gmail credentials found for user_id: {user_id}")
                return False
            
            # Build the Gmail API service
            try:
                logger.info(f"Building Gmail API service with credentials for user_id: {user_id}")
                self.service = build('gmail', 'v1', credentials=credentials)
                logger.info("Gmail API service initialized successfully")
                return True
            except Exception as e:
                logger.error(f"Error building Gmail API service: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False
        except Exception as e:
            logger.error(f"Error in _initialize_service: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def authenticate(self, user_id='default'):
        """
        Check authentication status with the Gmail API.
        
        Args:
            user_id: User identifier
            
        Returns:
            dict: Authentication status
        """
        # Check if the user is already authenticated
        auth_status = OAuthHandler.check_auth_status(user_id, 'gmail')
        
        if auth_status['authenticated']:
            # Initialize the service with the existing credentials
            logger.info(f"User {user_id} is authenticated with Gmail, initializing service...")
            service_initialized = self._initialize_service(user_id)
            
            if service_initialized:
                logger.info(f"Successfully initialized Gmail API service for user {user_id}")
                return {
                    "status": "success", 
                    "message": "Successfully authenticated with Gmail API",
                    "authenticated": True
                }
            else:
                logger.error(f"User {user_id} is authenticated but service initialization failed")
                return {
                    "status": "error", 
                    "message": "Authentication successful but service initialization failed. Please try reconnecting.",
                    "authenticated": False
                }
        else:
            logger.warning(f"User {user_id} is not authenticated with Gmail")
            return {
                "status": "error", 
                "message": "Not authenticated with Gmail API. Please authorize access.",
                "authenticated": False
            }
    
    def start_watch(self):
        """
        Start watching for new emails using Gmail API push notifications.
        
        Returns:
            dict: Result of the watch request
        """
        if not self.service:
            return {"status": "error", "message": "Gmail API service not initialized"}
        
        try:
            # Request push notifications for the user's inbox
            result = self.service.users().watch(
                userId="me",
                body={
                    'labelIds': ['INBOX'],
                    'topicName': 'projects/your-project-id/topics/gmail-notifications'  # Replace with your actual topic
                }
            ).execute()
            
            self.last_history_id = result.get('historyId')
            self.watch_active = True
            
            logger.info(f"Started watching for new emails, history ID: {self.last_history_id}")
            
            return {
                "status": "success",
                "watch_active": True,
                "history_id": self.last_history_id
            }
        except Exception as e:
            logger.error(f"Error starting watch: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def stop_watch(self):
        """
        Stop watching for new emails.
        
        Returns:
            dict: Result of the stop watch request
        """
        if not self.service:
            return {"status": "error", "message": "Gmail API service not initialized"}
        
        try:
            self.service.users().stop(userId="me").execute()
            self.watch_active = False
            
            logger.info("Stopped watching for new emails")
            
            return {
                "status": "success",
                "watch_active": False
            }
        except Exception as e:
            logger.error(f"Error stopping watch: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def start_polling(self, interval_seconds=60):
        """
        Start polling for new emails at regular intervals.
        
        This is an alternative to push notifications that doesn't require
        setting up a public endpoint.
        
        Args:
            interval_seconds: Polling interval in seconds
            
        Returns:
            dict: Result of starting the polling thread
        """
        if self.polling_thread and self.polling_thread.is_alive():
            return {"status": "warning", "message": "Polling already active"}
        
        # Reset the stop event
        self.stop_polling.clear()
        
        # Start the polling thread
        self.polling_thread = threading.Thread(
            target=self._polling_thread_func,
            args=(interval_seconds,),
            daemon=True
        )
        self.polling_thread.start()
        
        logger.info(f"Started polling for new emails every {interval_seconds} seconds")
        
        return {
            "status": "success",
            "polling_active": True,
            "interval_seconds": interval_seconds
        }
    
    def stop_polling(self):
        """
        Stop polling for new emails.
        
        Returns:
            dict: Result of stopping the polling thread
        """
        if not self.polling_thread or not self.polling_thread.is_alive():
            return {"status": "warning", "message": "Polling not active"}
        
        # Set the stop event and wait for the thread to finish
        self.stop_polling.set()
        self.polling_thread.join(timeout=5)
        
        logger.info("Stopped polling for new emails")
        
        return {
            "status": "success",
            "polling_active": False
        }
    
    def _polling_thread_func(self, interval_seconds):
        """
        Polling thread function.
        
        Args:
            interval_seconds: Polling interval in seconds
        """
        logger.info("Email polling thread started")
        
        while not self.stop_polling.is_set():
            try:
                # Check for new emails
                self._check_new_emails()
                
                # Sleep for the specified interval
                for _ in range(interval_seconds):
                    if self.stop_polling.is_set():
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Error in polling thread: {str(e)}")
                # Sleep for a short time before retrying
                time.sleep(5)
        
        logger.info("Email polling thread stopped")
    
    def _check_new_emails(self):
        """Check for new unread emails in the inbox."""
        if not self.service:
            logger.error("Gmail API service not initialized")
            return
        
        try:
            # Query for unread emails in the inbox
            results = self.service.users().messages().list(
                userId="me",
                labelIds=['INBOX', 'UNREAD'],
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            
            for message in messages:
                message_id = message['id']
                self._process_email(message_id)
        except Exception as e:
            logger.error(f"Error checking for new emails: {str(e)}")
    
    def _process_email(self, message_id):
        """
        Process a single email message.
        
        Args:
            message_id: ID of the email message to process
        """
        if not self.service:
            logger.error("Gmail API service not initialized")
            return
        
        try:
            # Get the full message details
            message = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format='full'
            ).execute()
            
            # Extract email details
            headers = message['payload']['headers']
            
            # Get From, Subject, and other headers
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            to_email = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
            
            # Extract the email body
            body = self._get_email_body(message)
            
            logger.info(f"Processing email from {from_email} with subject: {subject}")
            
            # Check if this is an email we should respond to
            if self._should_process_email(from_email, to_email, subject):
                # Handle the email if we have a message listener service
                if self.message_listener_service:
                    result = self.message_listener_service.handle_incoming_email(
                        from_email=from_email,
                        subject=subject,
                        body=body,
                        attachments=None  # Attachments not implemented yet
                    )
                    
                    # If auto-response is active and a response was generated, send it
                    if result.get('status') != 'ignored' and result.get('auto_response'):
                        self.send_email(
                            to_email=from_email,
                            subject=f"Re: {subject}",
                            body=result.get('auto_response'),
                            reply_to_message_id=message_id
                        )
                
                # Mark the email as read
                self.service.users().messages().modify(
                    userId="me",
                    id=message_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
        except Exception as e:
            logger.error(f"Error processing email {message_id}: {str(e)}")
    
    def _get_email_body(self, message):
        """
        Extract the body text from an email message and clean it by removing thread markers.
        
        Args:
            message: Full message object from Gmail API
            
        Returns:
            str: Email body text with thread markers removed
        """
        body = ""
        
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        # Clean the email body by removing thread markers
        return self._clean_email_thread(body)
    
    def _clean_email_thread(self, email_body):
        """
        Clean email body by removing Gmail thread markers and quoted content.
        Uses a simple approach that only targets the standard Gmail thread marker pattern.
        
        Args:
            email_body: Raw email body text
            
        Returns:
            str: Cleaned email body with thread markers and quoted content removed
        """
        if not email_body:
            return ""
        
        # More robust Gmail thread marker pattern
        # This matches various formats of Gmail thread markers and everything after them
        # Including variations with or without commas, with different spacing, and with "at" time indicators
        gmail_thread_pattern = r'\r?\n\s*On .+?(?:,|) .+ <.+@.+>(?:\s+wrote:|\s+at\s+.+\s+wrote:)[\s\S]*$'
        
        # Apply the pattern to remove thread markers and everything after
        cleaned_body = re.sub(gmail_thread_pattern, '', email_body, flags=re.IGNORECASE)
        
        # Remove any trailing whitespace and extra newlines
        cleaned_body = cleaned_body.strip()
        
        # If cleaning resulted in an empty body, return the original
        if not cleaned_body:
            return email_body.strip()
        
        return cleaned_body
    
    def _should_process_email(self, from_email, to_email, subject):
        """
        Determine if an email should be processed for auto-response.
        
        Args:
            from_email: Sender email address
            to_email: Recipient email address
            subject: Email subject
            
        Returns:
            bool: True if the email should be processed, False otherwise
        """
        # Don't respond to emails from yourself
        if from_email == to_email:
            return False
        
        # Don't respond to automated emails or notifications
        automated_senders = [
            'noreply',
            'no-reply',
            'donotreply',
            'automated',
            'notification',
            'alert',
            'system'
        ]
        
        if any(sender in from_email.lower() for sender in automated_senders):
            return False
        
        # Don't respond to common automated subject lines
        automated_subjects = [
            'automatic reply',
            'out of office',
            'vacation response',
            'auto-reply',
            'undeliverable',
            'delivery status',
            'subscription'
        ]
        
        if any(subj in subject.lower() for subj in automated_subjects):
            return False
        
        return True
    
    def send_email(self, to_email, subject, body, reply_to_message_id=None):
        """
        Send an email using the Gmail API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            reply_to_message_id: Optional message ID to reply to
            
        Returns:
            dict: Result of sending the email
        """
        if not self.service:
            return {"status": "error", "message": "Gmail API service not initialized"}
        
        try:
            # Create a MIMEText message
            message = MIMEMultipart()
            message['to'] = to_email
            message['subject'] = subject
            
            # Add the body as a text part
            message.attach(MIMEText(body, 'plain'))
            
            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send the message
            sent_message = self.service.users().messages().send(
                userId="me",
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Sent email to {to_email}, ID: {sent_message['id']}")
            
            return {
                "status": "sent",
                "message_id": sent_message['id'],
                "to": to_email,
                "subject": subject
            }
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def extract_sent_emails(self, max_emails=100, days=30):
        """
        Extract sent emails for training data.
        
        Args:
            max_emails: Maximum number of emails to extract
            days: Number of days to look back
            
        Returns:
            dict: Result of the extraction with extracted emails
        """
        # If service is not initialized, try to initialize it
        if not self.service:
            logger.info("Gmail API service not initialized, attempting to initialize...")
            service_initialized = self._initialize_service(self.user_id)
            if not service_initialized:
                logger.error(f"Failed to initialize Gmail API service for user_id: {self.user_id}")
                return {"status": "error", "message": "Gmail API service not initialized. Please reconnect your Gmail account."}
        
        try:
            # Calculate the date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for Gmail query
            start_date_str = start_date.strftime('%Y/%m/%d')
            end_date_str = end_date.strftime('%Y/%m/%d')
            
            # Query for sent emails in the specified date range
            query = f"in:sent after:{start_date_str} before:{end_date_str}"
            logger.info(f"Searching for emails with query: {query}")
            
            results = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_emails
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} sent emails")
            
            extracted_emails = []
            
            for message in messages:
                message_id = message['id']
                
                # Get the full message details
                msg = self.service.users().messages().get(
                    userId="me",
                    id=message_id,
                    format='full'
                ).execute()
                
                # Extract email details
                headers = msg['payload']['headers']
                
                # Get From, To, Subject headers
                from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                to_email = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
                
                # Extract the email body
                body = self._get_email_body(msg)
                
                # Extract thread information to get context
                thread_id = msg.get('threadId')
                thread = self.service.users().threads().get(
                    userId="me",
                    id=thread_id
                ).execute()
                
                # Get all messages in the thread to provide context
                thread_messages = []
                for thread_msg in thread.get('messages', []):
                    if thread_msg['id'] != message_id:  # Skip the current message
                        thread_msg_headers = thread_msg['payload']['headers']
                        thread_msg_from = next((h['value'] for h in thread_msg_headers if h['name'].lower() == 'from'), '')
                        thread_msg_body = self._get_email_body(thread_msg)
                        
                        # Only include if it's not from the user (i.e., it's a message they're responding to)
                        if from_email not in thread_msg_from:
                            thread_messages.append({
                                'from': thread_msg_from,
                                'body': thread_msg_body
                            })
                
                # Create an email object with all relevant information
                email_obj = {
                    'id': message_id,
                    'thread_id': thread_id,
                    'from': from_email,
                    'to': to_email,
                    'subject': subject,
                    'body': body,
                    'timestamp': datetime.fromtimestamp(int(msg['internalDate'])/1000).isoformat(),
                    'context': thread_messages
                }
                
                extracted_emails.append(email_obj)
                logger.info(f"Extracted email to {to_email} with subject: {subject}")
            
            # Save the extracted emails to a file
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            email_data_path = os.path.join(data_dir, 'extracted_emails.json')
            
            # Check if the file exists and load existing data
            if os.path.exists(email_data_path):
                with open(email_data_path, 'r') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        existing_data = {'emails': []}
            else:
                existing_data = {'emails': []}
            
            # Add new emails to existing data
            existing_ids = {email['id'] for email in existing_data['emails']}
            for email in extracted_emails:
                if email['id'] not in existing_ids:
                    existing_data['emails'].append(email)
            
            # Save the updated data
            with open(email_data_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
            
            # Convert extracted emails to training format
            training_data = self._convert_emails_to_training_format(existing_data['emails'])
            
            # Save the training data to a file
            training_data_path = os.path.join(data_dir, 'email_training_data.json')
            with open(training_data_path, 'w') as f:
                json.dump(training_data, f, indent=2)
            
            return {
                "status": "success",
                "message": f"Successfully extracted {len(extracted_emails)} sent emails",
                "extracted_count": len(extracted_emails),
                "total_emails": len(existing_data['emails']),
                "training_data_path": training_data_path
            }
        except Exception as e:
            logger.error(f"Error extracting sent emails: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _convert_emails_to_training_format(self, emails):
        """
        Convert extracted emails to the format used for training.
        
        Args:
            emails: List of extracted email objects
            
        Returns:
            dict: Training data in the required format
        """
        # Extract the user's email address from the first sent email
        user_email = ""
        if emails and 'from' in emails[0]:
            user_email = emails[0]['from']
            logger.info(f"Identified user email as: {user_email}")
        
        training_data = {
            "user_email": user_email,
            "conversations": []
        }
        
        for email in emails:
            # For each email, create a conversation with context
            conversation = {"messages": []}
            
            # Add context messages first (if any)
            for context_msg in email.get('context', []):
                conversation["messages"].append({
                    "sender": "user",  # This is from someone else to the user
                    "text": context_msg['body'],
                    "timestamp": email['timestamp'],  # Use the same timestamp as we don't have the original
                    "channel": "email",
                    "metadata": {
                        "from": context_msg['from'],
                        "subject": email['subject']  # Use the same subject
                    }
                })
            
            # Add the user's response
            conversation["messages"].append({
                "sender": "assistant",  # This is from the user (who we're cloning)
                "text": email['body'],
                "timestamp": email['timestamp'],
                "channel": "email",
                "metadata": {
                    "from": email['from'],
                    "to": email['to'],
                    "subject": email['subject']
                }
            })
            
            # Only add conversations with at least 2 messages (context + response)
            if len(conversation["messages"]) >= 2:
                training_data["conversations"].append(conversation)
        
        return training_data

# Register routes
@email_bp.route('/api/email/auth', methods=['GET'])
def authenticate():
    """Check authentication status with the Gmail API."""
    from utils.message_listener import get_message_listener_service
    
    user_id = request.args.get('user_id', 'default')
    
    email_integration = EmailIntegration(
        message_listener_service=get_message_listener_service(),
        user_id=user_id
    )
    
    result = email_integration.authenticate(user_id)
    
    return jsonify(result)

@email_bp.route('/api/email/watch/start', methods=['POST'])
def start_watch():
    """Start watching for new emails using Gmail API push notifications."""
    from utils.message_listener import get_message_listener_service
    
    data = request.json or {}
    user_id = data.get('user_id', 'default')
    
    email_integration = EmailIntegration(
        message_listener_service=get_message_listener_service(),
        user_id=user_id
    )
    
    result = email_integration.start_watch()
    
    return jsonify(result)

@email_bp.route('/api/email/watch/stop', methods=['POST'])
def stop_watch():
    """Stop watching for new emails."""
    from utils.message_listener import get_message_listener_service
    
    data = request.json or {}
    user_id = data.get('user_id', 'default')
    
    email_integration = EmailIntegration(
        message_listener_service=get_message_listener_service(),
        user_id=user_id
    )
    
    result = email_integration.stop_watch()
    
    return jsonify(result)

@email_bp.route('/api/email/polling/start', methods=['POST'])
def start_polling():
    """Start polling for new emails at regular intervals."""
    from utils.message_listener import get_message_listener_service
    
    data = request.json or {}
    interval_seconds = data.get('interval_seconds', 60)
    user_id = data.get('user_id', 'default')
    
    email_integration = EmailIntegration(
        message_listener_service=get_message_listener_service(),
        user_id=user_id
    )
    
    result = email_integration.start_polling(interval_seconds)
    
    return jsonify(result)

@email_bp.route('/api/email/polling/stop', methods=['POST'])
def stop_polling():
    """Stop polling for new emails."""
    from utils.message_listener import get_message_listener_service
    
    data = request.json or {}
    user_id = data.get('user_id', 'default')
    
    email_integration = EmailIntegration(
        message_listener_service=get_message_listener_service(),
        user_id=user_id
    )
    
    result = email_integration.stop_polling()
    
    return jsonify(result)

@email_bp.route('/api/email/send', methods=['POST'])
def send_email():
    """Send an email using the Gmail API."""
    from utils.message_listener import get_message_listener_service
    
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    to_email = data.get('to_email')
    subject = data.get('subject')
    body = data.get('body')
    reply_to_message_id = data.get('reply_to_message_id')
    user_id = data.get('user_id', 'default')
    
    if not to_email or not subject or not body:
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400
    
    email_integration = EmailIntegration(
        message_listener_service=get_message_listener_service(),
        user_id=user_id
    )
    
    result = email_integration.send_email(to_email, subject, body, reply_to_message_id)
    
    return jsonify(result)

@email_bp.route('/api/email/extract', methods=['POST'])
def extract_emails():
    """Extract sent emails for training data."""
    from utils.message_listener import get_message_listener_service
    
    data = request.json or {}
    max_emails = data.get('max_emails', 100)
    days = data.get('days', 30)
    user_id = data.get('user_id', 'default')
    
    # Get message listener service without passing user_id
    message_listener_service = get_message_listener_service()
    
    # Use get_email_integration instead of creating a new instance
    email_integration = get_email_integration(
        message_listener_service=message_listener_service,
        user_id=user_id
    )
    
    result = email_integration.extract_sent_emails(max_emails, days)
    
    return jsonify(result)

@email_bp.route('/api/email/auth/status', methods=['GET'])
def check_auth_status():
    """Check if the user is authenticated with Gmail."""
    user_id = request.args.get('user_id', 'default')
    
    # Use the OAuth handler to check authentication status
    auth_status = OAuthHandler.check_auth_status(user_id, 'gmail')
    
    return jsonify(auth_status)

# Singleton instance
_email_integration = None

def get_email_integration(message_listener_service=None, user_id='default', token=None):
    """
    Get the singleton instance of the EmailIntegration.
    
    Args:
        message_listener_service: Optional MessageListenerService instance
        user_id: User identifier for OAuth credentials
        token: Optional direct token to use for authentication
        
    Returns:
        EmailIntegration: Singleton instance
    """
    global _email_integration
    
    if _email_integration is None:
        _email_integration = EmailIntegration(
            message_listener_service=message_listener_service,
            user_id=user_id,
            token=token
        )
    
    return _email_integration
