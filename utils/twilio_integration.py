#!/usr/bin/env python3

"""
Twilio Integration for AI Clone

This module provides functionality for receiving and sending text messages
using the Twilio API as part of the automated response system.
"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Blueprint, request, Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Create blueprint for routes
twilio_bp = Blueprint('twilio', __name__)

class TwilioIntegration:
    """
    Integration with Twilio API for handling text messages.
    
    This class provides functionality for receiving incoming text messages via webhook
    and sending outgoing text messages using the Twilio API.
    """
    
    def __init__(self, message_listener_service=None):
        """
        Initialize the Twilio integration.
        
        Args:
            message_listener_service: Instance of MessageListenerService for handling messages
        """
        self.message_listener_service = message_listener_service
        self.client = None
        self.validator = None
        
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            try:
                self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                self.validator = RequestValidator(TWILIO_AUTH_TOKEN)
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Twilio client: {str(e)}")
        else:
            logger.warning("Twilio credentials not found in environment variables")
    
    def validate_request(self, request_data, signature, url):
        """
        Validate that a request is actually from Twilio.
        
        Args:
            request_data: The request data (form data or JSON)
            signature: The X-Twilio-Signature header value
            url: The full URL of the request
            
        Returns:
            bool: True if the request is valid, False otherwise
        """
        if not self.validator:
            logger.warning("Request validator not initialized, skipping validation")
            return True
        
        return self.validator.validate(url, request_data, signature)
    
    def send_message(self, to_number, message_body, media_urls=None):
        """
        Send a text message using Twilio.
        
        Args:
            to_number: Phone number to send the message to
            message_body: Content of the message
            media_urls: Optional list of media URLs to attach to the message
            
        Returns:
            dict: Result of sending the message, including message SID if successful
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return {"status": "error", "message": "Twilio client not initialized"}
        
        if not TWILIO_PHONE_NUMBER:
            logger.error("Twilio phone number not configured")
            return {"status": "error", "message": "Twilio phone number not configured"}
        
        try:
            message_params = {
                'body': message_body,
                'from_': TWILIO_PHONE_NUMBER,
                'to': to_number
            }
            
            if media_urls:
                message_params['media_url'] = media_urls
            
            message = self.client.messages.create(**message_params)
            
            logger.info(f"Sent message to {to_number}, SID: {message.sid}")
            
            return {
                "status": "sent",
                "message_sid": message.sid,
                "to": to_number,
                "body": message_body
            }
        except Exception as e:
            logger.error(f"Error sending message to {to_number}: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def handle_webhook(self, request_data):
        """
        Handle an incoming webhook request from Twilio.
        
        Args:
            request_data: The request data from Twilio
            
        Returns:
            tuple: (TwiML response, status code)
        """
        # Extract message details from the request
        from_number = request_data.get('From', '')
        message_body = request_data.get('Body', '')
        num_media = int(request_data.get('NumMedia', 0))
        
        media_urls = []
        for i in range(num_media):
            media_url = request_data.get(f'MediaUrl{i}')
            if media_url:
                media_urls.append(media_url)
        
        logger.info(f"Received message from {from_number}: {message_body}")
        
        # Process the message if we have a message listener service
        response_text = "Message received."
        if self.message_listener_service:
            result = self.message_listener_service.handle_incoming_text(
                from_number=from_number,
                message_body=message_body,
                media_urls=media_urls if media_urls else None
            )
            
            # If auto-response is active and a response was generated, use it
            if result.get('status') != 'ignored' and result.get('auto_response'):
                response_text = result.get('auto_response')
        
        # Create TwiML response
        twiml_response = MessagingResponse()
        twiml_response.message(response_text)
        
        return str(twiml_response), 200

# Register routes
@twilio_bp.route('/api/twilio/webhook', methods=['POST'])
def twilio_webhook():
    """Handle incoming webhook requests from Twilio."""
    from utils.message_listener import get_message_listener_service
    
    # Get the Twilio signature from the request headers
    twilio_signature = request.headers.get('X-Twilio-Signature', '')
    
    # Get the full URL of the request
    request_url = request.url
    
    # Initialize Twilio integration
    twilio_integration = TwilioIntegration(
        message_listener_service=get_message_listener_service()
    )
    
    # Validate the request
    if not twilio_integration.validate_request(request.form, twilio_signature, request_url):
        logger.warning("Invalid Twilio request signature")
        return "Invalid request", 403
    
    # Handle the webhook
    twiml_response, status_code = twilio_integration.handle_webhook(request.form)
    
    return Response(twiml_response, status=status_code, mimetype='text/xml')

@twilio_bp.route('/api/twilio/send', methods=['POST'])
def send_message():
    """Send a text message using Twilio."""
    from utils.message_listener import get_message_listener_service
    
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    to_number = data.get('to_number')
    message_body = data.get('message_body')
    media_urls = data.get('media_urls')
    
    if not to_number or not message_body:
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400
    
    # Initialize Twilio integration
    twilio_integration = TwilioIntegration(
        message_listener_service=get_message_listener_service()
    )
    
    # Send the message
    result = twilio_integration.send_message(to_number, message_body, media_urls)
    
    return jsonify(result)

# Singleton instance
_twilio_integration = None

def get_twilio_integration(message_listener_service=None):
    """
    Get the singleton instance of the TwilioIntegration.
    
    Args:
        message_listener_service: Optional MessageListenerService instance
        
    Returns:
        TwilioIntegration: Singleton instance
    """
    global _twilio_integration
    
    if _twilio_integration is None:
        _twilio_integration = TwilioIntegration(
            message_listener_service=message_listener_service
        )
    
    return _twilio_integration
