from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import sys
import json
import uuid
import time
import random
import logging
import datetime
from datetime import datetime as dt, timedelta
import threading
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from threading import Thread
from pymongo import MongoClient
import re

# Import RAG system
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.rag_system import MessageRAG
from rag.api_routes import rag_bp
from rag.simple_repository import SimpleDataRepository
from rag.data_integration import DataIntegration
from rag.enhanced_rag_integration import initialize_enhanced_rag, enhance_prompt_with_rag
from rag.rag_storage import add_interaction_to_rag
from rag.personal_info_routes import personal_info_bp
from utils.hybrid_response import HybridResponseGenerator
from utils.feedback_system import FeedbackSystem
from routes.feedback_routes import feedback_bp
from utils.auth_routes import auth_bp
from utils.auth import token_required, get_current_user_id
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from routes.mac_listener_routes import mac_listener_bp
from routes.gmail_listener_routes import gmail_listener_bp
from routes.active_chat_detector_routes import active_chat_detector_bp
from utils.message_listener import MessageListenerService, get_message_listener_service, message_listener_bp

# Try to import optional integrations
try:
    from utils.twilio_integration import TwilioIntegration, twilio_bp
    twilio_available = True
except ImportError:
    print("Twilio package not installed. Text message integration will be disabled.")
    twilio_available = False

try:
    from utils.email_integration import EmailIntegration, email_bp
    email_available = True
except ImportError:
    print("Google API packages not installed. Email integration will be disabled.")
    email_available = False
    
try:
    from utils.oauth_handler import oauth_bp
    oauth_available = True
except ImportError:
    print("OAuth handler not available. OAuth flows will be disabled.")
    oauth_available = False

# Load environment variables
load_dotenv()

# Default model configuration (simplified)
DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"
FINE_TUNED_MODEL = "gpt-4o-mini-2024-07-18"

def get_current_model():
    """Get the current model - simplified version without MongoDB dependency"""
    # For now, just return the default model
    # In production, this could check user-specific model IDs
    return DEFAULT_MODEL

# Initialize OpenAI client
# Don't set global variable from environment
# AI_MODEL = os.getenv('AI_MODEL', FINE_TUNED_MODEL)

# Configure OpenAI client - using the latest version of the library
# Create a completely clean client with minimal parameters
import httpx

# Create a custom HTTP client without proxies
http_client = httpx.Client()

# Initialize the OpenAI client with only the required parameters
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    http_client=http_client
)

# Default to gpt-4o-mini for both training and fine-tuning
DEFAULT_TRAINING_MODEL = 'gpt-4o-mini-2024-07-18'  # Cheaper and faster for training

app = Flask(__name__)

# Set the secret key for session management
app.secret_key = os.getenv('JWT_SECRET', 'dev-secret-key')

# Configure CORS more explicitly
CORS(app, resources={r"/*": {
    "origins": ["http://localhost:3000", "*"],  # Allow both localhost:3000 and any other origin
    "methods": ["GET", "POST", "OPTIONS"], 
    "allow_headers": ["Content-Type", "Authorization", "Content-Length", "X-Requested-With"], 
    "supports_credentials": True
}})

# Add CORS headers to all responses
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    if origin:
        response.headers.add('Access-Control-Allow-Origin', origin)
    else:
        response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Content-Length,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Handle OPTIONS requests for CORS preflight
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return '', 200

# Serve static files for downloads
@app.route('/downloads/<path:filename>')
def download_file(filename):
    downloads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'downloads')
    return app.send_from_directory(downloads_dir, filename, as_attachment=True)

# Initialize training data path - ensure it's consistent with other parts of the app
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
TRAINING_DATA_PATH = os.path.join(DATA_DIR, 'training_data.json')

def check_for_completed_finetunes_on_startup():
    """
    Check for completed fine-tuning jobs on startup to ensure 
    the backend is aware of them even after restarts.
    """
    print("Checking for completed fine-tuning jobs on startup...")
    
    try:
        # Ensure the training data file exists
        if not os.path.exists(TRAINING_DATA_PATH):
            print(f"Training data file not found at {TRAINING_DATA_PATH}, creating default")
            # Create default training data
            training_data = {
                'trained': False,  # Default to not trained for new users
                'fine_tuning_in_progress': False,
                'model_id': None,
                'current_session_messages': 0,
                'total_messages': 0
            }
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(TRAINING_DATA_PATH), exist_ok=True)
            # Save default training data
            with open(TRAINING_DATA_PATH, 'w') as f:
                json.dump(training_data, f, indent=2)
            print(f"Created new training data file at {TRAINING_DATA_PATH}")
            
        # Load existing training data
        with open(TRAINING_DATA_PATH, 'r') as f:
            training_data = json.load(f)
        
        # Check if there's an active fine-tuning job in local data
        job_id = training_data.get('fine_tuning_job_id')
        
        # If we have a local job ID and not already marked as trained, verify its status
        if job_id and not training_data.get('trained', False):
            print(f"Found fine-tuning job {job_id}, checking status with OpenAI...")
            try:
                # Get the status of the fine-tuning job
                response = client.fine_tuning.jobs.retrieve(job_id)
                status = response.status
                
                print(f"Fine-tuning job status: {status}")
                
                if status == 'succeeded':
                    # Fine-tuning completed successfully
                    fine_tuned_model = response.fine_tuned_model
                    training_data['trained'] = True
                    training_data['fine_tuning_in_progress'] = False
                    
                    # Store fine-tuned model ID in training data
                    training_data['model_id'] = fine_tuned_model
                    training_data['trained'] = True

                    # Don't update environment as it won't persist across app restarts
                    # os.environ['AI_MODEL'] = fine_tuned_model
                    # print(f"Updated AI_MODEL environment variable to {fine_tuned_model}")
                    
                    # Update the user's MongoDB record with the training status
                    user_id = g.user_id if hasattr(g, 'user_id') and g.user_id else None
                    if user_id:
                        try:
                            # Import the MongoDB connection from auth
                            from utils.auth import db
                            
                            # Update the MongoDB record to reflect training completion
                            update_result = db.users.update_one(
                                {"user_id": user_id},
                                {"$set": {
                                    "model_trained": True,
                                    "has_fine_tuned_model": True,
                                    "fine_tuned_model_id": fine_tuned_model,
                                    "model_last_updated": dt.now().isoformat()
                                }}
                            )
                            
                            if update_result.modified_count > 0:
                                print(f"Updated MongoDB record for user {user_id} to reflect training completion")
                            else:
                                print(f"Warning: MongoDB update for user {user_id} training status did not modify any records")
                        except Exception as e:
                            print(f"Error updating MongoDB with training status: {e}")
                    
                    # Now update the user-specific model config
                    user_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'user_configs')
                    user_model_config_path = os.path.join(user_config_dir, f'{user_id}_model_config.json')
                    
                    try:
                        # Ensure user config directory exists
                        os.makedirs(user_config_dir, exist_ok=True)
                        
                        user_model_config = {}
                        # Load existing config if it exists
                        if os.path.exists(user_model_config_path):
                            with open(user_model_config_path, 'r') as f:
                                user_model_config = json.load(f)
                        
                        # Update with new model info
                        user_model_config['fine_tuned_model'] = fine_tuned_model
                        user_model_config['trained'] = True
                        
                        # Ensure all required fields exist
                        if 'base_model' not in user_model_config:
                            user_model_config['base_model'] = "gpt-4o-mini-2024-07-18"
                        if 'rag_weight' not in user_model_config:
                            user_model_config['rag_weight'] = 0.7
                        if 'temperature' not in user_model_config:
                            user_model_config['temperature'] = 0.6
                        if 'max_tokens' not in user_model_config:
                            user_model_config['max_tokens'] = 300
                        
                        # Save updated config
                        with open(user_model_config_path, 'w') as f:
                            json.dump(user_model_config, f, indent=2)
                        print(f"Updated user model config for {user_id} with new model ID: {fine_tuned_model}")
                    except Exception as e:
                        print(f"Error updating user model config: {e}")
                
                elif status == 'failed':
                    # Fine-tuning failed
                    training_data['fine_tuning_in_progress'] = False
                    training_data['fine_tuning_error'] = "Fine-tuning failed"
                    
                    # Update the training data
                    with open(TRAINING_DATA_PATH, 'w') as f:
                        json.dump(training_data, f, indent=2)
                    
                    print("Updated training data: fine-tuning failed")
                
                elif status in ['validating_files', 'queued', 'running']:
                    # Still in progress
                    training_data['fine_tuning_in_progress'] = True
                    
                    # Update the training data
                    with open(TRAINING_DATA_PATH, 'w') as f:
                        json.dump(training_data, f, indent=2)
                    
                    print(f"Fine-tuning job {job_id} is still in progress, status: {status}")
                    
            except Exception as e:
                print(f"Error checking fine-tuning job status: {e}")
                import traceback
                traceback.print_exc()
        
        elif training_data.get('trained', False):
            model_id = training_data.get('model_id')
            print(f"Model already trained with ID: {model_id}")
            
    except Exception as e:
        print(f"Error checking for completed fine-tunes: {e}")
        import traceback
        traceback.print_exc()

# Call this function on startup
check_for_completed_finetunes_on_startup()

# Register blueprints
app.register_blueprint(rag_bp, url_prefix='/api')
app.register_blueprint(personal_info_bp, url_prefix='/api')
app.register_blueprint(feedback_bp, url_prefix='/api')
app.register_blueprint(auth_bp)
app.register_blueprint(mac_listener_bp, url_prefix='/api')
app.register_blueprint(gmail_listener_bp, url_prefix='/api')
app.register_blueprint(message_listener_bp, url_prefix='/api')
app.register_blueprint(active_chat_detector_bp, url_prefix='/api')
# message_suggestions_bp removed as we're using HybridResponseGenerator directly

# Add endpoint for message suggestions using HybridResponseGenerator
@app.route('/api/message-suggestions', methods=['POST'])
def get_message_suggestions():
    """
    API endpoint to get message suggestions based on conversation context
    using the HybridResponseGenerator for personalized suggestions.
    """
    try:
        print("\n" + "=" * 80)
        print("MESSAGE SUGGESTIONS ENDPOINT CALLED")
        print("=" * 80)
        
        # Get data from request body
        data = request.json or {}
        print(f"Request headers: {dict(request.headers)}")
        print(f"Request data: {data}")
        
        context = data.get('context', '')
        print(f"Context length: {len(context)} characters")
        print(f"Context first 200 chars: {context[:200]}")
        print(f"Context last 200 chars: {context[-200:] if len(context) > 200 else context}")
        
        # Get user ID from request body
        user_id = data.get('user_id')
        print(f"User ID from request body: {user_id}")
        
        # Check if g.user_id exists before request
        if hasattr(g, 'user_id'):
            print(f"g.user_id before setting: {g.user_id}")
        else:
            print("g.user_id not set before request")
        
        # Set user_id in Flask context if provided in the request
        if user_id:
            g.user_id = user_id
            print(f"Set g.user_id to: {user_id} from request body")
        else:
            # Fall back to g.user_id if already set (e.g., by token_required)
            if hasattr(g, 'user_id') and g.user_id:
                user_id = g.user_id
                print(f"Using existing g.user_id: {user_id}")
            else:
                user_id = None  # No default user ID, will be handled by the hybrid generator
                print("WARNING: No user_id provided in request or g object")
            
        print(f"Message suggestions requested for user ID: {user_id}")
        
        if not context:
            return jsonify({
                'success': False,
                'error': 'No conversation context provided',
                'suggestions': []
            }), 400
        
        # Parse conversation history from context
        conversation_history = []
        current_role = None
        current_content = []
        
        for line in context.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Me:'):
                # If we were building a previous message, add it to history
                if current_role and current_content:
                    conversation_history.append({
                        'role': current_role,
                        'content': '\n'.join(current_content)
                    })
                # Start a new user message
                current_role = 'user'
                current_content = [line[3:].strip()]
            elif line.startswith('Other:'):
                # If we were building a previous message, add it to history
                if current_role and current_content:
                    conversation_history.append({
                        'role': current_role,
                        'content': '\n'.join(current_content)
                    })
                # Start a new assistant message
                current_role = 'assistant'
                current_content = [line[6:].strip()]
            else:
                # Continue the current message
                if current_role:
                    current_content.append(line)
        
        # Add the last message if there is one
        if current_role and current_content:
            conversation_history.append({
                'role': current_role,
                'content': '\n'.join(current_content)
            })
        
        # Get the last user message for generating suggestions
        last_user_message = ""
        for msg in reversed(conversation_history):
            if msg['role'] == 'user':
                last_user_message = msg['content']
                break
                
        # Create a system prompt for message suggestions - exactly matching what was used in fine-tuning
        system_prompt = """You draft message suggestions that match the user's writing style, fit the conversation context, and are ready to send without editing."""
        
        # Skip RAG enhancement entirely and use the basic system prompt directly
        enhanced_prompt = system_prompt
        
        print(f"\nSKIPPING RAG ENHANCEMENT:")
        print(f"Using direct fine-tuned model approach without RAG for user_id: {user_id}")
        print(f"System prompt: {system_prompt}")
        print(f"Last user message: {last_user_message[:100]}...")
        print(f"Conversation history length: {len(conversation_history)}")
        
        # Note: We're completely bypassing the RAG enhancement to test if the fine-tuned model
        # performs better without potentially confusing RAG examples
        
        # Continue with message generation regardless of RAG success
        try:
            # Generate suggestions using HybridResponseGenerator with the user's model
            print(f"\nGENERATING SUGGESTIONS:")
            print(f"User ID for model: {user_id}")
            print(f"Conversation history length: {len(conversation_history)}")
            print(f"Using HybridResponseGenerator.generate_response_suggestions")
            
            # Make sure hybrid_generator has the correct user_id
            if hasattr(hybrid_generator, 'user_id') and user_id:
                # Update the user_id in the hybrid_generator instance
                hybrid_generator.user_id = user_id
                print(f"Updated hybrid_generator.user_id to: {user_id}")
            
            # Call generate_response_suggestions without the user_id parameter
            suggestions = hybrid_generator.generate_response_suggestions(
                user_message=last_user_message,
                conversation_history=conversation_history,
                count=3,  # Number of suggestions to generate
                channel='text',  # Use text channel for message suggestions
                system_prompt=enhanced_prompt  # Pass the enhanced prompt
            )
            print(f"Generated {len(suggestions)} suggestions for user ID: {user_id}")
            for i, suggestion in enumerate(suggestions):
                print(f"Suggestion {i+1}: {suggestion[:100]}...")
        except Exception as e:
            error_msg = f"Error generating suggestions with hybrid generator: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f"Error details: {str(e)}",
                'suggestions': []
            }), 500
        
        # Log the final response
        print("\nSENDING RESPONSE:")
        print(f"Success: True")
        print(f"Number of suggestions: {len(suggestions)}")
        print("=" * 80 + "\n")
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        print(f"Error in message suggestions endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f"General endpoint error: {str(e)}",
            'suggestions': []
        }), 500

# Register optional blueprints if available
if twilio_available:
    app.register_blueprint(twilio_bp, url_prefix='/api')
if email_available:
    app.register_blueprint(email_bp, url_prefix='/api')
    
if oauth_available:
    app.register_blueprint(oauth_bp)

# User-specific RAG systems are initialized per-request after authentication.
# No global RAG initialization at startup.
print("Enhanced RAG system configured for lazy initialization (no automatic verification)")

# Cache for storing user-specific RAG systems
user_rag_systems = {}

# User-specific RAG systems will be initialized only when needed

@app.route('/api/test', methods=['GET', 'OPTIONS'])
def test_route():
    if request.method == 'OPTIONS':
        # Preflight request
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    response = jsonify({"message": "API is working!"})
    # No need to add CORS headers here as they'll be added by the after_request handler
    return response

# Initialize Hybrid Response Generator
hybrid_generator = HybridResponseGenerator(skip_rag=True)  # Skip RAG for message suggestions

# Initialize Feedback System
feedback_system = FeedbackSystem()

# Initialize Message Listener Service with the hybrid generator
message_listener_service = get_message_listener_service(
    hybrid_response_generator=hybrid_generator,
    feedback_system=feedback_system
)

# We don't automatically load chat history into the RAG system
# The RAG system should only contain data from external sources like iMessage, LinkedIn, etc.
# Chat history with the clone is stored separately

# Data storage paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
USER_PROFILE_PATH = os.path.join(DATA_DIR, 'user_profile.json')
UNIFIED_REPO_DIR = os.path.join(DATA_DIR, 'unified_repository')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# RAG system is now initialized lazily when needed (no automatic startup verification)

# Initialize data files if they don't exist
if not os.path.exists(TRAINING_DATA_PATH):
    with open(TRAINING_DATA_PATH, 'w') as f:
        json.dump({
            'answers': {},
            'conversations': [],
            'trained': False,
            'last_updated': None
        }, f)

if not os.path.exists(USER_PROFILE_PATH):
    with open(USER_PROFILE_PATH, 'w') as f:
        json.dump({
            'style_characteristics': {},
            'vocabulary': [],
            'emoji_usage': {},
            'common_phrases': [],
            'punctuation_style': {}
        }, f)
        
if not os.path.exists(CHAT_HISTORY_PATH):
    with open(CHAT_HISTORY_PATH, 'w') as f:
        json.dump({
            'conversations': []
        }, f)

@app.route('/api/training-status', methods=['GET'])
def get_training_status():
    """Check if the AI clone has been trained"""
    try:
        # Check if training data file exists
        if not os.path.exists(TRAINING_DATA_PATH):
            print(f"Training data file not found at {TRAINING_DATA_PATH}, creating default")
            # Create default training data
            training_data = {
                'trained': False,  # Default to not trained for new users
                'fine_tuning_in_progress': False,
                'model_id': None,
                'current_session_messages': 0,
                'total_messages': 0
            }
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(TRAINING_DATA_PATH), exist_ok=True)
            # Save default training data
            with open(TRAINING_DATA_PATH, 'w') as f:
                json.dump(training_data, f, indent=2)
        else:
            # Load existing training data
            with open(TRAINING_DATA_PATH, 'r') as f:
                training_data = json.load(f)
        
        # Get the current session message count, default to 0 if not present
        current_session_count = training_data.get('current_session_messages', 0)
        
        # Check MongoDB for user training status if user is authenticated
        if hasattr(g, 'user_id') and g.user_id:
            try:
                # Import auth module which has the proper MongoDB connection
                from utils.auth import db
                
                # Get user from MongoDB
                user = db.users.find_one({"user_id": g.user_id})
                if user:
                    # MongoDB is the definitive source of truth - no fallbacks
                    training_data['trained'] = user.get('model_trained', False)
                    print(f"Using MongoDB training status for user {g.user_id}: {training_data['trained']}")
                else:
                    # No user record found - must be untrained
                    training_data['trained'] = False
                    print(f"No MongoDB record found for user {g.user_id}, setting trained=False")
            except Exception as e:
                # If we can't access MongoDB, fail clearly
                print(f"Error checking MongoDB for user training status: {e}")
                return jsonify({'error': f"Cannot determine training status: {str(e)}"}), 500
        else:
            # If no user is authenticated, ensure trained is False
            training_data['trained'] = False
        
        return jsonify({
            'trained': training_data.get('trained', False),
            'in_progress': training_data.get('fine_tuning_in_progress', False),
            'started_at': training_data.get('fine_tuning_started_at'),
            'last_updated': training_data.get('last_updated'),
            'model_id': training_data.get('model_id'),
            'current_session_messages': current_session_count,
            'messages_needed': max(0, 10 - current_session_count),
            'total_user_messages': 0,  # Default to 0 since count_user_messages is not defined
            'job_id': training_data.get('fine_tuning_job_id'),
            'error': training_data.get('fine_tuning_error')
        })
    except Exception as e:
        print(f"Error in fine-tuning status endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/combine-data-and-retrain', methods=['POST'])
def combine_data_and_retrain(user_id=None):
    """
    Combine data from all sources and retrain the model.
    The user_id parameter allows this function to be called from a background thread
    while still knowing which user to update in MongoDB.
    """
    try:
        # If user_id was not provided (e.g., when called directly as an API endpoint),
        # try to get it from the Flask request context
        if not user_id:
            from flask import g
            user_id = g.user_id if hasattr(g, 'user_id') and g.user_id else None
            
        if not user_id:
            error_msg = "No user ID available for fine-tuning job"
            print(error_msg)
            return jsonify({"success": False, "error": error_msg}), 400
        
        print(f"Starting data combination and retraining for user: {user_id}")
        
        # Initialize email data as empty
        email_data = {}
        email_data_path = None
        
        # Check if email training data exists (optional)
        potential_email_files = [
            os.path.join(DATA_DIR, 'email_training_data.json'),
            os.path.join(DATA_DIR, 'sent_emails.json'),
            os.path.join(DATA_DIR, 'emails.json'),
            os.path.join(DATA_DIR, 'email_data.json')
        ]
        
        # Use the first one that exists
        for potential_file in potential_email_files:
            if os.path.exists(potential_file):
                email_data_path = potential_file
                print(f"Found email data file: {email_data_path}")
                # Load email training data if it exists
                try:
                    with open(email_data_path, 'r') as f:
                        email_data = json.load(f)
                    print(f"Loaded email data from {email_data_path}")
                except Exception as e:
                    print(f"Error loading email data: {e}")
                    email_data = {}
                break
        
        # Email data is now optional, so we continue even if it's not found
        
        # Find the most recent raw iMessage data file
        imessage_files = [f for f in os.listdir(DATA_DIR) if f.startswith('imessage_raw_') and f.endswith('.json')]
        if not imessage_files:
            return jsonify({
                'success': False,
                'message': 'No iMessage data found. Please click "Extract iMessage Data" first to prepare your training data.'
            }), 400
        
        # Sort by timestamp (newest first)
        imessage_files.sort(reverse=True)
        imessage_data_path = os.path.join(DATA_DIR, imessage_files[0])
        print(f"Using most recent iMessage data file: {imessage_data_path}")
        
        # Load raw iMessage data
        with open(imessage_data_path, 'r') as f:
            raw_imessage_data = json.load(f)
        
        # Create a combined training data object
        combined_data = {
            "conversations": [],
            "answers": {},
            "trained": False,
            "last_updated": dt.now().isoformat(),
            "current_session_messages": 0
        }
        
        # Process raw iMessage data into conversations
        imessage_conversations = []
        for contact_data in raw_imessage_data:
            contact = contact_data.get('contact', 'unknown')
            messages = contact_data.get('messages', [])
            
            if messages:
                conversation = {
                    'id': str(uuid.uuid4()),
                    'messages': []
                }
                
                for msg in messages:
                    sender = 'user' if msg.get('is_from_me', False) else contact
                    conversation['messages'].append({
                        'id': str(msg.get('id', uuid.uuid4())),
                        'text': msg.get('text', ''),
                        'sender': sender,
                        'timestamp': msg.get('timestamp', dt.now().isoformat())
                    })
                
                imessage_conversations.append(conversation)
        
        print(f"Processed {len(imessage_conversations)} conversations from raw iMessage data")
        
        # Process email conversations (if any)
        email_conversations = []
        user_email = ''
        
        # Only process email data if it's not empty
        if email_data:
            # Handle different possible structures of email data
            if isinstance(email_data, list):
                # This is the format in email_data.json - a list of email objects with content and metadata
                print(f"Found {len(email_data)} emails in list format")
                
                # Group emails by thread_id to create conversations
                thread_conversations = {}
                
                for email in email_data:
                    # Extract thread ID or create a new one
                    thread_id = email.get('metadata', {}).get('thread_id', str(uuid.uuid4()))
                    
                    if thread_id not in thread_conversations:
                        thread_conversations[thread_id] = {
                            'id': thread_id,
                            'messages': []
                        }
                    
                    # Add this email as a message in the conversation
                    thread_conversations[thread_id]['messages'].append({
                        'id': email.get('metadata', {}).get('message_id', str(uuid.uuid4())),
                        'text': email.get('content', ''),
                        'sender': email.get('metadata', {}).get('sender', 'unknown'),
                        'timestamp': email.get('metadata', {}).get('timestamp', dt.now().isoformat())
                    })
                
                # Convert the thread_conversations dictionary to a list
                email_conversations = list(thread_conversations.values())
                print(f"Created {len(email_conversations)} email conversations from threads")
                
            elif 'conversations' in email_data:
                email_conversations = email_data.get('conversations', [])
                print(f"Found {len(email_conversations)} email conversations in 'conversations' format")
            elif 'emails' in email_data:
                # Convert emails format to conversations format if needed
                for email in email_data.get('emails', []):
                    conversation = {
                        'id': email.get('id', str(uuid.uuid4())),
                        'messages': [
                            {
                                'id': str(uuid.uuid4()),
                                'text': email.get('text', ''),
                                'sender': email.get('sender', 'unknown'),
                                'timestamp': email.get('timestamp', dt.now().isoformat())
                            }
                        ]
                    }
                    email_conversations.append(conversation)
                print(f"Converted {len(email_conversations)} emails to conversation format")
            
            # Extract user email from the training data if available
            user_email = email_data.get('user_email', '').lower()
            print(f"Using user email: {user_email if user_email else 'Not found in training data'}")
        else:
            print("No email data found or loaded - continuing with only iMessage data")
        
        # Combine the conversations
        existing_conversations = combined_data.get('conversations', [])
        print(f"Using {len(existing_conversations)} existing conversations")
        print(f"Adding {len(imessage_conversations)} iMessage conversations")
        print(f"Adding {len(email_conversations)} email conversations")
        combined_data['conversations'] = existing_conversations + imessage_conversations + email_conversations
        
        # Add flags to indicate what data is included
        combined_data['email_data_included'] = len(email_conversations) > 0
        combined_data['email_data_count'] = len(email_conversations)
        combined_data['email_data_source'] = email_data_path if email_data_path else 'none'
        combined_data['imessage_data_included'] = True
        combined_data['imessage_data_count'] = len(imessage_conversations)
        
        # Create a timestamp for the combined data
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        
        # Save the combined data to a new file
        combined_data_path = os.path.join(DATA_DIR, f'combined_training_data_{timestamp}.json')
        with open(combined_data_path, 'w') as f:
            json.dump(combined_data, f, indent=2)
        
        # Create a combined channel model JSONL file directly
        # This will be similar to the combined_channel_model.jsonl format
        combined_jsonl_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                          'models', f'combined_channel_model_{timestamp}.jsonl')
        
        # Create the JSONL entries
        jsonl_entries = []
        
        # Process iMessage conversations
        for conv in imessage_conversations:
            if 'messages' in conv and len(conv['messages']) >= 2:
                # Build chronological message list for this conversation
                chronological_messages = []
                for msg in conv['messages']:
                    if msg.get('text', '').strip():  # Only include non-empty messages
                        chronological_messages.append({
                            'text': msg['text'].strip(),
                            'is_from_me': msg.get('sender') == 'user',
                            'timestamp': msg.get('timestamp', '')
                        })
                
                # Create conversation-context training examples using sliding window
                min_context_length = 2
                max_context_length = 8
                
                for i in range(len(chronological_messages)):
                    current_msg = chronological_messages[i]
                    
                    # Only create examples where current message is from user (the response we want to learn)
                    if not current_msg['is_from_me']:
                        continue
                    
                    # Look back to build conversation context
                    context_start = max(0, i - max_context_length)
                    context_messages = chronological_messages[context_start:i]
                    
                    # Need at least min_context_length messages before the response
                    if len(context_messages) < min_context_length:
                        continue
                    
                    # Format conversation context like runtime format (Me: / Other:)
                    conversation_lines = []
                    for ctx_msg in context_messages:
                        sender = "Me" if ctx_msg['is_from_me'] else "Other"
                        conversation_lines.append(f"{sender}: {ctx_msg['text']}")
                    
                    conversation_context = "\n".join(conversation_lines)
                    user_response = current_msg['text']
                    
                    # Create training example with conversation context
                    entry = {
                        "messages": [
                            {
                                "role": "system",
                                "content": "You draft message suggestions that match the user's writing style, fit the conversation context, and are ready to send without editing."
                            },
                            {
                                "role": "user",
                                "content": conversation_context
                            },
                            {
                                "role": "assistant",
                                "content": user_response
                            }
                        ]
                    }
                    jsonl_entries.append(entry)
        
        # Process email conversations
        for conv in email_conversations:
            if 'messages' in conv and len(conv['messages']) >= 2:
                # Process message pairs for training
                for i in range(len(conv['messages']) - 1):
                    current_msg = conv['messages'][i]
                    next_msg = conv['messages'][i+1]
                    
                    # For emails, the user's messages have sender == 'assistant'
                    # and the metadata.from field contains the user's email
                    is_user_message = (
                        next_msg.get('sender') == 'assistant' and
                        'metadata' in next_msg and
                        'from' in next_msg['metadata'] and
                        user_email and
                        user_email.lower() in next_msg['metadata']['from'].lower() and
                        current_msg.get('text') and 
                        next_msg.get('text')
                    )
                    
                    if is_user_message:
                        print(f"Found email training pair from {current_msg.get('metadata', {}).get('from', 'unknown')} to {next_msg.get('metadata', {}).get('from', 'unknown')}")
                        
                        user_message = current_msg['text']
                        user_response = next_msg['text']
                        
                        # Create a JSONL entry with the message suggestions system prompt
                        entry = {
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You draft message suggestions that match the user's writing style, fit the conversation context, and are ready to send without editing."
                                },
                                {
                                    "role": "user",
                                    "content": user_message
                                },
                                {
                                    "role": "assistant",
                                    "content": user_response
                                }
                            ]
                        }
                        jsonl_entries.append(entry)
        
        # Write the JSONL file
        with open(combined_jsonl_path, 'w') as f:
            for entry in jsonl_entries:
                f.write(json.dumps(entry) + '\n')
        
        print(f"Created combined channel model JSONL file with {len(jsonl_entries)} entries at {combined_jsonl_path}")
        
        # Ensure we have at least one training example
        if len(jsonl_entries) == 0:
            return jsonify({
                'success': False,
                'message': 'No valid training examples could be created from the data. Please check your email and iMessage data.'
            }), 400
        
        # Split into train and validation sets (80/20 split)
        random.shuffle(jsonl_entries)
        split_idx = max(1, int(len(jsonl_entries) * 0.8))  # Ensure at least 1 example in training set
        train_entries = jsonl_entries[:split_idx]
        val_entries = jsonl_entries[split_idx:] if len(jsonl_entries) > 1 else train_entries  # Use training data for validation if only 1 example
        
        # Write train and validation files
        train_jsonl_path = combined_jsonl_path.replace('.jsonl', '_train.jsonl')
        val_jsonl_path = combined_jsonl_path.replace('.jsonl', '_val.jsonl')
        
        with open(train_jsonl_path, 'w') as f:
            for entry in train_entries:
                f.write(json.dumps(entry) + '\n')
        
        with open(val_jsonl_path, 'w') as f:
            for entry in val_entries:
                f.write(json.dumps(entry) + '\n')
        
        print(f"Created train file with {len(train_entries)} entries at {train_jsonl_path}")
        print(f"Created validation file with {len(val_entries)} entries at {val_jsonl_path}")
        
        # NEW: Build RAG database with the combined data
        print("Building RAG database with combined data...")
        try:
            from rag.pinecone_rag import PineconeRAGSystem
            
            # Initialize Pinecone RAG system directly
            rag_system = PineconeRAGSystem(user_id=user_id)
            
            # Clear existing data for this user
            rag_system.delete_user_data()
            
            # Add messages from iMessage conversations
            imessage_messages = []
            for conv in imessage_conversations:
                for msg in conv.get('messages', []):
                    if msg.get('sender') == 'user' and msg.get('text'):  # Only add user's messages
                        imessage_messages.append({
                            'text': msg.get('text', ''),
                            'timestamp': msg.get('timestamp', dt.now().isoformat()),
                            'source': "imessage",
                            'context': {
                                "conversation_id": conv.get('id', ''),
                                "recipient": conv.get('contact', 'unknown')
                            }
                        })
            
            # Add messages to Pinecone in one batch
            if imessage_messages:
                rag_system.add_messages_to_index(imessage_messages)
                print(f"Added {len(imessage_messages)} iMessage messages to Pinecone")
            
            # Add messages from email conversations
            email_messages = []
            for conv in email_conversations:
                for msg in conv.get('messages', []):
                    # For emails, the user's messages have sender == 'assistant'
                    # and the metadata.from field contains the user's email
                    is_user_message = (
                        msg.get('sender') == 'assistant' and
                        'metadata' in msg and
                        'from' in msg['metadata'] and
                        user_email and
                        user_email.lower() in msg['metadata']['from'].lower()
                    )
                    
                    if is_user_message:
                        print(f"Adding user email to RAG: {msg['metadata']['from']}")
                        email_messages.append({
                            'text': msg.get('text', ''),
                            'timestamp': msg.get('timestamp', dt.now().isoformat()),
                            'source': "email",
                            'channel': "email",  # Explicitly set channel to email
                            'context': {
                                "conversation_id": conv.get('id', ''),
                                "thread_id": conv.get('thread_id', ''),
                                "subject": msg.get('metadata', {}).get('subject', '')
                            }
                        })
            
            # Add email messages to Pinecone in one batch
            if email_messages:
                rag_system.add_messages_to_index(email_messages)
                print(f"Added {len(email_messages)} email messages to Pinecone")
            
            print("Pinecone RAG database built successfully")
            
            # Check if LinkedIn profiles directory exists
            linkedin_profiles_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                               'scrapers', 'data', 'linkedin_profiles')
            
            # Only try to access the directory if it exists
            if os.path.exists(linkedin_profiles_dir):
                linkedin_files = [f for f in os.listdir(linkedin_profiles_dir) 
                                 if f.endswith('.json')]
                print(f"Found {len(linkedin_files)} LinkedIn profile files")
            else:
                print("LinkedIn profiles directory not found. Skipping LinkedIn data processing.")
                linkedin_files = []  # Initialize as empty list to avoid errors later
            
            # Note: Letta memory creation removed for simplified version
            print("Skipping memory creation (Letta integration removed)")
            total_memories = 0
            
        except Exception as rag_error:
            print(f"Error building RAG database: {rag_error}")
            import traceback
            traceback.print_exc()
        
        # Upload the training file to OpenAI
        print("Uploading training file to OpenAI...")
        with open(train_jsonl_path, 'rb') as f:
            response = client.files.create(
                file=f,
                purpose='fine-tune'
            )
            
        training_file_id = response.id
        print(f"Training file uploaded with ID: {training_file_id}")
        
        # Upload validation file
        print("Uploading validation file to OpenAI...")
        with open(val_jsonl_path, 'rb') as f:
            response = client.files.create(
                file=f,
                purpose='fine-tune'
            )
            
        validation_file_id = response.id
        print(f"Validation file uploaded with ID: {validation_file_id}")
        
        # Wait for the file to be processed
        print("Waiting for file to be processed...")
        time.sleep(30)
        
        # Create the fine-tuning job with the specific model
        print("Creating fine-tuning job...")
        response = client.fine_tuning.jobs.create(
            training_file=training_file_id,
            validation_file=validation_file_id,
            model="gpt-4o-mini-2024-07-18"  # Explicitly use the correct base model
        )
        
        job_id = response.id
        print(f"Fine-tuning job created with ID: {job_id}")
        
        # Update MongoDB with the job ID
        try:
            from utils.auth import db
            import pymongo
            
            # Use the user_id parameter passed to this function
            if user_id:
                db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "fine_tuning_job_id": job_id,
                        "fine_tuning_in_progress": True,
                        "fine_tuning_started_at": dt.now().isoformat()
                    }}
                )
                print(f"Successfully updated MongoDB with job ID: {job_id} for user: {user_id}")
            else:
                print("Warning: No user_id available to update MongoDB with job ID")
        except Exception as e:
            print(f"Error updating MongoDB: {e}")
        
        # Update the combined data with fine-tuning information
        combined_data = {
            "fine_tuning_job_id": job_id,
            "fine_tuning_in_progress": True,
            "fine_tuning_started_at": dt.now().isoformat(),
            "base_model": "gpt-4o-mini-2024-07-18",
            "rag_database_built": True,
            "memories_created": False
        }
        
        # Save the updated combined data
        with open(combined_data_path, 'w') as f:
            json.dump(combined_data, f, indent=2)
        
        # Also update the original training data file to indicate fine-tuning is in progress
        with open(TRAINING_DATA_PATH, 'r') as f:
            training_data = json.load(f)
        
        training_data['fine_tuning_job_id'] = job_id
        training_data['fine_tuning_in_progress'] = True
        training_data['fine_tuning_started_at'] = dt.now().isoformat()
        training_data['combined_training_data_path'] = combined_data_path
        training_data['last_updated'] = dt.now().isoformat()
        training_data['rag_database_built'] = True
        training_data['memories_created'] = False
        
        with open(TRAINING_DATA_PATH, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        # Return success response with training information
        return jsonify({
            'success': True,
            'message': f'Training data combined with {len(imessage_conversations)} iMessage conversations. Model training started. This process may take 30-60 minutes to complete.',
            'imessage_count': len(imessage_conversations),
            'email_count': len(email_conversations),
            'total_count': len(jsonl_entries),
            'job_id': job_id,
            'imessage_data_source': imessage_data_path,
            'email_data_source': email_data_path if email_data_path else 'none',
            'rag_database_built': True,
            'letta_memories_created': True
        })
    except Exception as e:
        print(f"Error combining data and retraining: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/draft-message', methods=['POST'])
def draft_message():
    """Generate a text message draft using the AI clone"""
    data = request.json
    context = data.get('context', '')
    recipient = data.get('recipient', '')
    formality = data.get('formality', 'casual')  # casual, professional, formal
    
    # Load user profile
    user_profile = {}
    if os.path.exists(USER_PROFILE_PATH):
        with open(USER_PROFILE_PATH, 'r') as f:
            user_profile = json.load(f)
    
    # Create a simple system prompt similar to the chat interface
    system_prompt = f"You are an AI clone that mimics the user's communication style. You're drafting a {formality} text message based on the given context."
    
    # Add specific instructions for text message generation
    message_instructions = f"""
    Draft a text message in {formality} tone about: {context}
    """
    
    if recipient:
        message_instructions += f" The message is for: {recipient}"
    
    # Skip RAG enhancement for now since focusing on speed
    enhanced_prompt = system_prompt
    print(f"Using basic prompt for text message drafting (RAG disabled for speed)")
    
    # Prepare messages for API call with the enhanced prompt
    messages = [
        {"role": "system", "content": enhanced_prompt},
        {"role": "user", "content": message_instructions}
    ]
    
    # Get model ID from environment or use default
    if not hasattr(g, 'user_id') or not g.user_id:
        error_msg = "No user ID available in request context. Cannot proceed without user identification."
        print(f"ERROR: {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 400
    
    user_id = g.user_id
    
    # Get model from user config
    user_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'user_configs')
    user_model_config_path = os.path.join(user_config_dir, f'{user_id}_model_config.json')
    
    if not os.path.exists(user_model_config_path):
        return jsonify({
            'success': False,
            'error': 'No model config found. Please train your model first.'
        }), 400
    
    try:
        with open(user_model_config_path, 'r') as f:
            model_config = json.load(f)
        
        if not model_config.get('trained', False) or not model_config.get('fine_tuned_model'):
            return jsonify({
                'success': False,
                'error': 'No trained model available. Please train your model first.'
            }), 400
        
        model_id = model_config['fine_tuned_model']
    except Exception as e:
        print(f"Error loading user model config: {e}")
        return jsonify({
            'success': False,
            'error': 'Error loading model configuration.'
        }), 500
    
    try:
        # Use the existing OpenAI client (initialized at the top of the file)
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=500,
            temperature=0.6  # Reduced from 0.7 to 0.6 to reduce hallucinations
        )
        
        # Extract the generated message
        draft = response.choices[0].message.content.strip()
        
        return jsonify({
            "success": True,
            "draft": draft
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/add-to-rag', methods=['POST'])
def add_to_rag():
    """Add a conversation to the RAG system for future context"""
    try:
        data = request.json
        user_message = data.get('user_message', {})
        ai_response = data.get('ai_response', {})
        user_id = data.get('user_id', None)
        
        # Validate required fields
        if not user_message or not ai_response:
            return jsonify({"error": "Both user_message and ai_response are required"}), 400
        
        # Add to RAG system
        from rag.app_integration import add_interaction_to_rag
        
        # Create conversation history with the current interaction
        conversation_history = []
        
        # If this is an email, add more context
        is_email = user_message.get('channel') == 'email'
        subject = user_message.get('subject', '')
        previous_context = user_message.get('previous_context', '')
        
        # If there's previous context (like a previous email), add it first
        if previous_context and is_email:
            conversation_history.append({
                'text': previous_context,
                'sender': 'other',  # Not the user or the clone
                'channel': 'email',
                'subject': subject,
                'timestamp': (dt.now() - timedelta(hours=1)).isoformat()  # Slightly older
            })
        
        # Add the user message
        conversation_history.append({
            'text': user_message.get('text', ''),
            'sender': 'user',
            'channel': user_message.get('channel', 'text'),
            'subject': subject,
            'timestamp': user_message.get('timestamp', dt.now().isoformat())
        })
        
        # Add the AI response
        conversation_history.append({
            'text': ai_response.get('text', ''),
            'sender': 'clone',
            'channel': user_message.get('channel', 'text'),
            'subject': subject,
            'timestamp': ai_response.get('timestamp', dt.now().isoformat())
        })
        
        # Add the interaction to RAG with enhanced context
        add_interaction_to_rag(
            user_message.get('text', ''),
            ai_response.get('text', ''),
            conversation_history=conversation_history,
            user_id=user_id  # Pass user_id to add_interaction_to_rag
        )
        
        # Log what was added
        print(f"Added to RAG: {user_message.get('channel', 'text').upper()} message for user {user_id}")
        if is_email:
            print(f"Email subject: {subject}")
        print(f"User message: {user_message.get('text', '')[:50]}...")
        print(f"AI response: {ai_response.get('text', '')[:50]}...")
        
        return jsonify({"success": True, "message": "Conversation added to RAG system"})
    except Exception as e:
        print(f"Error adding to RAG: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/start-training', methods=['POST'])
def start_training():
    """
    Start the training process in a background thread and return immediately.
    This prevents timeout errors on the frontend.
    """
    try:
        # Capture the user ID from the request context before starting the thread
        from flask import g
        user_id = g.user_id if hasattr(g, 'user_id') and g.user_id else None
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'No user ID found in request context. Please ensure you are logged in.'
            }), 400
            
        print(f"Starting training for user: {user_id}")
        
        # Start the training process in a background thread, passing the user_id
        training_thread = threading.Thread(
            target=combine_data_and_retrain,
            kwargs={"user_id": user_id}
        )
        training_thread.daemon = True
        training_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Training process started in the background. This may take 30-60 minutes to complete.',
            'training_started': True
        })
    except Exception as e:
        print(f"Error starting training thread: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/overlay-settings', methods=['GET', 'POST'])
def handle_overlay_settings():
    """Save or retrieve overlay settings for the current user"""
    try:
        # Ensure user is authenticated
        if not hasattr(g, 'user_id') or not g.user_id:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401
            
        # Import auth module which has the proper MongoDB connection
        from utils.auth import db
        
        # Handle GET request - retrieve settings
        if request.method == 'GET':
            # Get user from MongoDB
            user = db.users.find_one({'user_id': g.user_id})
            
            if user and 'overlay_settings' in user:
                return jsonify({
                    'success': True,
                    'settings': user['overlay_settings']
                })
            else:
                # Return default settings if not found
                return jsonify({
                    'success': True,
                    'settings': {
                        'suggestionCount': 3,
                        'checkInterval': 5
                    }
                })
        
        # Handle POST request - save settings
        elif request.method == 'POST':
            data = request.json
            settings = data.get('settings', {})
            
            # Validate settings
            if not isinstance(settings, dict):
                return jsonify({
                    'success': False,
                    'message': 'Invalid settings format'
                }), 400
                
            # Update user document with overlay settings
            result = db.users.update_one(
                {'user_id': g.user_id},
                {'$set': {'overlay_settings': settings}},
                upsert=True
            )
            
            if result.modified_count > 0 or result.upserted_id:
                print(f"Updated overlay settings for user {g.user_id}")
                return jsonify({
                    'success': True,
                    'message': 'Settings saved successfully'
                })
            else:
                print(f"Warning: MongoDB update for user {g.user_id} overlay settings did not modify any records")
                return jsonify({
                    'success': False,
                    'message': 'Settings not updated'
                }), 500
    
    except Exception as e:
        error_msg = f"Error handling overlay settings: {e}"
        print(error_msg)
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500

@app.route('/api/fine-tuning-status', methods=['GET'])
def get_fine_tuning_status():
    """Get the status of the fine-tuning process - uses MongoDB exclusively as source of truth"""
    try:
        # Default response data structure for new users or error cases
        response_data = {
            'trained': False,
            'in_progress': False,
            'started_at': None,
            'last_updated': None,
            'model_id': None,
            'current_session_messages': 0,
            'messages_needed': 10,  # Default to needing 10 messages
            'total_user_messages': 0,
            'job_id': None,
            'error': None
        }
        
        # Get current user ID from Flask global
        user_id = g.user_id if hasattr(g, 'user_id') and g.user_id else None
        
        if not user_id:
            print("WARNING: No user_id available in request context")
            return jsonify(response_data)
        
        # Check MongoDB for user training status - the ONLY source of truth
        try:
            # Import auth module which has the proper MongoDB connection
            from utils.auth import db
            
            # Get user from MongoDB
            user = db.users.find_one({"user_id": user_id})
            if user:
                # Get training status from MongoDB only
                response_data['trained'] = user.get('model_trained', False) 
                
                # Only populate model_id if both conditions are met
                if user.get('model_trained', False) and user.get('fine_tuned_model_id'):
                    response_data['model_id'] = user.get('fine_tuned_model_id')
                
                # Get additional training metadata if available
                response_data['last_updated'] = user.get('model_last_updated')
                
                # Log what we found in MongoDB
                print(f"MongoDB training status for user {user_id}: trained={response_data['trained']}, model_id={response_data['model_id']}")
            else:
                print(f"No MongoDB record found for user {user_id}")
                
        except Exception as e:
            error_msg = f"Error checking MongoDB for user training status: {e}"
            print(error_msg)
            response_data['error'] = error_msg
        
        # Check if there's an active fine-tuning job in OpenAI
        # This is still valuable as we want to check OpenAI API for job status
        check_status = request.args.get('check_status', 'true').lower() == 'true'
        
        # Get job_id from MongoDB if available
        job_id = None
        if user and user.get('fine_tuning_job_id'):
            job_id = user.get('fine_tuning_job_id')
            response_data['job_id'] = job_id
        
        # If a job_id exists, check its status with OpenAI
        if job_id and check_status:
            try:
                # Get the status from OpenAI
                response = client.fine_tuning.jobs.retrieve(job_id)
                status = response.status
                
                print(f"Fine-tuning job status: {status}")
                response_data['in_progress'] = status in ['created', 'pending', 'running']
                
                # If job succeeded, update the user record in MongoDB
                if status == 'succeeded':
                    try:
                        from utils.auth import db
                        
                        # Get the fine-tuned model ID from OpenAI
                        fine_tuned_model = response.fine_tuned_model
                        
                        # Update MongoDB directly
                        update_result = db.users.update_one(
                            {"user_id": user_id},
                            {"$set": {
                                "model_trained": True,
                                "has_fine_tuned_model": True,
                                "fine_tuning_in_progress": False, 
                                "fine_tuned_model_id": fine_tuned_model,
                                "model_last_updated": dt.now().isoformat()
                            }}
                        )
                        
                        if update_result.modified_count > 0:
                            print(f"Updated MongoDB record for user {user_id} to reflect training completion")
                            # Update the response to reflect the change
                            response_data['trained'] = True
                            response_data['model_id'] = fine_tuned_model
                            response_data['in_progress'] = False
                        else:
                            print(f"Warning: MongoDB update for user {user_id} training status did not modify any records")
                            
                    except Exception as e:
                        error_msg = f"Error updating MongoDB after successful fine-tuning: {e}"
                        print(error_msg)
                        response_data['error'] = error_msg
                        
                elif status == 'failed':
                    error_msg = "Fine-tuning job failed"
                    print(error_msg)
                    response_data['error'] = error_msg
                    
                    # Update MongoDB to reflect the failure
                    try:
                        from utils.auth import db
                        db.users.update_one(
                            {"user_id": user_id},
                            {"$set": {
                                "fine_tuning_in_progress": False,
                                "fine_tuning_error": error_msg
                            }}
                        )
                    except Exception as e:
                        print(f"Error updating MongoDB after fine-tuning failure: {e}")
                
            except Exception as e:
                error_msg = f"Error checking OpenAI fine-tuning job status: {e}"
                print(error_msg)
                response_data['error'] = error_msg
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Unexpected error in fine-tuning status endpoint: {e}")
        return jsonify({'error': str(e), 'trained': False}), 500

@app.route('/api/reset-training-status', methods=['POST'])
def reset_training_status():
    """Reset the training status for the current user to allow starting a new training job"""
    try:
        # Get current user ID from Flask global
        user_id = g.user_id if hasattr(g, 'user_id') and g.user_id else None
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'No user ID found in request context. Please ensure you are logged in.'
            }), 400
        
        # Import auth module which has the proper MongoDB connection
        from utils.auth import db
        
        # Update MongoDB to reset training status
        result = db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "model_trained": False,
                "fine_tuned_model_id": None,
                "fine_tuning_job_id": None,
                "fine_tuning_in_progress": False,
                "fine_tuning_started_at": None,
                "model_last_updated": None
            }}
        )
        
        if result.modified_count > 0:
            return jsonify({
                'success': True,
                'message': 'Training status reset successfully. You can now start a new training job.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to reset training status. User record not found or no changes made.'
            }), 404
            
    except Exception as e:
        print(f"Error resetting training status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.before_request
def set_user_context():
    """Set user context from JWT token"""
    # Skip for authentication routes
    if request.path.startswith('/api/auth/'):
        return
        
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        from utils.auth import decode_token, get_user_by_id
        
        token = auth_header.split(' ')[1]
        user_id = decode_token(token)
        
        if user_id:
            user = get_user_by_id(user_id)
            if user:
                g.user = user
                g.user_id = user_id
                return
    
    # Default to None if no valid user found
    g.user = None
    g.user_id = None

def get_user_rag_system(user_id=None, force_init=False):
    """
    Get or create a user-specific RAG system.
    
    Args:
        user_id: User ID to get RAG system for
        force_init: If True, force initialization even if not cached
        
    Returns:
        PineconeRAGSystem: User-specific RAG system, or None if not initialized
    """
    global user_rag_systems
    
    # If no user_id provided, try to get from Flask request context
    if not user_id:
        try:
            from flask import g
            user_id = g.user_id if hasattr(g, 'user_id') and g.user_id else None
        except:
            pass
    
    # If still no user_id, use default
    if not user_id:
        user_id = "default"
    
    # Check if we already have a RAG system for this user
    if user_id in user_rag_systems:
        return user_rag_systems[user_id]
    
    # Only create a new RAG system if force_init is True
    if force_init:
        # Create a new RAG system for this user
        from rag.pinecone_rag import PineconeRAGSystem
        user_rag = PineconeRAGSystem(user_id=user_id)
        
        # Cache it for future use
        user_rag_systems[user_id] = user_rag
        
        return user_rag
    
    # Return None if not cached and not forced to initialize
    return None

# Store the latest suggestions in memory
latest_suggestions = []

@app.route('/api/latest-suggestions', methods=['GET'])
def get_latest_suggestions():
    """Return the latest message suggestions"""
    return jsonify({
        'success': True,
        'suggestions': latest_suggestions
    })

@app.route('/api/update-suggestions', methods=['POST'])
def update_latest_suggestions():
    """Update the latest message suggestions"""
    global latest_suggestions
    data = request.get_json()
    
    if data and 'suggestions' in data and isinstance(data['suggestions'], list):
        latest_suggestions = data['suggestions']
        print(f"Updated latest suggestions: {latest_suggestions}")
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid suggestions format'}), 400

@app.route('/api/suggestion-selected', methods=['POST'])
def suggestion_selected():
    """Handle when a suggestion is selected by the user"""
    data = request.get_json()
    
    if data and 'index' in data and 'text' in data:
        print(f"User selected suggestion {data['index']}: \"{data['text']}\" (inserted: {data.get('inserted', False)})")
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid suggestion selection format'}), 400

@app.route('/api/conversation-context', methods=['POST'])
def conversation_context():
    """Handle conversation context from the overlay agent"""
    data = request.get_json()
    
    if data and 'context' in data and isinstance(data['context'], str):
        print(f"Received conversation context ({len(data['context'])} chars)")
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid conversation context format'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
