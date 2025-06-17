#!/usr/bin/env python3
"""
Routes for controlling the Mac Message Listener script
"""

import os
import sys
import json
import subprocess
import signal
import time
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, g

# Global variable to track when the listener was started
LISTENER_START_TIME = None

def get_listener_start_time():
    """Get the time when the listener was started"""
    global LISTENER_START_TIME
    return LISTENER_START_TIME

def is_user_number(phone_number):
    """Check if the phone number belongs to the user
    
    Args:
        phone_number: The phone number to check
        
    Returns:
        bool: True if the phone number belongs to the user, False otherwise
    """
    # Get the user's phone number from the environment variables
    user_number = os.environ.get('USER_PHONE_NUMBER', '')
    
    # Clean up both numbers for comparison (remove +, spaces, etc.)
    if phone_number:
        clean_phone = ''.join(c for c in phone_number if c.isdigit())
        clean_user = ''.join(c for c in user_number if c.isdigit())
        
        # Check if the phone number matches the user's number
        return clean_phone and clean_user and clean_phone == clean_user
    
    return False

# Create blueprint
mac_listener_bp = Blueprint('mac_listener', __name__)

# Path to the project root
PROJECT_ROOT = Path(__file__).parent.parent

# Path to store the PID of the running script
PID_FILE = PROJECT_ROOT / "data" / "mac_listener_pid.txt"

# Path to store the script output
OUTPUT_LOG_FILE = PROJECT_ROOT / "data" / "mac_listener_output.log"

# Import user-specific configuration manager
from utils.imessage_config import (
    get_current_user_imessage_config,
    update_current_user_imessage_config,
    DEFAULT_CONFIG
)

# Import authentication decorator
from utils.auth import token_required


@mac_listener_bp.route('/auto-response/status', methods=['GET'])
def get_auto_response_status():
    """Get the status of the auto-response system (for backward compatibility)"""
    try:
        # Check if the Mac Message Listener is running
        is_running = False
        pid = None
        
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if the process is still running
            try:
                os.kill(pid, 0)  # Signal 0 doesn't kill the process, just checks if it exists
                is_running = True
            except OSError:
                # Process is not running
                is_running = False
        
        return jsonify({
            "active": is_running,
            "schedule": {
                "active": is_running,
                "channels": {
                    "text": True,
                    "email": True
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
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mac_listener_bp.route('/mac-listener/status', methods=['GET'])
@token_required
def get_status():
    """Get the status of the Mac Message Listener script with user-specific configuration"""
    try:
        # Check if the script is running
        is_running = False
        pid = None
        
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if the process is still running
            try:
                os.kill(pid, 0)  # Signal 0 doesn't kill the process, just checks if it exists
                is_running = True
            except OSError:
                # Process is not running
                is_running = False
                
        # Get user-specific configuration from MongoDB
        config = get_current_user_imessage_config()
        
        return jsonify({
            "status": "running" if is_running else "stopped",
            "pid": pid,
            "config": config
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mac_listener_bp.route('/mac-listener/start', methods=['POST'])
@token_required
def start_listener():
    """Start the Mac Message Listener script with user-specific configuration"""
    global LISTENER_START_TIME
    try:
        # Check if the script is already running
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            try:
                os.kill(pid, 0)
                return jsonify({
                    "status": "already_running",
                    "pid": pid,
                    "message": "Mac Message Listener is already running"
                })
            except OSError:
                # Process is not running, remove the PID file
                os.remove(PID_FILE)
                print("Removed stale PID file")
        
        # Get user-specific configuration from MongoDB
        config = get_current_user_imessage_config()
        
        # Update configuration from request
        if request.json:
            # Handle allowed_numbers specially
            if "allowed_numbers" in request.json and request.json["allowed_numbers"]:
                allowed_numbers = request.json["allowed_numbers"]
                
                # Normalize phone numbers
                normalized_numbers = []
                for num in allowed_numbers:
                    # Remove all non-digit characters
                    digits_only = ''.join(c for c in num if c.isdigit())
                    
                    # If it's a 10-digit US number without country code, add +1
                    if len(digits_only) == 10:
                        normalized_numbers.append(digits_only)
                    else:
                        normalized_numbers.append(digits_only)
                
                # Update the request data with normalized numbers
                request.json["allowed_numbers"] = normalized_numbers
                print(f"Normalized allowed numbers: {normalized_numbers}")
            
            # Update user-specific configuration in MongoDB
            config = update_current_user_imessage_config(request.json)
        
        # Start the script
        script_path = PROJECT_ROOT / "scripts" / "mac_message_listener.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--interval", str(config["check_interval"]),
        ]
        
        if not config["auto_respond"]:
            cmd.append("--no-auto-respond")
        
        if config["allowed_numbers"]:
            cmd.extend(["--allowed-numbers"] + config["allowed_numbers"])
            print(f"Starting Mac listener with allowed numbers: {config['allowed_numbers']}")
            
        # Get the current user ID from Flask g object
        if hasattr(g, 'user_id') and g.user_id:
            user_id = g.user_id
            cmd.extend(["--user-id", user_id])
            print(f"Starting Mac listener with user ID: {user_id}")
        else:
            print("Warning: No user ID available, Mac listener will use default model")
        
        # Add visual mode if enabled
        if config.get("visual_mode", False):
            cmd.append("--visual")
            print("Starting Mac listener in visual mode")
        
        # Open the output log file
        output_log = open(OUTPUT_LOG_FILE, 'w')
        
        # Log the command being executed
        print(f"Executing command: {' '.join(cmd)}")
        output_log.write(f"Executing command: {' '.join(cmd)}\n")
        output_log.flush()
        
        # Start the process and redirect output to the log file
        # Use the same environment as the current process
        process = subprocess.Popen(
            cmd, 
            stdout=output_log, 
            stderr=output_log,
            env=os.environ.copy()  # Use the same environment variables
        )
        
        # Log the process ID
        print(f"Started Mac message listener with PID: {process.pid}")
        output_log.write(f"Started Mac message listener with PID: {process.pid}\n")
        output_log.flush()
        
        # Save PID
        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))
            
        # Set the listener start time
        LISTENER_START_TIME = datetime.now()
        
        return jsonify({
            "status": "running",
            "pid": process.pid,
            "config": config,
            "message": "Mac Message Listener started successfully"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error"}), 500


@mac_listener_bp.route('/mac-listener/stop', methods=['POST'])
@token_required
def stop_listener():
    """Stop the Mac Message Listener script"""
    global LISTENER_START_TIME
    try:
        if not PID_FILE.exists():
            return jsonify({
                "status": "not_running",
                "message": "Mac Message Listener is not running"
            })
        
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        try:
            # Check if process exists before trying to kill it
            try:
                # Send signal 0 to check if process exists without affecting it
                os.kill(pid, 0)
                process_exists = True
            except ProcessLookupError:
                process_exists = False
            
            if process_exists:
                print(f"Sending SIGTERM to process {pid}")
                # First try SIGTERM for graceful shutdown
                os.kill(pid, signal.SIGTERM)
                
                # Wait for up to 3 seconds for process to terminate
                max_wait = 3
                for _ in range(max_wait * 10):  # Check 10 times per second
                    try:
                        # Check if process still exists
                        os.kill(pid, 0)
                        # Process still exists, wait a bit
                        time.sleep(0.1)
                    except ProcessLookupError:
                        # Process is gone
                        print(f"Process {pid} terminated successfully with SIGTERM")
                        break
                else:
                    # Process didn't terminate after max_wait seconds, use SIGKILL
                    print(f"Process {pid} didn't terminate with SIGTERM, using SIGKILL")
                    try:
                        os.kill(pid, signal.SIGKILL)
                        print(f"Sent SIGKILL to process {pid}")
                    except ProcessLookupError:
                        # Process terminated between last check and SIGKILL
                        pass
                
                # Final verification
                try:
                    os.kill(pid, 0)
                    print(f"WARNING: Process {pid} still exists after SIGKILL!")
                except ProcessLookupError:
                    print(f"Verified process {pid} is terminated")
            else:
                print(f"Process with PID {pid} not found")
            
            # Clean up PID file regardless
            if PID_FILE.exists():
                os.remove(PID_FILE)
            
            # Reset the listener start time
            LISTENER_START_TIME = None
            
            return jsonify({
                "status": "stopped",
                "message": "Mac Message Listener stopped successfully"
            })
        except ProcessLookupError:
            # Process doesn't exist
            print(f"Process with PID {pid} not found")
            if PID_FILE.exists():
                os.remove(PID_FILE)
            
            # Reset the listener start time
            LISTENER_START_TIME = None
            
            return jsonify({
                "status": "not_running",
                "message": f"Mac Message Listener process (PID {pid}) was not running"
            })
        except OSError as e:
            # Other OS errors
            print(f"Error stopping process with PID {pid}: {str(e)}")
            if PID_FILE.exists():
                os.remove(PID_FILE)
            
            # Reset the listener start time
            LISTENER_START_TIME = None
            
            return jsonify({
                "status": "error",
                "message": f"Error stopping Mac Message Listener: {str(e)}"
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error stopping Mac listener: {str(e)}")
        
        return jsonify({
            "error": str(e),
            "status": "error",
            "message": f"Failed to stop Mac Message Listener: {str(e)}"
        }), 500


@mac_listener_bp.route('/mac-listener/config', methods=['POST'])
@token_required
def update_config():
    """Update the Mac Message Listener configuration with user-specific settings"""
    try:
        # Get user-specific configuration from MongoDB
        config = get_current_user_imessage_config()
        
        # Update with request data
        if request.json:
            # Update user-specific configuration in MongoDB
            config = update_current_user_imessage_config(request.json)
        
        # Check if the script is running
        is_running = False
        pid = None
        
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            try:
                os.kill(pid, 0)
                is_running = True
            except OSError:
                is_running = False
        
        return jsonify({
            "status": "running" if is_running else "stopped",
            "pid": pid,
            "config": config,
            "message": "Configuration updated successfully"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mac_listener_bp.route('/mac-listener/log', methods=['GET'])
def get_message_log():
    """Get recent messages from the chat history"""
    try:
        # Path to chat history file
        chat_history_path = PROJECT_ROOT / "data" / "chat_history.json"
        
        if not chat_history_path.exists():
            return jsonify({"messages": []})
        
        # Get the listener start time from the global variable
        listener_start_time = get_listener_start_time()
        
        with open(chat_history_path, 'r') as f:
            chat_history = json.load(f)
        
        # Extract messages from chat history
        messages = []
        if (isinstance(chat_history, dict) and 
            "conversations" in chat_history and 
            len(chat_history["conversations"]) > 0 and
            "messages" in chat_history["conversations"][0]):
            
            # Get all messages
            all_messages = chat_history["conversations"][0]["messages"]
            
            # Group messages by conversation
            conversation_map = {}
            for msg in all_messages:
                if msg.get("channel") != "imessage":
                    continue
                    
                # Create a timestamp for sorting
                timestamp_str = msg.get("timestamp", "")
                
                # Skip messages that don't have a timestamp
                if not timestamp_str:
                    continue
                
                # Parse the timestamp
                try:
                    # Remove the Z suffix if present
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1]
                    
                    # Parse the timestamp
                    msg_timestamp = datetime.fromisoformat(timestamp_str)
                    
                    # Skip messages that were created before the listener started
                    if listener_start_time and msg_timestamp < listener_start_time:
                        continue
                except (ValueError, TypeError):
                    # If we can't parse the timestamp, include the message anyway
                    pass
                
                # Create a conversation ID based on sender
                sender = msg.get("sender", "unknown")
                
                if sender not in conversation_map:
                    conversation_map[sender] = []
                
                conversation_map[sender].append({
                    "sender": sender,
                    "text": msg.get("text", ""),
                    "timestamp": timestamp_str,
                    "id": msg.get("id", "")  # Store the message ID to reference the original message
                })
            
            # Process conversations to show all messages, including standalone ones
            for sender, msgs in conversation_map.items():
                # Sort by timestamp
                msgs.sort(key=lambda x: x.get("timestamp", ""))
                
                # Process messages in pairs when possible (user message followed by clone response)
                i = 0
                while i < len(msgs):
                    # Look for the original message to get the contact info
                    contact_info = None
                    for msg in all_messages:
                        if msg.get("id") == msgs[i].get("id"):
                            # If we found the original message, use the contact_id if available
                            contact_info = msg.get("contact_id")
                            break
                    
                    # Format the contact display name
                    display_name = "Contact"
                    
                    # Check if the sender is a phone number (from someone else)
                    if msgs[i]["sender"].startswith("+") or msgs[i]["sender"].isdigit():
                        # It's a message from someone else, use their number as display name
                        display_name = msgs[i]["sender"]
                    elif msgs[i]["sender"] == "user":
                        # For backward compatibility with old messages
                        if contact_info and not is_user_number(contact_info):
                            # If it's a message from someone else, use their number
                            display_name = contact_info
                        else:
                            # If it's from the user, show "You"
                            display_name = "You"
                    elif msgs[i]["sender"] == "clone":
                        display_name = "AI Clone"
                    
                    if i < len(msgs) - 1 and msgs[i]["sender"] == "user" and msgs[i+1]["sender"] == "clone":
                        # Found a pair
                        messages.append({
                            "from": display_name,
                            "text": msgs[i].get("text", ""),
                            "response": msgs[i+1].get("text", ""),
                            "timestamp": msgs[i].get("timestamp", "")
                        })
                        i += 2  # Skip both messages
                    else:
                        # Standalone message
                        messages.append({
                            "from": display_name,
                            "text": msgs[i].get("text", ""),
                            "response": None,  # No response for standalone messages
                            "timestamp": msgs[i].get("timestamp", "")
                        })
                        i += 1  # Move to next message
            
            # Sort by timestamp (newest first) and limit to 20
            messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            messages = messages[:20]
        
        return jsonify({"messages": messages})
    except Exception as e:
        return jsonify({"error": str(e), "messages": []}), 500


@mac_listener_bp.route('/mac-listener/terminal-output', methods=['GET'])
def get_terminal_output():
    """Get the terminal output from the Mac Message Listener script"""
    try:
        if not OUTPUT_LOG_FILE.exists():
            return jsonify({"output": "", "status": "no_log_file"})
        
        # Read the last 50 lines from the log file
        max_lines = request.args.get('max_lines', 50, type=int)
        
        with open(OUTPUT_LOG_FILE, 'r') as f:
            # Read all lines and get the last max_lines
            lines = f.readlines()
            if len(lines) > max_lines:
                lines = lines[-max_lines:]
            
            output = ''.join(lines)
        
        # Check if the script is running
        is_running = False
        pid = None
        
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            try:
                os.kill(pid, 0)
                is_running = True
            except OSError:
                is_running = False
        
        return jsonify({
            "output": output,
            "status": "running" if is_running else "stopped",
            "pid": pid
        })
    except Exception as e:
        return jsonify({"error": str(e), "output": ""}), 500
