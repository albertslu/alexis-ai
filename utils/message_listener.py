#!/usr/bin/env python3

"""
Message Listener Service for AI Clone

This module provides functionality for monitoring incoming messages from different
channels (text and email) and triggering automated responses when appropriate.
"""

import os
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
try:
    import requests
    requests_available = True
except ImportError:
    requests_available = False
from flask import Blueprint, request, jsonify

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CONFIG_DIR = os.path.join(DATA_DIR, 'config')
SCHEDULE_CONFIG_PATH = os.path.join(CONFIG_DIR, 'auto_response_schedule.json')

# Ensure directories exist
os.makedirs(CONFIG_DIR, exist_ok=True)

# Create blueprint for routes
message_listener_bp = Blueprint('message_listener', __name__)

class MessageListenerService:
    """
    Service for monitoring incoming messages and triggering automated responses.
    
    This class provides functionality to listen for incoming messages from different
    channels (text and email) and trigger automated responses when appropriate based
    on user-defined schedules and settings.
    """
    
    def __init__(self, hybrid_response_generator=None, feedback_system=None):
        """
        Initialize the message listener service.
        
        Args:
            hybrid_response_generator: Instance of HybridResponseGenerator for generating responses
            feedback_system: Instance of FeedbackSystem for logging responses for feedback
        """
        self.hybrid_response_generator = hybrid_response_generator
        self.feedback_system = feedback_system
        self.schedule = self._load_schedule()
        self.active = False
        self.listener_threads = {}
        
    def _load_schedule(self):
        """
        Load auto-response schedule from file.
        
        Returns:
            dict: Schedule configuration
        """
        default_schedule = {
            "active": False,
            "channels": {
                "text": False,
                "email": False
            },
            "schedule": {
                "enabled": False,
                "start_time": "09:00",
                "end_time": "17:00",
                "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            },
            "confidence_threshold": 0.7,
            "auto_response_enabled_until": None
        }
        
        if os.path.exists(SCHEDULE_CONFIG_PATH):
            try:
                with open(SCHEDULE_CONFIG_PATH, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading schedule config: {str(e)}")
                return default_schedule
        else:
            # Create default schedule file
            with open(SCHEDULE_CONFIG_PATH, 'w') as f:
                json.dump(default_schedule, f, indent=2)
            return default_schedule
    
    def save_schedule(self):
        """Save the current schedule configuration to file."""
        with open(SCHEDULE_CONFIG_PATH, 'w') as f:
            json.dump(self.schedule, f, indent=2)
    
    def update_schedule(self, schedule_data):
        """
        Update the auto-response schedule.
        
        Args:
            schedule_data: New schedule configuration
            
        Returns:
            dict: Updated schedule
        """
        self.schedule.update(schedule_data)
        self.save_schedule()
        
        # Update active status based on new schedule
        self._update_active_status()
        
        return self.schedule
    
    def _update_active_status(self):
        """Update the active status based on current schedule and time."""
        if not self.schedule["active"]:
            self.active = False
            return
        
        # Check if auto-response is enabled until a specific time
        if self.schedule["auto_response_enabled_until"]:
            end_time = datetime.fromisoformat(self.schedule["auto_response_enabled_until"])
            if datetime.now() < end_time:
                self.active = True
                return
            else:
                # Reset if the end time has passed
                self.schedule["auto_response_enabled_until"] = None
                self.save_schedule()
        
        # Check scheduled times if enabled
        if self.schedule["schedule"]["enabled"]:
            now = datetime.now()
            current_day = now.strftime("%A")
            
            if current_day in self.schedule["schedule"]["days"]:
                start_time = datetime.strptime(self.schedule["schedule"]["start_time"], "%H:%M").time()
                end_time = datetime.strptime(self.schedule["schedule"]["end_time"], "%H:%M").time()
                current_time = now.time()
                
                if start_time <= current_time <= end_time:
                    self.active = True
                    return
        
        self.active = False
    
    def enable_auto_response(self, duration_hours=4):
        """
        Enable auto-response for a specified duration.
        
        Args:
            duration_hours: Number of hours to enable auto-response
            
        Returns:
            dict: Updated schedule
        """
        end_time = datetime.now() + timedelta(hours=duration_hours)
        self.schedule["active"] = True
        self.schedule["auto_response_enabled_until"] = end_time.isoformat()
        self.save_schedule()
        self._update_active_status()
        
        return self.schedule
    
    def disable_auto_response(self):
        """
        Disable auto-response.
        
        Returns:
            dict: Updated schedule
        """
        self.schedule["active"] = False
        self.schedule["auto_response_enabled_until"] = None
        self.save_schedule()
        self._update_active_status()
        
        return self.schedule
    
    def is_auto_response_active(self, channel=None):
        """
        Check if auto-response is currently active.
        
        Args:
            channel: Optional channel to check (text or email)
            
        Returns:
            bool: True if auto-response is active for the specified channel
        """
        self._update_active_status()
        
        if not self.active:
            return False
        
        if channel and not self.schedule["channels"].get(channel, False):
            return False
            
        return True
    
    def start_listeners(self):
        """Start all message listener threads."""
        if self.schedule["channels"].get("text", False):
            self._start_text_listener()
        
        if self.schedule["channels"].get("email", False):
            self._start_email_listener()
    
    def stop_listeners(self):
        """Stop all message listener threads."""
        for name, thread_info in self.listener_threads.items():
            if thread_info["thread"].is_alive():
                thread_info["stop_event"].set()
                thread_info["thread"].join(timeout=5)
                logger.info(f"Stopped {name} listener")
    
    def _start_text_listener(self):
        """Start the text message listener thread."""
        if "text_listener" in self.listener_threads and self.listener_threads["text_listener"]["thread"].is_alive():
            logger.info("Text listener already running")
            return
        
        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._text_listener_thread,
            args=(stop_event,),
            daemon=True
        )
        thread.start()
        
        self.listener_threads["text_listener"] = {
            "thread": thread,
            "stop_event": stop_event
        }
        
        logger.info("Started text message listener")
    
    def _start_email_listener(self):
        """Start the email listener thread."""
        if "email_listener" in self.listener_threads and self.listener_threads["email_listener"]["thread"].is_alive():
            logger.info("Email listener already running")
            return
        
        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._email_listener_thread,
            args=(stop_event,),
            daemon=True
        )
        thread.start()
        
        self.listener_threads["email_listener"] = {
            "thread": thread,
            "stop_event": stop_event
        }
        
        logger.info("Started email listener")
    
    def _text_listener_thread(self, stop_event):
        """
        Text message listener thread function.
        
        This function will be implemented to use Twilio's webhook API.
        For now, it's a placeholder that logs activity.
        
        Args:
            stop_event: Threading event to signal when to stop the thread
        """
        logger.info("Text message listener thread started")
        
        while not stop_event.is_set():
            # This will be replaced with actual Twilio webhook handling
            # For now, just sleep and check the stop event
            time.sleep(5)
            
            # Check if auto-response is active
            if self.is_auto_response_active("text"):
                logger.debug("Auto-response is active for text messages")
            else:
                logger.debug("Auto-response is inactive for text messages")
        
        logger.info("Text message listener thread stopped")
    
    def _email_listener_thread(self, stop_event):
        """
        Email listener thread function.
        
        This function will be implemented to use Gmail API with push notifications.
        For now, it's a placeholder that logs activity.
        
        Args:
            stop_event: Threading event to signal when to stop the thread
        """
        logger.info("Email listener thread started")
        
        while not stop_event.is_set():
            # This will be replaced with actual Gmail API integration
            # For now, just sleep and check the stop event
            time.sleep(5)
            
            # Check if auto-response is active
            if self.is_auto_response_active("email"):
                logger.debug("Auto-response is active for emails")
            else:
                logger.debug("Auto-response is inactive for emails")
        
        logger.info("Email listener thread stopped")
    
    def handle_incoming_text(self, from_number, message_body, media_urls=None):
        """
        Handle an incoming text message.
        
        Args:
            from_number: Phone number the message is from
            message_body: Content of the message
            media_urls: Optional list of media URLs attached to the message
            
        Returns:
            dict: Result of handling the message, including response if generated
        """
        logger.info(f"Received text message from {from_number}")
        
        # Check if auto-response is active
        if not self.is_auto_response_active("text"):
            logger.info("Auto-response is inactive for text messages, ignoring")
            return {"status": "ignored", "reason": "auto-response inactive"}
        
        # Generate response using the hybrid generator
        if self.hybrid_response_generator:
            try:
                # Create a conversation ID based on the phone number
                conversation_id = f"text_{from_number.replace('+', '')}"
                
                # Generate response using the hybrid generator
                ai_response = self.hybrid_response_generator.generate_response(
                    message_body, 
                    conversation_id,
                    channel="text"
                )
                
                # Log the interaction for feedback if feedback system is available
                if self.feedback_system:
                    self.feedback_system.log_interaction(
                        user_message=message_body,
                        ai_response=ai_response,
                        conversation_id=conversation_id,
                        channel="text",
                        metadata={
                            "from_number": from_number,
                            "media_urls": media_urls
                        }
                    )
                
                # Save to chat history
                self._save_to_chat_history(
                    user_message=message_body,
                    ai_response=ai_response,
                    conversation_id=conversation_id,
                    channel="text"
                )
                
                return {
                    "status": "responded",
                    "from": from_number,
                    "message": message_body,
                    "media": media_urls,
                    "auto_response": ai_response
                }
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                return {
                    "status": "error",
                    "reason": f"Error generating response: {str(e)}",
                    "from": from_number,
                    "message": message_body
                }
        else:
            logger.warning("No hybrid generator available, cannot generate response")
            return {
                "status": "error",
                "reason": "No response generator available",
                "from": from_number,
                "message": message_body
            }
    
    def handle_incoming_email(self, from_email, subject, body, attachments=None):
        """
        Handle an incoming email.
        
        Args:
            from_email: Email address the message is from
            subject: Subject of the email
            body: Body content of the email
            attachments: Optional list of attachments
            
        Returns:
            dict: Result of handling the email, including response if generated
        """
        logger.info(f"Received email from {from_email} with subject: {subject}")
        
        # Check if auto-response is active
        if not self.is_auto_response_active("email"):
            logger.info("Auto-response is inactive for emails, ignoring")
            return {"status": "ignored", "reason": "auto-response inactive"}
        
        # Here we would process the email and generate a response using the hybrid generator
        # For now, return a placeholder
        return {
            "status": "received",
            "from": from_email,
            "subject": subject,
            "body": body,
            "attachments": attachments,
            "auto_response": "Auto-response feature is being implemented"
        }

    def _save_to_chat_history(self, user_message, ai_response, conversation_id, channel):
        """
        Save messages to chat history.
        
        Args:
            user_message: The message from the user
            ai_response: The response from the AI
            conversation_id: ID of the conversation
            channel: The channel (text or email)
        """
        try:
            import uuid
            from datetime import datetime
            import json
            import os
            
            # Path to chat history file
            chat_history_path = os.path.join(DATA_DIR, 'chat_history.json')
            
            # Generate unique IDs for messages
            user_message_id = str(uuid.uuid4())
            clone_message_id = str(uuid.uuid4())
            
            # Current timestamp with Z suffix for UTC
            timestamp = datetime.now().isoformat() + "Z"
            
            # Model version (hardcoded for now, could be made configurable)
            model_version = "v1.4"
            
            # Create message objects
            user_msg = {
                "sender": "user",
                "text": user_message,
                "timestamp": timestamp,
                "channel": channel,
                "id": user_message_id,
                "model_version": model_version
            }
            
            clone_msg = {
                "sender": "clone",
                "text": ai_response,
                "timestamp": timestamp,
                "channel": channel,
                "id": clone_message_id,
                "model_version": model_version
            }
            
            # Load existing chat history
            chat_history = []
            if os.path.exists(chat_history_path):
                try:
                    with open(chat_history_path, 'r') as f:
                        chat_history = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading chat history: {str(e)}")
                    # Create a new chat history if loading fails
                    chat_history = []
            
            # Find the conversation or create a new one
            conversation_found = False
            for conv in chat_history:
                if conv.get("id") == conversation_id:
                    conv["messages"].append(user_msg)
                    conv["messages"].append(clone_msg)
                    conversation_found = True
                    break
            
            if not conversation_found:
                new_conversation = {
                    "id": conversation_id,
                    "messages": [user_msg, clone_msg],
                    "model_version": model_version
                }
                chat_history.append(new_conversation)
            
            # Save updated chat history
            with open(chat_history_path, 'w') as f:
                json.dump(chat_history, f, indent=2)
            
            logger.info(f"Saved messages to chat history for conversation {conversation_id}")
            
            # Add to RAG system if available
            self._add_to_rag(user_message, ai_response, conversation_id, channel)
            
        except Exception as e:
            logger.error(f"Error saving to chat history: {str(e)}")
    
    def _add_to_rag(self, user_message, ai_response, conversation_id, channel):
        """
        Add interaction to RAG system.
        
        Args:
            user_message: The message from the user
            ai_response: The response from the AI
            conversation_id: ID of the conversation
            channel: The channel (text or email)
        """
        try:
            # Import here to avoid circular imports
            from rag.app_integration import add_interaction_to_rag
            
            # Add to RAG system
            add_interaction_to_rag(
                user_message=user_message,
                ai_response=ai_response,
                conversation_history=None,  # We don't have the full history here
                model_version="v1.4"
            )
            
            logger.info(f"Added interaction to RAG system for conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Error adding to RAG system: {str(e)}")

# Register routes
@message_listener_bp.route('/auto-response/status', methods=['GET'])
def get_auto_response_status():
    """Get the current status of the auto-response system."""
    service = get_message_listener_service()
    service._update_active_status()
    
    return jsonify({
        "active": service.active,
        "schedule": service.schedule
    })

@message_listener_bp.route('/auto-response/enable', methods=['POST'])
def enable_auto_response():
    """Enable auto-response for a specified duration."""
    service = get_message_listener_service()
    data = request.json or {}
    duration_hours = data.get('duration_hours', 4)
    
    updated_schedule = service.enable_auto_response(duration_hours)
    
    return jsonify({
        "status": "enabled",
        "active": service.active,
        "schedule": updated_schedule
    })

@message_listener_bp.route('/auto-response/disable', methods=['POST'])
def disable_auto_response():
    """Disable auto-response."""
    service = get_message_listener_service()
    updated_schedule = service.disable_auto_response()
    
    return jsonify({
        "status": "disabled",
        "active": service.active,
        "schedule": updated_schedule
    })

@message_listener_bp.route('/auto-response/schedule', methods=['POST'])
def update_auto_response_schedule():
    """Update the auto-response schedule."""
    service = get_message_listener_service()
    data = request.json or {}
    
    updated_schedule = service.update_schedule(data)
    
    return jsonify({
        "status": "updated",
        "active": service.active,
        "schedule": updated_schedule
    })

# Singleton instance
_message_listener_service = None

def get_message_listener_service(hybrid_response_generator=None, feedback_system=None):
    """
    Get the singleton instance of the MessageListenerService.
    
    Args:
        hybrid_response_generator: Optional HybridResponseGenerator instance
        feedback_system: Optional FeedbackSystem instance
        
    Returns:
        MessageListenerService: Singleton instance
    """
    global _message_listener_service
    
    if _message_listener_service is None:
        _message_listener_service = MessageListenerService(
            hybrid_response_generator=hybrid_response_generator,
            feedback_system=feedback_system
        )
    
    return _message_listener_service

# Example usage
if __name__ == "__main__":
    service = get_message_listener_service()
    print(f"Auto-response active: {service.is_auto_response_active()}")
    print(f"Schedule: {json.dumps(service.schedule, indent=2)}")
