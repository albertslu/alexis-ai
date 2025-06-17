#!/usr/bin/env python3
"""
Routes for controlling the Active Chat Detector script
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

# Create blueprint
active_chat_detector_bp = Blueprint('active_chat_detector', __name__)

# Path to the project root
PROJECT_ROOT = Path(__file__).parent.parent

# Path to store the PID of the running script
PID_FILE = PROJECT_ROOT / "data" / "active_chat_detector_pid.txt"

# Path to store the script output
OUTPUT_LOG_FILE = PROJECT_ROOT / "data" / "active_chat_detector_output.log"

# Import authentication decorator
from utils.auth import token_required

@active_chat_detector_bp.route('/active-chat-detector/start', methods=['POST'])
@token_required
def start_detector():
    """Start the Active Chat Detector script with user-specific configuration"""
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
                    "message": "Active Chat Detector is already running"
                })
            except OSError:
                # Process is not running, remove the PID file
                os.remove(PID_FILE)
                print("Removed stale PID file")
        
        # Get configuration from request
        config = request.json or {}
        websocket_url = config.get('websocket_url')
        
        if not websocket_url:
            return jsonify({
                "status": "error",
                "message": "WebSocket URL is required"
            }), 400
        
        # Start the script
        script_path = PROJECT_ROOT / "scripts" / "active_chat_detector.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--websocket", websocket_url,
            "--interval", "1.0"
        ]
        
        # Get user ID from Flask's g object (set by token_required decorator)
        if hasattr(g, 'user_id') and g.user_id:
            user_id = g.user_id
            cmd.extend(["--user-id", user_id])
            print(f"Starting Active Chat Detector with user ID: {user_id}")
        else:
            print("Warning: No user_id found in Flask context")
        
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
        print(f"Started Active Chat Detector with PID: {process.pid}")
        output_log.write(f"Started Active Chat Detector with PID: {process.pid}\n")
        output_log.flush()
        
        # Save PID
        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))
        
        return jsonify({
            "status": "running",
            "pid": process.pid,
            "message": "Active Chat Detector started successfully"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error"}), 500

@active_chat_detector_bp.route('/active-chat-detector/stop', methods=['POST'])
@token_required
def stop_detector():
    """Stop the Active Chat Detector script"""
    try:
        # Check if the script is running
        if not PID_FILE.exists():
            return jsonify({
                "status": "not_running",
                "message": "Active Chat Detector is not running"
            })
        
        # Get the PID
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Try to terminate the process
        try:
            print(f"Sending SIGTERM to process {pid}")
            os.kill(pid, signal.SIGTERM)
            
            # Wait for the process to terminate
            max_wait = 3  # seconds
            for _ in range(max_wait * 10):  # Check every 0.1 seconds
                try:
                    # Check if process still exists
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except OSError:
                    # Process has terminated
                    break
            else:
                # Process didn't terminate, try SIGKILL
                print(f"Process {pid} didn't terminate with SIGTERM, using SIGKILL")
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
            
            # Check if process still exists after SIGKILL
            try:
                os.kill(pid, 0)
                print(f"WARNING: Process {pid} still exists after SIGKILL!")
            except OSError:
                # Process has terminated
                pass
            
            # Remove the PID file
            os.remove(PID_FILE)
            
            return jsonify({
                "status": "stopped",
                "message": "Active Chat Detector stopped successfully"
            })
        except OSError as e:
            # Process doesn't exist
            os.remove(PID_FILE)
            return jsonify({
                "status": "not_running",
                "message": f"Active Chat Detector process {pid} not found: {e}"
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error"}), 500

@active_chat_detector_bp.route('/active-chat-detector/status', methods=['GET'])
@token_required
def get_status():
    """Get the status of the Active Chat Detector script"""
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
        
        return jsonify({
            "status": "running" if is_running else "stopped",
            "pid": pid
        })
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500
