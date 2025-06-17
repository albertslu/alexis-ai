"""
Gmail listener routes for the AI Clone backend.
Handles starting/stopping the email auto-response script and managing email responses.
"""

from flask import Blueprint, request, jsonify
import os
import sys
import json
import subprocess
import signal
import time
from datetime import datetime
import threading

# Create blueprint
gmail_listener_bp = Blueprint('gmail_listener', __name__)

# Global variables to track the listener process
gmail_listener_process = None
gmail_listener_config = {
    'check_interval': 60,
    'auto_respond': False,
    'confidence_threshold': 0.7,
    'max_emails_per_check': 10,
    'filter_rules': {
        'ignore_noreply': True,
        'ignore_subscriptions': True,
        'allowed_senders': []
    }
}
gmail_listener_status = 'stopped'
gmail_listener_pid = None
has_credentials = False

# Directory for pending email responses
PENDING_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pending_responses')
os.makedirs(PENDING_DIR, exist_ok=True)

# Path to the email auto-response script
EMAIL_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'email_auto_response.py')

# Path to credentials file
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'credentials.json')

# Path to token file
TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'token.json')

# Log file path
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs', 'gmail_listener.log')
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# Function to check if credentials exist
def check_credentials():
    global has_credentials
    has_credentials = os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 0
    return has_credentials

# Function to get the current status
def get_status():
    global gmail_listener_process, gmail_listener_status, gmail_listener_pid, gmail_listener_config
    
    # Check if the process is still running
    if gmail_listener_process and gmail_listener_process.poll() is None:
        gmail_listener_status = 'running'
    else:
        gmail_listener_status = 'stopped'
        gmail_listener_pid = None
    
    # Check credentials
    check_credentials()
    
    return {
        'status': gmail_listener_status,
        'pid': gmail_listener_pid,
        'config': gmail_listener_config,
        'has_credentials': has_credentials
    }

# Function to start the Gmail listener
def start_listener(config):
    global gmail_listener_process, gmail_listener_status, gmail_listener_pid, gmail_listener_config
    
    # Update config
    gmail_listener_config.update(config)
    
    # Check if credentials exist
    if not check_credentials():
        return {
            'error': 'Gmail API credentials not found. Please upload credentials first.'
        }
    
    # Check if already running
    if gmail_listener_process and gmail_listener_process.poll() is None:
        return {
            'error': 'Gmail listener is already running'
        }
    
    try:
        # Prepare command
        cmd = [
            sys.executable,
            EMAIL_SCRIPT_PATH,
            '--mode=monitor',
            f'--interval={config["check_interval"]}',
            f'--max_emails={config["max_emails_per_check"]}'
        ]
        
        if config['auto_respond']:
            cmd.append('--auto_respond')
        
        # Start the process
        with open(LOG_PATH, 'a') as log_file:
            gmail_listener_process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            )
        
        # Update status
        gmail_listener_status = 'running'
        gmail_listener_pid = gmail_listener_process.pid
        
        return get_status()
    
    except Exception as e:
        return {
            'error': f'Failed to start Gmail listener: {str(e)}'
        }

# Function to stop the Gmail listener
def stop_listener():
    global gmail_listener_process, gmail_listener_status, gmail_listener_pid
    
    # Check if running
    if not gmail_listener_process or gmail_listener_process.poll() is not None:
        gmail_listener_status = 'stopped'
        gmail_listener_pid = None
        return get_status()
    
    try:
        # Try to terminate gracefully
        gmail_listener_process.terminate()
        
        # Wait for process to terminate
        for _ in range(5):
            if gmail_listener_process.poll() is not None:
                break
            time.sleep(1)
        
        # Force kill if still running
        if gmail_listener_process.poll() is None:
            if sys.platform == 'win32':
                os.kill(gmail_listener_pid, signal.CTRL_C_EVENT)
            else:
                os.kill(gmail_listener_pid, signal.SIGKILL)
        
        # Update status
        gmail_listener_status = 'stopped'
        gmail_listener_pid = None
        
        return get_status()
    
    except Exception as e:
        return {
            'error': f'Failed to stop Gmail listener: {str(e)}'
        }

# Routes

@gmail_listener_bp.route('/gmail-listener/status', methods=['GET'])
def get_gmail_listener_status():
    """Get the current status of the Gmail listener"""
    return jsonify(get_status())

@gmail_listener_bp.route('/gmail-listener/start', methods=['POST'])
def start_gmail_listener():
    """Start the Gmail listener with the provided configuration"""
    config = request.json
    result = start_listener(config)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)

@gmail_listener_bp.route('/gmail-listener/stop', methods=['POST'])
def stop_gmail_listener():
    """Stop the Gmail listener"""
    result = stop_listener()
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)

@gmail_listener_bp.route('/gmail-listener/config', methods=['POST'])
def update_gmail_listener_config():
    """Update the Gmail listener configuration"""
    global gmail_listener_config
    
    config = request.json
    gmail_listener_config.update(config)
    
    return jsonify(get_status())

@gmail_listener_bp.route('/gmail-listener/credentials', methods=['POST'])
def upload_credentials():
    """Upload Gmail API credentials"""
    if 'credentials' not in request.files:
        return jsonify({'error': 'No credentials file provided'}), 400
    
    credentials_file = request.files['credentials']
    
    if credentials_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Save credentials file
        credentials_file.save(CREDENTIALS_PATH)
        
        # Update status
        check_credentials()
        
        return jsonify(get_status())
    
    except Exception as e:
        return jsonify({'error': f'Failed to upload credentials: {str(e)}'}), 500

@gmail_listener_bp.route('/gmail-listener/log', methods=['GET'])
def get_log():
    """Get the Gmail listener log"""
    try:
        if not os.path.exists(LOG_PATH):
            return jsonify({'log': 'No log file found'})
        
        with open(LOG_PATH, 'r') as log_file:
            # Get the last 100 lines of the log
            lines = log_file.readlines()[-100:]
            log_content = ''.join(lines)
        
        return jsonify({'log': log_content})
    
    except Exception as e:
        return jsonify({'error': f'Failed to read log file: {str(e)}'}), 500

@gmail_listener_bp.route('/gmail-listener/pending', methods=['GET'])
def get_pending_responses():
    """Get pending email responses"""
    try:
        if not os.path.exists(PENDING_DIR):
            return jsonify({'pending': []})
        
        pending_responses = []
        
        for filename in os.listdir(PENDING_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(PENDING_DIR, filename)
                
                with open(file_path, 'r') as f:
                    response_data = json.load(f)
                
                # Add the filename (email ID) to the response data
                response_data['id'] = filename.replace('.json', '')
                
                pending_responses.append(response_data)
        
        return jsonify({'pending': pending_responses})
    
    except Exception as e:
        return jsonify({'error': f'Failed to get pending responses: {str(e)}'}), 500

@gmail_listener_bp.route('/gmail-listener/approve', methods=['POST'])
def approve_response():
    """Approve and send a pending email response"""
    try:
        data = request.json
        email_id = data.get('email_id')
        
        if not email_id:
            return jsonify({'error': 'No email ID provided'}), 400
        
        # Check if the response exists
        response_file = os.path.join(PENDING_DIR, f"{email_id}.json")
        
        if not os.path.exists(response_file):
            return jsonify({'error': 'Response not found'}), 404
        
        # Run the email_auto_response.py script with the approve mode
        cmd = [
            sys.executable,
            EMAIL_SCRIPT_PATH,
            '--mode=approve',
            f'--email_id={email_id}'
        ]
        
        subprocess.run(cmd, check=True)
        
        return jsonify({'success': True, 'message': 'Response approved and sent'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to approve response: {str(e)}'}), 500

@gmail_listener_bp.route('/gmail-listener/reject', methods=['POST'])
def reject_response():
    """Reject a pending email response"""
    try:
        data = request.json
        email_id = data.get('email_id')
        
        if not email_id:
            return jsonify({'error': 'No email ID provided'}), 400
        
        # Check if the response exists
        response_file = os.path.join(PENDING_DIR, f"{email_id}.json")
        
        if not os.path.exists(response_file):
            return jsonify({'error': 'Response not found'}), 404
        
        # Delete the response file
        os.remove(response_file)
        
        return jsonify({'success': True, 'message': 'Response rejected'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to reject response: {str(e)}'}), 500

@gmail_listener_bp.route('/gmail-listener/terminal-output', methods=['GET'])
def get_gmail_terminal_output():
    """Get the Gmail listener terminal output"""
    try:
        if not os.path.exists(LOG_PATH):
            return jsonify({'output': 'No log file found'})
        
        with open(LOG_PATH, 'r') as log_file:
            # Get the last 100 lines of the log
            lines = log_file.readlines()[-100:]
            log_content = ''.join(lines)
        
        return jsonify({'output': log_content})
    
    except Exception as e:
        return jsonify({'error': f'Failed to read log file: {str(e)}'}), 500
