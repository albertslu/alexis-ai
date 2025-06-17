#!/usr/bin/env python3
"""
Mac Message Listener for AI Clone

This script monitors the Mac Messages database for new messages and
forwards them to the AI clone for automated responses.
"""

import os
import sys
import time
import sqlite3
import json
import subprocess
import requests
import signal
from datetime import datetime
from pathlib import Path
import argparse
import uuid

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the send_imessage script
from scripts.send_ai_message import send_imessage_background, generate_message
# Import the model configuration
from model_config import get_current_model
# Import the visual message module
from scripts.visual_message import send_visual_imessage, type_visual_imessage

# Path to Messages database
MESSAGES_DB = Path.home() / "Library/Messages/chat.db"

# Backend API URL
API_URL = os.environ.get('API_URL', 'http://localhost:5002')

class MacMessageListener:
    def __init__(self, auto_respond=True, check_interval=5, allowed_numbers=None, add_to_rag=False, user_id=None, visual_mode=False):
        """
        Initialize the Mac Message Listener
        
        Args:
            auto_respond: Whether to automatically respond to messages
            check_interval: How often to check for new messages (in seconds)
            allowed_numbers: List of phone numbers to auto-respond to (None for all)
            add_to_rag: Whether to add messages to the RAG database for training
            user_id: User ID to use for model and memories from MongoDB
        """
        self.auto_respond = auto_respond
        self.check_interval = check_interval
        self.last_message_id = self._get_last_message_id()
        self.contacts_cache = {}
        self.allowed_numbers = allowed_numbers or []
        self.add_to_rag = add_to_rag
        self.current_conversation_id = None
        self.user_id = user_id or "default"  # Use default if no user_id provided
        self.visual_mode = visual_mode  # Whether to use visual mode for sending messages
        
        print(f"Mac Message Listener initialized (add_to_rag={self.add_to_rag})")
        print(f"Auto-respond: {self.auto_respond}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Starting from message ID: {self.last_message_id}")
        if self.allowed_numbers:
            print(f"Auto-responding only to these numbers: {', '.join(self.allowed_numbers)}")
        else:
            print("Auto-responding to all numbers")
        
    def _get_last_message_id(self):
        """Get the ID of the last message in the database"""
        try:
            conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
            cursor = conn.execute("SELECT MAX(ROWID) FROM message")
            last_id = cursor.fetchone()[0] or 0
            conn.close()
            return last_id
        except Exception as e:
            print(f"Error getting last message ID: {e}")
            return 0
    
    def _get_contact_info(self, conn, handle_id):
        """
        Get contact info for a handle_id
        
        Args:
            conn: Database connection
            handle_id: Handle ID to look up
            
        Returns:
            Contact ID (phone number or email)
        """
        if handle_id in self.contacts_cache:
            return self.contacts_cache[handle_id]
            
        try:
            cursor = conn.execute("SELECT id FROM handle WHERE ROWID = ?", (handle_id,))
            result = cursor.fetchone()
            if result:
                contact_id = result[0]
                self.contacts_cache[handle_id] = contact_id
                return contact_id
            return None
        except Exception as e:
            print(f"Error getting contact info: {e}")
            return None
            
    def _get_chat_id(self, conn, handle_id):
        """
        Get the chat ID for a given handle_id from the database
        
        Args:
            conn: Database connection
            handle_id: Handle ID to look up
            
        Returns:
            Chat ID if found, None otherwise
        """
        try:
            # Query the chat_handle_join table to find the chat_id associated with this handle
            cursor = conn.execute("""
                SELECT chat_id FROM chat_handle_join 
                WHERE handle_id = ?
                ORDER BY chat_id DESC
                LIMIT 1
            """, (handle_id,))
            
            result = cursor.fetchone()
            if result:
                chat_id = result[0]
                print(f"Found chat_id {chat_id} for handle_id {handle_id}")
                return chat_id
            else:
                print(f"No chat found for handle_id {handle_id}")
                return None
        except Exception as e:
            print(f"Error getting chat ID: {e}")
            return None
    
    def _should_save_message_from_contact(self, contact_id):
        """
        Determine if we should save messages from this contact
        
        Args:
            contact_id: The contact ID (phone number or email)
            
        Returns:
            bool: True if we should save messages from this contact, False otherwise
        """
        # If no allowed numbers are specified, save messages from everyone
        if not self.allowed_numbers:
            print(f"No allowed numbers specified, saving messages from all contacts including {contact_id}")
            return True
            
        # Normalize the contact_id for comparison
        normalized_contact = self._normalize_phone_number(contact_id)
        
        # Check if the contact is in the allowed list
        for allowed in self.allowed_numbers:
            # Normalize the allowed number
            normalized_allowed = self._normalize_phone_number(allowed)
            
            # Compare the normalized numbers
            if normalized_contact == normalized_allowed:
                print(f"Contact {contact_id} is in allowed list, will save messages")
                return True
                
        print(f"Contact {contact_id} is not in allowed list, will not save messages")
        return False
        
    def _should_generate_response(self, contact_id):
        """
        Determine if we should generate a response for this contact
        
        Args:
            contact_id: The contact ID (phone number or email)
            
        Returns:
            bool: True if we should generate a response, False otherwise
        """
        # If no allowed numbers are specified, generate responses for everyone
        if not self.allowed_numbers:
            print(f"No allowed numbers specified, generating response for {contact_id}")
            return True
            
        # Normalize the contact_id for comparison
        normalized_contact = self._normalize_phone_number(contact_id)
        print(f"Normalized contact number: {normalized_contact} (original: {contact_id})")
        
        # Check if the contact is in the allowed list
        for allowed in self.allowed_numbers:
            # Normalize the allowed number
            normalized_allowed = self._normalize_phone_number(allowed)
            print(f"Checking against allowed number: {normalized_allowed} (original: {allowed})")
            
            # Compare the normalized numbers
            if normalized_contact == normalized_allowed:
                print(f"Contact {contact_id} is in allowed list, will generate response")
                return True
                
        print(f"Contact {contact_id} is not in allowed list, will not generate response")
        return False
    
    def _should_auto_send_response(self, contact_id):
        """
        Determine if we should automatically send a response to this contact
        
        Args:
            contact_id: The contact ID (phone number or email)
            
        Returns:
            bool: True if we should auto-send, False otherwise
        """
        # If auto-respond is disabled, never auto-send
        if not self.auto_respond:
            print(f"Auto-respond is disabled, not auto-sending to {contact_id}")
            return False
            
        # Otherwise, use the same logic as for generating responses
        return self._should_generate_response(contact_id)
    
    def _normalize_phone_number(self, number):
        """
        Normalize a phone number for comparison by removing all non-digit characters
        and ensuring it has a consistent format.
        
        Args:
            number: The phone number to normalize
            
        Returns:
            str: Normalized phone number with only digits
        """
        # Handle email addresses (don't try to normalize them)
        if '@' in number:
            return number
            
        # Remove all non-digit characters
        digits_only = ''.join(c for c in number if c.isdigit())
        
        # If it's a 10-digit US number without country code, add +1
        if len(digits_only) == 10:
            return "1" + digits_only
            
        # If it already has a country code (11+ digits), keep it as is
        return digits_only
        
    # Method removed as we're using the simpler hallucination detection
    
    def _forward_to_ai_clone(self, message_text, sender_id):
        """
        Forward the message to the AI clone backend for processing
        
        Args:
            message_text: The text of the message
            sender_id: The ID of the sender
            
        Returns:
            The AI's response or None if there was an error
        """
        global running
        try:
            # Prepare the request data
            request_data = {
                "message": message_text,
                "sender": sender_id,
                "channel": "imessage",
                "use_enhanced_rag": True,  # Ensure enhanced RAG is used
                "addToRag": self.add_to_rag,  # Use the configured setting
                "user_id": self.user_id  # Include the user ID to use the correct model and memories
            }
            
            print(f"Using addToRag={self.add_to_rag} for this message")
            
            # Log the message length for debugging
            message_length = len(message_text.strip())
            if message_length < 5:
                print(f"INFO: Received a very short message ({message_length} chars). Forwarding to RAG system.")
            
            
            print(f"Preparing API call to {API_URL}/api/handle_message")
            print(f"Request data: {request_data}")
            
            # Use the enhanced RAG system through the handle_message endpoint
            try:
                response = requests.post(
                    f"{API_URL}/api/handle_message",
                    json=request_data,
                    timeout=60  # Increased timeout for memory-enhanced RAG processing
                )
                
                print(f"Sent request to handle_message API: {message_text[:30]}...")
                print(f"Response status code: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        ai_response = response_data.get("response")
                        if ai_response:
                            print(f"Received response from API: {ai_response[:50]}...")
                            
                            # No need for quality checks with RAG system
                            # Just log the response length for debugging purposes
                            if len(ai_response.strip()) < 10:
                                print(f"INFO: API returned a short response: '{ai_response}'.")
                            
                            return ai_response
                        else:
                            print("API returned 200 but no 'response' field in the JSON data")
                            print(f"Full response data: {response_data}")
                    except Exception as json_error:
                        print(f"Error parsing JSON response: {str(json_error)}")
                        print(f"Raw response text: {response.text[:200]}")
                else:
                    print(f"API call failed with status code {response.status_code}")
                    print(f"Response headers: {response.headers}")
                    print(f"Response text: {response.text[:200]}")
            except requests.exceptions.ConnectionError as conn_error:
                print(f"Connection error when calling API: {str(conn_error)}")
                print("Is the backend server running on port 5002?")
            except requests.exceptions.Timeout as timeout_error:
                print(f"Timeout error when calling API: {str(timeout_error)}")
                print("The request took too long to complete. The server might be overloaded.")
            except requests.exceptions.RequestException as req_error:
                print(f"Request error when calling API: {str(req_error)}")
            
            # Don't use fallbacks - if the API call fails, terminate the listener
            print("API call failed. Terminating listener...")
            running = False
            return None
            
        except Exception as e:
            print(f"Error forwarding to AI clone: {str(e)}")
            import traceback
            traceback.print_exc()
            print("Terminating listener due to error...")
            running = False
            return None
    
    def _send_response(self, contact_id, response_text, use_visual=False, handle_id=None):
        """
        Send the AI's response back to the contact
        
        Args:
            contact_id: The ID of the contact to respond to
            response_text: The text to send
            use_visual: Whether to send the message visually through the Messages app
            handle_id: The handle_id from the database (used to find the chat_id)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if use_visual:
                # If we have a handle_id, try to get the chat_id for more reliable conversation finding
                chat_id = None
                if handle_id:
                    try:
                        conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
                        chat_id = self._get_chat_id(conn, handle_id)
                        conn.close()
                    except Exception as e:
                        print(f"Error getting chat ID: {e}")
                
                print(f"Using recipient: {contact_id}")
                print("Sending message visually through Messages app...")
                
                if chat_id:
                    print(f"Using chat_id: {chat_id} for more reliable conversation finding")
                
                # Send the message visually
                return send_visual_imessage(contact_id, response_text, chat_id)
            else:
                # Send the message in the background
                print("Sending message in the background...")
                return send_imessage_background(contact_id, response_text)
        except Exception as e:
            print(f"Error sending response: {e}")
            return False
    
    def save_message_to_history(self, message_text, is_from_me=False, user_id="default"):
        """
        Save a message to the chat history
        
        Args:
            message_text: The text of the message
            is_from_me: Whether the message is from the user (True) or the AI (False)
            user_id: User ID for the chat history (default: default)
        """
        try:
            # Create a message object
            message = {
                "sender": "clone" if is_from_me else "user",
                "text": message_text,
                "timestamp": datetime.now().isoformat(),
                "id": str(uuid.uuid4()),
                "channel": "imessage",
                "model_version": get_current_model(),
                "add_to_rag": self.add_to_rag
            }
            
            # Path to user-specific chat history
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            chat_histories_dir = os.path.join(base_dir, 'data', 'chat_histories')
            
            # Ensure the chat_histories directory exists
            os.makedirs(chat_histories_dir, exist_ok=True)
            
            # User-specific chat history path
            chat_history_path = os.path.join(chat_histories_dir, f"user_{user_id}_chat_history.json")
            
            # If user-specific file doesn't exist, fall back to the default
            if not os.path.exists(chat_history_path):
                print(f"User-specific chat history not found for {user_id}, using default")
                chat_history_path = os.path.join(base_dir, 'data', 'chat_history.json')
                
                # If default doesn't exist either, create a new one
                if not os.path.exists(chat_history_path):
                    print(f"Default chat history not found, creating new file")
                    with open(chat_history_path, 'w') as f:
                        json.dump({"conversations": []}, f)
            
            # Load the existing chat history with proper structure
            try:
                with open(chat_history_path, 'r') as f:
                    chat_history = json.load(f)
                    
                    # Verify the expected structure exists
                    if not isinstance(chat_history, dict):
                        print("Warning: chat history is not in expected format, creating new structure")
                        chat_history = {"conversations": []}
                    elif "conversations" not in chat_history:
                        print("Warning: chat history missing 'conversations' key, creating it")
                        chat_history["conversations"] = []
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Creating new chat history structure: {e}")
                chat_history = {"conversations": []}
            
            # If this is a user message (not from the AI), create a new conversation
            if not is_from_me:
                # Create a new conversation with this message
                new_conversation = {
                    "id": str(uuid.uuid4()),
                    "messages": [message],
                    "model_version": get_current_model()
                }
                
                # Add the new conversation to the beginning of the list
                chat_history["conversations"].insert(0, new_conversation)
                
                # Store the conversation ID for the AI response
                self.current_conversation_id = new_conversation["id"]
                
            else:
                # This is an AI response, add it to the current conversation
                # Find the conversation with the stored ID
                for conversation in chat_history["conversations"]:
                    if conversation["id"] == self.current_conversation_id:
                        conversation["messages"].append(message)
                        break
            
            # Save updated chat history
            with open(chat_history_path, 'w') as f:
                json.dump(chat_history, f, indent=2)
                
            print(f"Added message to chat history: {message_text[:30]}...")
            return True
        except Exception as e:
            print(f"Error saving to chat history: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def check_for_new_messages(self):
        """Check for new messages and process them"""
        global running
        try:
            print(f"Attempting to connect to Messages database at: {MESSAGES_DB}")
            conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
            print("Successfully connected to Messages database")
            
            # Query for new messages (not from me)
            cursor = conn.execute("""
                SELECT ROWID, handle_id, text, date 
                FROM message 
                WHERE ROWID > ? AND is_from_me = 0 AND text IS NOT NULL
                ORDER BY date ASC
            """, (self.last_message_id,))
            
            new_messages = cursor.fetchall()
            if new_messages:
                print(f"Found {len(new_messages)} new messages")
            else:
                print(f"No new messages found. Last message ID: {self.last_message_id}")
                
            # Process each new message
            for message in new_messages:
                message_id, handle_id, text, date = message
                self.last_message_id = max(self.last_message_id, message_id)
                
                # Get contact info
                contact_id = self._get_contact_info(conn, handle_id)
                if not contact_id:
                    print(f"Could not find contact for handle_id {handle_id}")
                    continue
                
                print(f"New message from {contact_id}: {text}")
                
                # Check if we should save this message
                should_save = self._should_save_message_from_contact(contact_id)
                if should_save:
                    # Save incoming message to chat history
                    self.save_message_to_history(text, is_from_me=False, user_id=contact_id)
                    print(f"Saved message from {contact_id} to chat history")
                else:
                    print(f"Not saving message from {contact_id} (not in allowed list)")
                
                # Check if we should generate a response
                should_generate = self._should_generate_response(contact_id)
                if should_generate:
                    # Generate a response regardless of auto-respond setting
                    print(f"Generating response for message from {contact_id}")
                    response = self._forward_to_ai_clone(text, contact_id)
                    
                    if response:
                        print(f"AI response: {response}")
                        
                        # Check if we should auto-send the response
                        should_auto_send = self._should_auto_send_response(contact_id)
                        if should_auto_send:
                            print(f"Auto-responding to {contact_id}")
                            # Send the response, passing the handle_id for more reliable conversation finding
                            if self._send_response(contact_id, response, use_visual=self.visual_mode, handle_id=handle_id):
                                print(f"Response sent to {contact_id}")
                                
                                # Only save outgoing message to chat history if the contact is in the allowed list
                                if should_save:
                                    self.save_message_to_history(response, is_from_me=True, user_id=contact_id)
                                    print(f"Saved response to {contact_id} in chat history")
                                else:
                                    print(f"Not saving response to {contact_id} (not in allowed list)")
                            else:
                                print(f"Failed to send response to {contact_id}")
                        else:
                            # Auto-respond is disabled, type the message but don't send it
                            print(f"Auto-respond is disabled. Typing response without sending...")
                            
                            # Type the message in the Messages app without sending it
                            if self.visual_mode:
                                # Get chat_id for more reliable conversation finding
                                chat_id = None
                                if handle_id:
                                    try:
                                        conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
                                        chat_id = self._get_chat_id(conn, handle_id)
                                        conn.close()
                                    except Exception as e:
                                        print(f"Error getting chat ID: {e}")
                                
                                # Type the message without sending
                                if type_visual_imessage(contact_id, response, chat_id):
                                    print(f"Response typed (not sent) to {contact_id}")
                                else:
                                    print(f"Failed to type response to {contact_id}")
                            else:
                                print(f"Visual mode is disabled. Enable visual mode to see responses in Messages app.")
                else:
                    print(f"Not generating response for {contact_id} (not in allowed list)")
            
            conn.close()
        except Exception as e:
            print(f"Error checking for new messages: {e}")
            print("Terminating listener due to error...")
            running = False
    
    def run(self):
        """Run the message listener in a loop"""
        global running
        
        print("Starting Mac Message Listener...")
        print(f"Monitoring Messages database at: {MESSAGES_DB}")
        print("Press Ctrl+C to stop")
        
        # If in visual mode, open the Messages app at startup
        if self.visual_mode:
            print("Visual mode enabled - opening Messages app...")
            try:
                # Import the subprocess module
                import subprocess
                
                # Open the Messages app
                subprocess.run(["open", "-a", "Messages"], check=False)
                print("Messages app opened successfully")
                # Give it a moment to open
                time.sleep(1.5)
            except Exception as e:
                print(f"Error opening Messages app: {e}")
        
        # Check if the database exists and is accessible
        if not os.path.exists(MESSAGES_DB):
            print(f"ERROR: Messages database not found at {MESSAGES_DB}")
            print("Make sure Messages app has been run at least once and permissions are correct")
            print("Trying to continue anyway...")
        
        try:
            # Use the global running flag to control the loop
            while running:
                try:
                    self.check_for_new_messages()
                except sqlite3.OperationalError as e:
                    print(f"Database error: {e}")
                    print("This could be due to permissions or database lock issues")
                    print("Continuing to run despite error...")
                except Exception as e:
                    print(f"Error in check_for_new_messages: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue running despite errors
                    print("Continuing to run despite error...")
                
                # Print a heartbeat message every 10 cycles to show the script is still alive
                if (int(time.time()) // self.check_interval) % 10 == 0:
                    print(f"Listener heartbeat: still running at {datetime.now().strftime('%H:%M:%S')}")
                
                # Check if we should exit before sleeping
                if not running:
                    break
                    
                # Use a shorter sleep interval and check the running flag more frequently
                # This allows for faster response to termination signals
                for _ in range(self.check_interval):
                    if not running:
                        break
                    time.sleep(1)
            
            print("\nMac Message Listener stopped gracefully")
        except KeyboardInterrupt:
            print("\nStopping Mac Message Listener...")
        except Exception as e:
            print(f"Fatal error in message listener: {e}")
            import traceback
            traceback.print_exc()
    
# Flag to control the main loop
running = True

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    global running
    print(f"\nReceived signal {sig}, shutting down gracefully...")
    running = False

def main():
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description='Mac Message Listener for AI Clone')
    parser.add_argument('--no-auto-respond', action='store_true', help='Disable auto-responses')
    parser.add_argument('--interval', type=int, default=5, help='Check interval in seconds')
    parser.add_argument('--allowed-numbers', nargs='+', help='List of phone numbers to auto-respond to')
    parser.add_argument('--add-to-rag', action='store_true', help='Add messages to RAG database for training')
    parser.add_argument('--user-id', type=str, help='User ID to use for model and memories from MongoDB')
    parser.add_argument('--visual', action='store_true', help='Use visual mode to send messages through the Messages app')
    args = parser.parse_args()
    
    listener = MacMessageListener(
        auto_respond=not args.no_auto_respond,
        check_interval=args.interval,
        allowed_numbers=args.allowed_numbers,
        add_to_rag=args.add_to_rag,
        user_id=args.user_id,
        visual_mode=args.visual
    )
    listener.run()

if __name__ == "__main__":
    main()
