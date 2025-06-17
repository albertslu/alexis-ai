"""
Routes for the Gmail Listener functionality.
These routes handle starting, stopping, and configuring the Gmail listener.
"""

import os
import json
import subprocess
import sys
import traceback
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, g

# Set up a logger for this module
logger = logging.getLogger('gmail_listener_routes')
logger.setLevel(logging.INFO)

# Add a handler that writes to stderr (which will be captured in the backend.log)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

logger.info("========== GMAIL_LISTENER_ROUTES.PY MODULE LOADED ==========")
logger.info(f"Python path: {sys.path}")
logger.info(f"Current directory: {os.getcwd()}")

gmail_listener_bp = Blueprint('gmail_listener', __name__)

# Define the default configuration directly to avoid import issues
DEFAULT_CONFIG = {
    'auto_respond': False,
    'check_interval': 60,  # seconds
    'max_emails_per_check': 5,
    'respond_to_all': False,
    'filter_labels': [],
    'filter_from': '',
    'filter_to': '',
    'filter_subject': ''
}

# Ensure the project root is in the Python path
# Add the project root to the Python path if it's not already there
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also add the utils directory specifically
utils_dir = os.path.join(project_root, 'utils')
if utils_dir not in sys.path:
    sys.path.insert(0, utils_dir)

# Log the current Python path and working directory for debugging
print(f"Python path in gmail_listener_routes.py: {sys.path}")
print(f"Current directory in gmail_listener_routes.py: {os.getcwd()}")
print(f"Project root in gmail_listener_routes.py: {project_root}")
print(f"Utils directory in gmail_listener_routes.py: {utils_dir}")

# This will help us track if the module is being loaded correctly in production

# First import the MongoDB connection from auth
try:
    # Import the MongoDB connection from auth
    print("Attempting to import auth module...")
    from utils.auth import db, users_collection
    print(f"Successfully imported auth module with db: {db.name}")
    
    # Ensure the gmail_configs collection exists
    print("Checking if gmail_configs collection exists...")
    collections = db.list_collection_names()
    print(f"Available collections: {collections}")
    
    # Check if the gmail_configs collection exists
    if 'gmail_configs' not in collections:
        print("gmail_configs collection does not exist, creating it now...")
        
        # Create the collection
        gmail_configs = db.create_collection('gmail_configs')
        print(f"Created gmail_configs collection: {gmail_configs.name}")
        
        # Create an index on user_id for faster lookups
        gmail_configs.create_index('user_id', unique=True)
        print("Created index on user_id field")
        
        # Create a dummy document to ensure the collection exists
        dummy_config = DEFAULT_CONFIG.copy()
        dummy_config['user_id'] = 'dummy_user_id'
        dummy_config['is_dummy'] = True
        
        # Insert the dummy document
        result = gmail_configs.insert_one(dummy_config)
        print(f"Created dummy document in gmail_configs collection: {result.inserted_id}")
    else:
        print("gmail_configs collection already exists")
        gmail_configs = db.get_collection('gmail_configs')
        print(f"Retrieved gmail_configs collection: {gmail_configs.name}")
        
        # Check if the dummy document exists
        dummy_doc = gmail_configs.find_one({"user_id": "dummy_user_id"})
        if not dummy_doc:
            print("Creating dummy document in existing collection...")
            dummy_config = DEFAULT_CONFIG.copy()
            dummy_config['user_id'] = 'dummy_user_id'
            dummy_config['is_dummy'] = True
            result = gmail_configs.insert_one(dummy_config)
            print(f"Created dummy document: {result.inserted_id}")
        else:
            print(f"Dummy document already exists: {dummy_doc['_id']}")

except Exception as e:
    print(f"Error setting up MongoDB connection: {str(e)}")
    import traceback
    print(traceback.format_exc())
    
# Now try to import the Gmail configuration module
try:
    # Try to import the module directly
    print("Attempting to import gmail_config module...")
    from utils.gmail_config import (
        get_current_user_gmail_config,
        update_current_user_gmail_config
    )
    print("Successfully imported gmail_config module")
    
    # Set a flag to indicate successful import
    GMAIL_CONFIG_IMPORTED = True
except Exception as e:
    print(f"Error importing gmail_config module: {str(e)}")
    import traceback
    print(traceback.format_exc())
    
    # Define our own implementation of the Gmail configuration functions
    print("Defining custom Gmail configuration functions")
    
    # Define functions to work with the gmail_configs collection
    def get_current_user_gmail_config():
        """Get the Gmail configuration for the current user"""
        print("Using custom get_current_user_gmail_config function")
        
        user_id = getattr(g, 'user_id', None)
        print(f"Current user_id from g: {user_id}")
        
        # If not found, check for _id in g.user
        if not user_id and hasattr(g, 'user') and g.user and '_id' in g.user:
            user_id = g.user['_id']
            print(f"Using _id from g.user: {user_id}")
        
        if not user_id:
            print("No user_id found, returning default config")
            return DEFAULT_CONFIG.copy()
        
        # Get the user's configuration from MongoDB
        try:
            # First try with user_id field
            print(f"Looking for config with user_id: {user_id}")
            config = db.gmail_configs.find_one({"user_id": user_id})
            
            # If not found, try with _id field
            if not config:
                print(f"No config found with user_id, trying with _id: {user_id}")
                config = db.gmail_configs.find_one({"_id": user_id})
            
            if config:
                print(f"Found existing config: {config}")
                # Make a copy to avoid modifying the original
                config_copy = config.copy()
                # Remove MongoDB _id field before returning if it's not the user_id
                if "_id" in config_copy and config_copy["_id"] != user_id:
                    del config_copy["_id"]
                # Ensure user_id is set correctly
                config_copy["user_id"] = user_id
                return config_copy
            else:
                print(f"No config found, creating new config for user: {user_id}")
                # Create a new configuration for the user
                new_config = DEFAULT_CONFIG.copy()
                new_config["user_id"] = user_id
                
                # Insert the new configuration
                result = db.gmail_configs.insert_one(new_config)
                print(f"Created new config with ID: {result.inserted_id}")
                
                # Return a copy without the _id field
                return_config = new_config.copy()
                if "_id" in return_config:
                    del return_config["_id"]
                return return_config
        except Exception as e:
            print(f"Error getting user Gmail config: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return DEFAULT_CONFIG.copy()
    
    def update_current_user_gmail_config(config_updates):
        """Update the Gmail configuration for the current user"""
        print("Using custom update_current_user_gmail_config function")
        print(f"Config updates: {config_updates}")
        
        user_id = getattr(g, 'user_id', None)
        print(f"Current user_id from g: {user_id}")
        
        # If not found, check for _id in g.user
        if not user_id and hasattr(g, 'user') and g.user and '_id' in g.user:
            user_id = g.user['_id']
            print(f"Using _id from g.user: {user_id}")
        
        if not user_id:
            print("No user_id found, returning updated default config")
            config = DEFAULT_CONFIG.copy()
            config.update(config_updates)
            return config
        
        # Update the user's configuration in MongoDB
        try:
            # Get the current configuration
            print("Getting current config before update")
            current_config = get_current_user_gmail_config()
            print(f"Current config before update: {current_config}")
            
            # Update with new values
            current_config.update(config_updates)
            print(f"Updated config: {current_config}")
            
            # Ensure user_id is set correctly
            current_config["user_id"] = user_id
            
            # Save to MongoDB - try both user_id and _id for compatibility
            print(f"Saving config to MongoDB for user: {user_id}")
            result = db.gmail_configs.update_one(
                {"user_id": user_id},
                {"$set": current_config},
                upsert=True
            )
            print(f"Update result: {result.modified_count} documents modified, {result.upserted_id} upserted")
            
            return current_config
        except Exception as e:
            print(f"Error updating user Gmail config: {str(e)}")
            import traceback
            print(traceback.format_exc())
            config = DEFAULT_CONFIG.copy()
            config.update(config_updates)
            return config
    
    # Set a flag to indicate we're using our custom implementation
    GMAIL_CONFIG_IMPORTED = False

# Import authentication decorator
from utils.auth import token_required

# Constants
SCRIPT_PATH = Path(__file__).parent.parent / 'scripts' / 'gmail_listener.py'
PID_FILE = Path('gmail_listener.pid')
CREDENTIALS_FILE = Path('credentials.json')
OUTPUT_LOG_FILE = Path('gmail_listener_output.log')


@gmail_listener_bp.route('/gmail-listener/status', methods=['GET'])
@token_required
def get_status():
    """Get the status of the Gmail Listener script"""
    try:
        # Log diagnostic information
        print("========== GMAIL LISTENER STATUS ENDPOINT CALLED ==========")
        print(f"Current directory: {os.getcwd()}")
        print(f"Python path: {sys.path}")
        print(f"GMAIL_CONFIG_IMPORTED: {GMAIL_CONFIG_IMPORTED}")
        print(f"User ID: {g.user_id if hasattr(g, 'user_id') else 'None'}")
        print(f"User object: {g.user if hasattr(g, 'user') else 'None'}")
        
        # Check MongoDB connection and collections
        print("Checking MongoDB connection and collections...")
        try:
            collections = db.list_collection_names()
            print(f"Available collections: {collections}")
            
            # Ensure gmail_configs collection exists
            if 'gmail_configs' not in collections:
                print("gmail_configs collection does not exist, creating it now...")
                db.create_collection('gmail_configs')
                print("Created gmail_configs collection")
                
                # Create index on user_id
                db.gmail_configs.create_index('user_id', unique=True)
                print("Created index on user_id field")
                
                # Create a dummy document
                dummy_config = DEFAULT_CONFIG.copy()
                dummy_config['user_id'] = 'dummy_user_id'
                dummy_config['is_dummy'] = True
                result = db.gmail_configs.insert_one(dummy_config)
                print(f"Created dummy document with ID: {result.inserted_id}")
        except Exception as mongo_error:
            print(f"Error checking MongoDB: {str(mongo_error)}")
            print(traceback.format_exc())
        
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
                # Process doesn't exist
                pass
        
        # Get the current user's configuration from MongoDB
        print("Calling get_current_user_gmail_config()")
        config = get_current_user_gmail_config()
        print(f"Retrieved config: {config}")
        
        # Check if we're using the fallback function
        using_fallback = not GMAIL_CONFIG_IMPORTED
        
        # Include diagnostic information in the response
        response = {
            "status": "running" if is_running else "stopped",
            "pid": pid,
            "config": config,
            "diagnostic": {
                "gmail_config_imported": GMAIL_CONFIG_IMPORTED,
                "using_fallback": using_fallback,
                "current_directory": os.getcwd(),
                "python_path": sys.path,
                "user_id": g.user_id if hasattr(g, 'user_id') else None,
                "has_user_object": hasattr(g, 'user'),
                "mongodb_collections": db.list_collection_names() if 'db' in globals() else [],
                "env_variables": {
                    "MONGODB_URI": os.environ.get("MONGODB_URI", "Not set"),
                    "DB_NAME": os.environ.get("DB_NAME", "Not set"),
                    "FLASK_ENV": os.environ.get("FLASK_ENV", "Not set")
                }
            }
        }
        
        print(f"Returning response: {response}")
        return jsonify(response)
    except Exception as e:
        print(f"Error getting Gmail listener status: {str(e)}")
        print(traceback.format_exc())
        if hasattr(current_app, 'logger'):
            current_app.logger.error(f"Error getting Gmail listener status: {str(e)}")
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "diagnostic": {
                "gmail_config_imported": globals().get('GMAIL_CONFIG_IMPORTED', False),
                "current_directory": os.getcwd(),
                "python_path": sys.path,
                "user_id": getattr(g, 'user_id', None),
                "has_user_object": hasattr(g, 'user'),
                "env_variables": {
                    "MONGODB_URI": os.environ.get("MONGODB_URI", "Not set"),
                    "DB_NAME": os.environ.get("DB_NAME", "Not set"),
                    "FLASK_ENV": os.environ.get("FLASK_ENV", "Not set")
                }
            }
        }), 500

@gmail_listener_bp.route('/gmail-listener/start', methods=['POST'])
@token_required
def start_listener():
    """Start the Gmail Listener script"""
    try:
        # Check if already running
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            try:
                os.kill(pid, 0)
                return jsonify({"error": "Gmail Listener is already running", "pid": pid}), 400
            except OSError:
                # Process doesn't exist, continue with starting
                pass
        
        # Check if credentials exist
        if not CREDENTIALS_FILE.exists():
            return jsonify({"error": "Gmail API credentials not found. Please upload credentials.json first."}), 400
        
        # Update user-specific configuration if provided
        if request.json:
            # Update the user's configuration in MongoDB
            config = update_current_user_gmail_config(request.json)
        else:
            # Get the current user's configuration
            config = get_current_user_gmail_config()
        
        # Create or clear the output log file
        with open(OUTPUT_LOG_FILE, 'w') as f:
            f.write(f"Starting Gmail listener...\n")
        
        # Get the current user ID
        user_id = None
        if hasattr(g, 'user') and g.user:
            user_id = g.user.get('_id')
        
        if not user_id:
            return jsonify({"error": "No authenticated user found"}), 401
        
        # Start the script with output redirection and user ID
        output_log = open(OUTPUT_LOG_FILE, 'a')
        process = subprocess.Popen(
            ['python', str(SCRIPT_PATH), '--user-id', str(user_id)],
            stdout=output_log, 
            stderr=output_log
        )
        
        return jsonify({
            "status": "started",
            "pid": process.pid,
            "message": "Gmail Listener started successfully"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@gmail_listener_bp.route('/gmail-listener/stop', methods=['POST'])
@token_required
def stop_listener():
    """Stop the Gmail Listener script"""
    try:
        if not PID_FILE.exists():
            return jsonify({"error": "Gmail Listener is not running"}), 400
        
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        try:
            os.kill(pid, signal.SIGTERM)
            return jsonify({
                "status": "stopped",
                "message": "Gmail Listener stopped successfully"
            })
        except OSError as e:
            # Process doesn't exist
            if PID_FILE.exists():
                PID_FILE.unlink()
            return jsonify({
                "status": "stopped",
                "message": f"Process was not running, cleaned up PID file: {e}"
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@gmail_listener_bp.route('/gmail-listener/config', methods=['GET', 'POST'])
@token_required
def handle_config():
    """Get or update the Gmail Listener configuration"""
    try:
        # Log diagnostic information
        print("========== GMAIL LISTENER CONFIG ENDPOINT CALLED ==========")
        print(f"Method: {request.method}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Python path: {sys.path}")
        print(f"GMAIL_CONFIG_IMPORTED: {GMAIL_CONFIG_IMPORTED}")
        print(f"User ID: {g.user_id if hasattr(g, 'user_id') else 'None'}")
        print(f"User object: {g.user if hasattr(g, 'user') else 'None'}")
        
        # Check MongoDB connection and collections
        print("Checking MongoDB connection and collections...")
        try:
            collections = db.list_collection_names()
            print(f"Available collections: {collections}")
            
            # Ensure gmail_configs collection exists
            if 'gmail_configs' not in collections:
                print("gmail_configs collection does not exist, creating it now...")
                db.create_collection('gmail_configs')
                print("Created gmail_configs collection")
                
                # Create index on user_id
                db.gmail_configs.create_index('user_id', unique=True)
                print("Created index on user_id field")
                
                # Create a dummy document to ensure the collection exists
                dummy_config = DEFAULT_CONFIG.copy()
                dummy_config['user_id'] = 'dummy_user_id'
                dummy_config['is_dummy'] = True
                result = db.gmail_configs.insert_one(dummy_config)
                print(f"Created dummy document with ID: {result.inserted_id}")
        except Exception as mongo_error:
            print(f"Error checking MongoDB: {str(mongo_error)}")
            print(traceback.format_exc())
        
        if request.method == 'GET':
            # Get the current user's configuration
            print("Calling get_current_user_gmail_config() from GET handler")
            config = get_current_user_gmail_config()
            print(f"Retrieved config: {config}")
            
            # Include diagnostic information in the response
            response = {
                "config": config,
                "diagnostic": {
                    "gmail_config_imported": GMAIL_CONFIG_IMPORTED,
                    "using_fallback": not GMAIL_CONFIG_IMPORTED,
                    "current_directory": os.getcwd(),
                    "python_path": sys.path,
                    "user_id": g.user_id if hasattr(g, 'user_id') else None,
                    "has_user_object": hasattr(g, 'user'),
                    "mongodb_collections": collections if 'collections' in locals() else [],
                    "env_variables": {
                        "MONGODB_URI": os.environ.get("MONGODB_URI", "Not set"),
                        "DB_NAME": os.environ.get("DB_NAME", "Not set"),
                        "FLASK_ENV": os.environ.get("FLASK_ENV", "Not set")
                    }
                }
            }
            
            print(f"Returning GET response: {response}")
            return jsonify(response)
            
        elif request.method == 'POST':
            # Log the request body
            print(f"Request JSON: {request.json}")
            
            # Update the user's configuration
            print("Calling update_current_user_gmail_config() from POST handler")
            config = update_current_user_gmail_config(request.json)
            print(f"Updated config: {config}")
            
            # Verify the config was saved correctly
            print("Verifying configuration was saved correctly...")
            saved_config = get_current_user_gmail_config()
            print(f"Saved config: {saved_config}")
            
            # Include diagnostic information in the response
            response = {
                "config": config,
                "status": "success",
                "message": "Configuration updated successfully",
                "verification": {
                    "saved_config": saved_config,
                    "matches_expected": all(saved_config.get(k) == config.get(k) for k in request.json.keys())
                },
                "diagnostic": {
                    "gmail_config_imported": GMAIL_CONFIG_IMPORTED,
                    "using_fallback": not GMAIL_CONFIG_IMPORTED,
                    "current_directory": os.getcwd(),
                    "python_path": sys.path,
                    "user_id": g.user_id if hasattr(g, 'user_id') else None,
                    "has_user_object": hasattr(g, 'user'),
                    "mongodb_collections": collections if 'collections' in locals() else []
                }
            }
            
            logger.info(f"Returning POST response: {response}")
            return jsonify(response)
    except Exception as e:
        logger.error(f"Error handling Gmail listener config: {str(e)}")
        logger.error(traceback.format_exc())
        if hasattr(current_app, 'logger'):
            current_app.logger.error(f"Error handling Gmail listener config: {str(e)}")
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "diagnostic": {
                "gmail_config_imported": globals().get('GMAIL_CONFIG_IMPORTED', False),
                "current_directory": os.getcwd(),
                "python_path": sys.path
            }
        }), 500

@gmail_listener_bp.route('/gmail-listener/credentials', methods=['POST'])
@token_required
def upload_credentials():
    """Upload Gmail API credentials"""
    try:
        if 'credentials' not in request.files:
            return jsonify({"error": "No credentials file provided"}), 400
        
        file = request.files['credentials']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if file and file.filename.endswith('.json'):
            file.save(str(CREDENTIALS_FILE))
            return jsonify({
                "status": "success",
                "message": "Credentials uploaded successfully"
            })
        else:
            return jsonify({"error": "Invalid file format. Please upload a JSON file."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@gmail_listener_bp.route('/gmail-listener/terminal-output', methods=['GET'])
def get_terminal_output():
    """Get the terminal output of the Gmail Listener script"""
    try:
        if not OUTPUT_LOG_FILE.exists():
            return jsonify({"output": "No output log file found."})
        
        # Read the last 50 lines of the log file
        with open(OUTPUT_LOG_FILE, 'r') as f:
            lines = f.readlines()
            last_lines = lines[-50:] if len(lines) > 50 else lines
            output = ''.join(last_lines)
        
        return jsonify({"output": output})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
