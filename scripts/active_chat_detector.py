#!/usr/bin/env python3
"""
Active Chat Detector for Alexis AI

This script detects the active chat in the Messages app, retrieves the conversation context,
generates message suggestions, and sends those suggestions to the overlay agent.
"""

import os
import re
import sys
import time
import json
import sqlite3
import logging
import argparse
import traceback
import subprocess
import websocket
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Set up logging first
logger = logging.getLogger('active_chat_detector')
logger.setLevel(logging.INFO)

# No longer importing message_suggestions module as we're using the backend API directly

# Create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add handler to logger
logger.addHandler(ch)

# Create file handler for detailed logging
try:
    # Create logs directory in the application's data directory if it doesn't exist
    app_data_dir = os.path.expanduser("~/Library/Application Support/alexis-ai-desktop")
    logs_dir = os.path.join(app_data_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create file handler
    log_file = os.path.join(logs_dir, "active_chat_detector.log")
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)  # Set to DEBUG to capture all log levels
    fh.setFormatter(formatter)
    
    # Add file handler to logger
    logger.addHandler(fh)
    
    logger.info(f"Logging to file: {log_file}")
except Exception as e:
    logger.error(f"Failed to set up file logging: {e}")
    logger.error(traceback.format_exc())

# Constants
MESSAGES_DB = os.path.expanduser("~/Library/Messages/chat.db")
API_URL = os.environ.get("API_URL", "http://localhost:5002")

def extract_text_from_attributed_body(blob):
    """
    Extract plain text from NSAttributedString BLOB data
    """
    if not blob:
        return ""
    
    # Convert blob to readable characters
    readable = ''.join([chr(b) if 32 <= b <= 126 else ' ' for b in blob])
    
    # Look for the pattern: NSString followed by message text before iI
    # The pattern seems to be: NSString....+"[MESSAGE]"...iI
    message_pattern = re.search(r'NSString[^"]*\+"([^"]+)"', readable)
    if message_pattern:
        message_text = message_pattern.group(1).strip()
        if message_text and len(message_text) > 1:
            return message_text
    
    # Alternative pattern: look for text between NSString and iI
    alt_pattern = re.search(r'NSString[^a-zA-Z]*([A-Za-z][^.]*?)(?:\s*iI|\s*\.\.\.)', readable)
    if alt_pattern:
        message_text = alt_pattern.group(1).strip()
        # Remove any remaining artifacts
        message_text = re.sub(r'\s*iI\s*', '', message_text)
        message_text = re.sub(r'\s+', ' ', message_text).strip()
        if message_text and len(message_text) > 1:
            return message_text
    
    # Fallback: Try to find readable text patterns and filter out metadata
    text_patterns = re.findall(r'[A-Za-z][A-Za-z0-9\s,.\'\!\?\-\/\(\)]*[A-Za-z0-9\.\!\?]', readable)
    
    # Filter out metadata patterns
    filtered_patterns = []
    for pattern in text_patterns:
        pattern = pattern.strip()
        # Keep patterns that look like actual message content
        if (len(pattern) > 3 and 
            'NSString' not in pattern and
            'NSObject' not in pattern and
            'NSAttributed' not in pattern and
            'NSNumber' not in pattern and
            'NSValue' not in pattern and
            'NSDictionary' not in pattern and
            'kIMMessage' not in pattern and
            'streamtyped' not in pattern and
            'AttributeName' not in pattern and
            pattern != 'iI' and
            pattern != 'i' and
            not pattern.isdigit()):
            filtered_patterns.append(pattern)
    
    # Join the patterns and clean up
    extracted_text = ' '.join(filtered_patterns)
    extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
    
    # Final cleanup - remove any remaining "iI" artifacts
    extracted_text = re.sub(r'\s*iI\s*$', '', extracted_text)
    extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
    
    return extracted_text

class ActiveChatDetector:
    """
    Detects the active chat in Messages app and generates suggestions
    """
    
    def __init__(self, check_interval=1.0, websocket_url=None, user_id=None, max_messages=10, test_mode=False):
        """
        Initialize the active chat detector
        
        Args:
            check_interval (float): Interval in seconds to check for active chat changes
            websocket_url (str): WebSocket URL to send suggestions to
            user_id (str): User ID for message suggestions
            max_messages (int): Maximum number of messages to retrieve
            test_mode (bool): Run in test mode (don't send to WebSocket)
        """
        self.check_interval = check_interval
        self.websocket_url = websocket_url
        self.user_id = user_id
        self.max_messages = max_messages
        self.test_mode = test_mode
        self.last_conversation_id = None
        self.ws = None
        
        logger.info("========================================")
        logger.info("ACTIVE CHAT DETECTOR INITIALIZED")
        logger.info("========================================")
        logger.info(f"Check interval: {check_interval} seconds")
        logger.info(f"WebSocket URL: {websocket_url}")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Max messages: {max_messages}")
        logger.info(f"Test mode: {test_mode}")
        logger.info("========================================")
    
    def _connect_websocket(self):
        """Connect to the WebSocket server"""
        if not self.websocket_url:
            logger.error("No WebSocket URL provided")
            return False
        
        try:
            logger.info(f"Connecting to WebSocket server at {self.websocket_url}")
            logger.info(f"WebSocket URL details: host={self.websocket_url.split('://')[1].split(':')[0]}, port={self.websocket_url.split(':')[-1]}")
            
            # Create WebSocket connection with detailed logging
            self.ws = websocket.create_connection(self.websocket_url)
            
            # Log connection details
            logger.info("Connected to WebSocket server successfully")
            logger.info(f"WebSocket connection established: {self.ws is not None}")
            
            # Send a test message to verify connection
            test_data = {"type": "connected", "message": "Active Chat Detector connected"}
            self.ws.send(json.dumps(test_data))
            logger.info(f"Sent test message to WebSocket server: {json.dumps(test_data)}")
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to WebSocket server: {e}")
            logger.error(traceback.format_exc())
            self.ws = None
            return False
    
    def _send_to_websocket(self, data):
        """Send data to the WebSocket server"""
        if self.test_mode:
            logger.info("Test mode: Not sending to WebSocket")
            return True
        
        if not self.ws:
            logger.warning("No WebSocket connection")
            logger.info("Attempting to establish WebSocket connection...")
            if not self._connect_websocket():
                logger.error("Failed to establish WebSocket connection")
                return False
            logger.info("WebSocket connection established successfully")
        
        try:
            # Convert data to JSON string
            json_data = json.dumps(data)
            logger.info(f"Sending JSON data to WebSocket: {json_data[:200]}..." if len(json_data) > 200 else json_data)
            
            # Send data to WebSocket server
            self.ws.send(json_data)
            logger.info(f"Successfully sent {len(json_data)} bytes to WebSocket server")
            
            # Try to receive any response (non-blocking)
            try:
                self.ws.settimeout(0.1)  # Set a short timeout
                response = self.ws.recv()
                logger.info(f"Received response from WebSocket server: {response[:200]}..." if len(response) > 200 else response)
            except websocket.WebSocketTimeoutException:
                logger.info("No immediate response from WebSocket server (expected)")
            except Exception as e:
                logger.warning(f"Error receiving response from WebSocket server: {e}")
            finally:
                self.ws.settimeout(None)  # Reset timeout
            
            return True
        except Exception as e:
            logger.error(f"Error sending to WebSocket server: {e}")
            logger.error(traceback.format_exc())
            logger.warning("WebSocket connection may be closed or invalid")
            logger.info("Attempting to reconnect...")
            self.ws = None
            reconnected = self._connect_websocket()
            if reconnected:
                logger.info("Successfully reconnected to WebSocket server")
                # Try sending again after reconnecting
                try:
                    self.ws.send(json.dumps(data))
                    logger.info("Successfully sent data after reconnecting")
                    return True
                except Exception as e2:
                    logger.error(f"Error sending data after reconnect: {e2}")
                    return False
            else:
                logger.error("Failed to reconnect to WebSocket server")
                return False
    
    def get_active_conversation_id(self):
        """Get the active conversation ID using the defaults command"""
        try:
            logger.debug("Getting active conversation ID")
            result = subprocess.run(
                ["defaults", "read", "com.apple.MobileSMS.plist", "CKLastSelectedItemIdentifier"],
                capture_output=True, text=True, check=False
            )
            
            if result.returncode != 0:
                logger.warning(f"Command failed with return code {result.returncode}")
                logger.warning(f"stderr: {result.stderr}")
                logger.warning("Make sure Messages app is open and you have a conversation selected")
                return None
                
            raw_id = result.stdout.strip()
            logger.debug(f"Raw preference value: {raw_id}")
            
            # The format is typically list-service;-;identifier
            # We want to extract just the identifier part
            if '-' not in raw_id:
                logger.warning(f"Unexpected format for preference value: {raw_id}")
                return raw_id
                
            guid = raw_id.replace(raw_id.split('-')[0] + '-', '')
            logger.debug(f"Extracted GUID: {guid}")
            return guid
        except Exception as e:
            logger.error(f"Error getting active conversation ID: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def get_chat_info(self, conversation_id):
        """Get the chat info for a conversation ID"""
        try:
            logger.info(f"Getting chat info for conversation ID: {conversation_id}")
            
            # Extract the phone number or email from the conversation ID
            # Format is usually: iMessage;-;+1234567890 or iMessage;-;user@example.com
            parts = conversation_id.split(";-;")
            if len(parts) != 2:
                logger.warning(f"Unexpected conversation ID format: {conversation_id}")
                return None
            
            identifier = parts[1]
            logger.info(f"Extracted phone number or email: {identifier}")
            
            # Connect to the Messages database
            conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Query the database for the chat ID
            cursor.execute("""
                SELECT ROWID
                FROM chat
                WHERE guid = ?
            """, (conversation_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                chat_id = result[0]
                logger.info(f"Found chat with ROWID: {chat_id}")
                return chat_id
            else:
                logger.warning(f"No chat found for conversation ID: {conversation_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting chat info: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def get_recent_messages(self, chat_id):
        """Get recent messages for a chat ID"""
        try:
            logger.info(f"Getting recent messages for chat ID: {chat_id}")
            
            # Connect to the Messages database
            conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Query the database for recent messages - include attributedBody for user messages
            cursor.execute("""
                SELECT 
                    message.ROWID,
                    message.text,
                    message.attributedBody,
                    message.is_from_me,
                    message.date,
                    handle.id as handle_id
                FROM message
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                WHERE message.cache_has_attachments = 0
                AND chat_message_join.chat_id = ?
                ORDER BY message.date DESC
                LIMIT ?
            """, (chat_id, self.max_messages))
            
            messages = cursor.fetchall()
            conn.close()
            
            if messages:
                # Convert to list of dicts and reverse to get chronological order
                result = []
                for message in messages:
                    msg_dict = dict(message)
                    
                    # Extract text content properly
                    text = msg_dict.get('text') or ""
                    
                    # If text is empty and this is from the user, try to extract from attributedBody
                    if not text and msg_dict.get('is_from_me') == 1 and msg_dict.get('attributedBody'):
                        extracted_text = extract_text_from_attributed_body(msg_dict['attributedBody'])
                        if extracted_text:
                            text = extracted_text
                            logger.debug(f"Extracted text from attributedBody: {text[:50]}...")
                    
                    # Update the text field with the extracted content
                    msg_dict['text'] = text
                    result.append(msg_dict)
                
                result.reverse()
                logger.info(f"Found {len(result)} messages")
                return result
            else:
                logger.warning(f"No messages found for chat ID: {chat_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def format_conversation(self, messages):
        """Format messages into a conversation context"""
        try:
            logger.info("Formatting conversation context")
            
            lines = []
            
            for message in messages:
                # Convert the date (Mac timestamp) to a readable format
                # Mac timestamp is seconds since 2001-01-01
                mac_epoch = datetime(2001, 1, 1)
                timestamp = mac_epoch + timedelta(seconds=message["date"]/1e9)
                date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                # Format the message
                sender = "Me" if message["is_from_me"] else "Other"
                text = message["text"] or ""
                
                lines.append(f"{sender}: {text}")
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error formatting conversation: {e}")
            logger.error(traceback.format_exc())
            return ""
    
    def generate_suggestions(self, context):
        """
        Get message suggestions from the backend API based on conversation context
        
        Args:
            context: The conversation context
            
        Returns:
            list: List of message suggestions or None if generation fails
        """
        try:
            logger.info("Requesting message suggestions from backend API")
            
            # Prepare API request
            api_url = f"{API_URL}/api/message-suggestions"
            data = {
                "context": context,
                "user_id": self.user_id  # Include the user ID to access the correct model
            }
            
            # Log the full request data for debugging
            logger.info("========== FULL REQUEST DATA ==========")
            logger.info(f"API URL: {api_url}")
            logger.info(f"User ID: {self.user_id}")
            logger.info(f"Context length: {len(context)} characters")
            logger.info(f"Context first 200 chars: {context[:200]}")
            logger.info(f"Context last 200 chars: {context[-200:] if len(context) > 200 else context}")
            logger.info(f"Full request data: {json.dumps(data, indent=2)}")
            logger.info("========================================")
            
            # Send request to backend API
            logger.info(f"Sending POST request to {api_url}")
            response = requests.post(api_url, json=data)
            
            # Log the response details
            logger.info("========== RESPONSE DETAILS ==========")
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {response.headers}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Response JSON: {json.dumps(result, indent=2)[:500]}...")
                
                if result.get('success', False):
                    suggestions = result.get("suggestions", [])
                    logger.info(f"Generated {len(suggestions)} suggestions")
                    for i, suggestion in enumerate(suggestions):
                        logger.info(f"Suggestion {i+1}: {suggestion[:100]}...")
                    return suggestions
                else:
                    logger.error(f"API error: {result.get('error', 'Unknown error')}")
                    return None
            else:
                logger.error(f"Error from backend API: {response.status_code}")
                logger.error(f"Response text: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            logger.error(traceback.format_exc())
            return None

    def send_suggestions(self, suggestions):
        """Send message suggestions to the overlay agent and update the backend API"""
        try:
            logger.info("========== SENDING SUGGESTIONS TO OVERLAY AGENT ==========")
            logger.info(f"Sending {len(suggestions)} suggestions to overlay agent")
            
            # Log each suggestion
            for i, suggestion in enumerate(suggestions):
                logger.info(f"Suggestion {i+1}: {suggestion}")
            
            # Format the data to send to WebSocket
            data = {
                "type": "suggestions",
                "suggestions": suggestions
            }
            
            # Also update the backend API with the latest suggestions
            try:
                logger.info("Updating latest suggestions in backend API")
                api_url = "http://localhost:5002/api/update-suggestions"
                api_data = {
                    "suggestions": suggestions
                }
                response = requests.post(api_url, json=api_data)
                if response.status_code == 200:
                    logger.info("Successfully updated suggestions in backend API")
                else:
                    logger.error(f"Failed to update suggestions in backend API: {response.status_code}")
                    logger.error(f"Response: {response.text}")
            except Exception as e:
                logger.error(f"Error updating suggestions in backend API: {e}")
                logger.error(traceback.format_exc())
            
            if self.test_mode:
                logger.info("Test mode: Not sending suggestions to WebSocket")
                return True
            
            # Check WebSocket connection status
            if not self.ws:
                logger.warning("No active WebSocket connection. Attempting to reconnect...")
                if not self._connect_websocket():
                    logger.error("Failed to establish WebSocket connection. Suggestions will not be displayed.")
                    return False
                logger.info("WebSocket connection established successfully")
            else:
                logger.info(f"Using existing WebSocket connection: {self.websocket_url}")
                # Check if the connection is still open
                try:
                    # Send a ping to check if the connection is still open
                    self.ws.ping()
                    logger.info("WebSocket connection is active (ping successful)")
                except Exception as e:
                    logger.warning(f"WebSocket connection appears to be closed: {e}")
                    logger.warning("Attempting to reconnect...")
                    if not self._connect_websocket():
                        logger.error("Failed to re-establish WebSocket connection. Suggestions will not be displayed.")
                        return False
                    logger.info("WebSocket connection re-established successfully")
            
            # Log the data being sent
            logger.info(f"Sending data to WebSocket: {json.dumps(data)}")
            
            # Send the data to the WebSocket server
            result = self._send_to_websocket(data)
            logger.info(f"WebSocket send result: {result}")
            
            # Log success or failure
            if result:
                logger.info("Successfully sent suggestions to overlay agent")
            else:
                logger.error("Failed to send suggestions to overlay agent")
                
            logger.info("========== END SENDING SUGGESTIONS ==========\n")
            return result
        except Exception as e:
            logger.error(f"Error sending suggestions: {e}")
            logger.error(traceback.format_exc())
            return False

    def run(self):
        """
        Run the active chat detector
        """
        # Check if we have a valid WebSocket connection
        if not self.test_mode and not self.ws:
            if not self._connect_websocket():
                logger.error("Could not connect to WebSocket server")
                return
        
        try:
            logger.info("Starting Active Chat Detector")
            
            while True:
                # Get the active conversation ID
                conversation_id = self.get_active_conversation_id()
                
                # If we have a conversation ID and it's different from the last one
                if conversation_id and conversation_id != self.last_conversation_id:
                    logger.info("")
                    logger.info("*" * 50)
                    logger.info(f"ACTIVE CONVERSATION CHANGED TO: {conversation_id}")
                    logger.info("*" * 50)
                    logger.info("")
                    self.last_conversation_id = conversation_id
                    
                    # Get the chat info
                    chat_id = self.get_chat_info(conversation_id)
                    if not chat_id:
                        logger.warning("Could not get chat info")
                        time.sleep(self.check_interval)
                        continue
                    
                    # Get recent messages
                    messages = self.get_recent_messages(chat_id)
                    if not messages:
                        logger.warning("Could not get recent messages")
                        time.sleep(self.check_interval)
                        continue
                    
                    # Format conversation
                    context = self.format_conversation(messages)
                    logger.info("Conversation context:")
                    for line in context.split('\n'):
                        logger.info(f"  {line}")
                    
                    # Generate suggestions
                    suggestions = self.generate_suggestions(context)
                    if suggestions:
                        logger.info("Generated suggestions:")
                        for i, suggestion in enumerate(suggestions):
                            logger.info(f"  {i+1}. {suggestion}")
                        
                        # Send suggestions to overlay agent
                        self.send_suggestions(suggestions)
                
                # Sleep for a bit
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Stopping Active Chat Detector")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Clean up WebSocket connection
            if self.ws:
                try:
                    self.ws.close()
                    logger.info("Closed WebSocket connection")
                except:
                    pass

def main():
    parser = argparse.ArgumentParser(description='Active Chat Detector for Alexis AI')
    parser.add_argument('--interval', type=float, default=1.0, help='Check interval in seconds')
    parser.add_argument('--websocket', type=str, help='WebSocket URL to send suggestions to')
    parser.add_argument('--user-id', type=str, help='User ID for message suggestions')
    parser.add_argument('--max-messages', type=int, default=10, help='Maximum number of messages to retrieve')
    parser.add_argument('--test', action='store_true', help='Run in test mode (don\'t send to WebSocket)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create and run the detector
    detector = ActiveChatDetector(
        check_interval=args.interval,
        websocket_url=args.websocket,
        user_id=args.user_id,
        max_messages=args.max_messages,
        test_mode=args.test
    )
    detector.run()

if __name__ == '__main__':
    main()
