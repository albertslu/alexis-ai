"""
Authentication module for AI Clone
"""
import os
import json
import uuid
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, g, current_app
from pymongo import MongoClient
import bcrypt

# MongoDB connection
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('DB_NAME', 'ai_clone')

try:
    # Print the MongoDB URI (with password redacted for security)
    uri_parts = MONGO_URI.split('@')
    if len(uri_parts) > 1:
        redacted_uri = uri_parts[0].split(':')[0] + ':***@' + uri_parts[1]
    else:
        redacted_uri = MONGO_URI
    print(f"Attempting to connect to MongoDB at {redacted_uri}")
    
    # Add timeout and updated SSL configuration to prevent handshake errors
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000,
        tlsAllowInvalidCertificates=True,  # Less strict SSL cert verification
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        retryWrites=True,
        w='majority'
    )
    
    # Validate connection
    server_info = client.server_info()
    print(f"Successfully connected to MongoDB: {server_info.get('version')}")
    
    # Get database and collection
    db = client[DB_NAME]
    print(f"Using database: {DB_NAME}")
    
    # List all collections
    collections = db.list_collection_names()
    print(f"Available collections: {collections}")
    
    users_collection = db['users']
    print("Users collection initialized")
    
    # Test inserting and retrieving a document
    test_id = 'test_connection'
    test_doc = {'_id': test_id, 'test': True, 'timestamp': datetime.datetime.utcnow()}
    
    # Check if test document exists and update or insert
    result = users_collection.update_one(
        {'_id': test_id},
        {'$set': test_doc},
        upsert=True
    )
    print(f"Test document upserted: {result.acknowledged}")
    
    # Retrieve the test document
    retrieved = users_collection.find_one({'_id': test_id})
    print(f"Test document retrieved: {retrieved is not None}")
    
    # Remove test document
    users_collection.delete_one({'_id': test_id})
    print("MongoDB connection test completed successfully")
    
except Exception as e:
    import traceback
    print(f"Error connecting to MongoDB: {e}")
    print("Traceback:")
    traceback.print_exc()
    
    # Create a fallback in-memory dictionary for development
    print("Using in-memory user storage as fallback")
    db = None
    users_collection = None
    in_memory_users = {}

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_EXPIRATION = datetime.timedelta(days=7)

def generate_token(user_id):
    """Generate a JWT token for a user"""
    payload = {
        'exp': datetime.datetime.utcnow() + JWT_EXPIRATION,
        'iat': datetime.datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm='HS256'
    )

def decode_token(token):
    """Decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    """Decorator to require a valid JWT token for API calls"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        current_app.logger.info(f"Auth header: {auth_header}")
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            current_app.logger.info(f"Token extracted: {token[:10]}...")
        
        # Check if token exists
        if not token:
            current_app.logger.error("Token is missing")
            return jsonify({'message': 'Token is missing'}), 401
        
        # Decode token
        current_app.logger.info(f"Decoding token: {token[:10]}...")
        user_id = decode_token(token)
        current_app.logger.info(f"Decoded user_id: {user_id}")
        
        if not user_id:
            current_app.logger.error("Token is invalid or expired")
            return jsonify({'message': 'Token is invalid or expired'}), 401
        
        # Get user from database
        # Make sure we're using the correct ID format (MongoDB might be expecting string)
        try:
            user = users_collection.find_one({'_id': user_id})
            if not user:
                # Try with string ID if not found
                user = users_collection.find_one({'_id': str(user_id)})
            if not user:
                return jsonify({'message': 'User not found'}), 401
        except Exception as e:
            current_app.logger.error(f"Error finding user: {str(e)}")
            return jsonify({'message': 'Error finding user'}), 500
        
        # Store user in g object for the current request
        g.user = user
        g.user_id = user.get('_id')
        current_app.logger.info(f"Set g.user_id to: {g.user_id}")
        
        return f(*args, **kwargs)
    
    return decorated

def create_user_from_google_profile(google_id, profile_data):
    """Create a new user from Google profile data"""
    # Check if MongoDB is available
    if users_collection is not None:
        # Check if user already exists
        existing_user = users_collection.find_one({'google_id': google_id})
        if existing_user:
            # Update user profile data
            users_collection.update_one(
                {'_id': existing_user['_id']},
                {'$set': {
                    'name': profile_data.get('name'),
                    'email': profile_data.get('email'),
                    'picture': profile_data.get('picture'),
                    'last_login': datetime.datetime.utcnow()
                }}
            )
            return existing_user['_id']
        
        # Create new user
        user_id = str(uuid.uuid4())
        new_user = {
            '_id': user_id,
            'google_id': google_id,
            'name': profile_data.get('name'),
            'email': profile_data.get('email'),
            'picture': profile_data.get('picture'),
            'created_at': datetime.datetime.utcnow(),
            'last_login': datetime.datetime.utcnow(),
            'role': 'user',
            'status': 'active'
        }
        
        users_collection.insert_one(new_user)
        return user_id
    else:
        # Use in-memory fallback
        # Check if user already exists
        for uid, user in in_memory_users.items():
            if user.get('google_id') == google_id:
                # Update user
                in_memory_users[uid].update({
                    'name': profile_data.get('name'),
                    'email': profile_data.get('email'),
                    'picture': profile_data.get('picture'),
                    'last_login': datetime.datetime.utcnow().isoformat()
                })
                return uid
        
        # Create new user
        user_id = str(uuid.uuid4())
        in_memory_users[user_id] = {
            '_id': user_id,
            'google_id': google_id,
            'name': profile_data.get('name'),
            'email': profile_data.get('email'),
            'picture': profile_data.get('picture'),
            'created_at': datetime.datetime.utcnow().isoformat(),
            'last_login': datetime.datetime.utcnow().isoformat(),
            'role': 'user',
            'status': 'active'
        }
        return user_id

def get_user_by_id(user_id):
    """Get user by ID"""
    if users_collection is not None:
        # Try with the original ID format
        user = users_collection.find_one({'_id': user_id})
        
        # If not found, try with string ID
        if not user:
            user = users_collection.find_one({'_id': str(user_id)})
        
        if user:
            # Remove sensitive fields
            user.pop('google_credentials', None)
            return user
    else:
        # Use in-memory fallback
        user = in_memory_users.get(user_id) or in_memory_users.get(str(user_id))
        if user:
            # Create a copy to avoid modifying the original
            user_copy = user.copy()
            # Remove sensitive fields
            user_copy.pop('google_credentials', None)
            return user_copy
    
    return None

def create_user_with_credentials(email, password):
    """
    Create a new user with email and password
    """
    try:
        # Hash the password before storing
        hashed_password = hash_password(password)
        
        # Connect to MongoDB
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=10000,
            tlsAllowInvalidCertificates=True,  # Less strict SSL cert verification
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            retryWrites=True,
            w='majority'
        )
        db = client[DB_NAME]
        users_collection = db['users']
        
        # Check if user already exists
        existing_user = users_collection.find_one({'email': email})
        
        if existing_user:
            # User already exists
            print(f"User with email {email} already exists with id: {existing_user['_id']}")
            
            # Check if the existing user has a password
            if 'password' not in existing_user or not existing_user['password']:
                # Update the existing user with the new hashed password
                update_result = users_collection.update_one(
                    {'_id': existing_user['_id']},
                    {'$set': {
                        'password': hashed_password,
                        'last_login': datetime.datetime.utcnow(),
                        'user_id': existing_user['_id']  # Ensure user_id is set
                    }}
                )
                print(f"Update result: {update_result.modified_count} document(s) modified")
                
                # Verify the update
                updated_user = users_collection.find_one({'_id': existing_user['_id']})
                print(f"Updated user: {updated_user}")
            
            # Return the existing user's ID regardless of password update
            return existing_user['_id']
        
        # If we get here, user doesn't exist, so create a new one
        # Extract username from email, use it as base for user_id
        username = email.split('@')[0].lower()
        user_id = f"user_{username}"
        
        # Create new user document
        new_user = {
            '_id': user_id,
            'user_id': user_id,  # Add user_id field explicitly
            'email': email,
            'name': username.replace('.', ' ').title(),
            'password': hashed_password,  # Store hashed password
            'created_at': datetime.datetime.utcnow(),
            'last_login': datetime.datetime.utcnow(),
            'role': 'user',
            'status': 'active',
            'model_trained': False,  # New users don't have trained models
            'data_initialized': False,  # Data not initialized yet
            'has_fine_tuned_model': False  # New users don't have fine-tuned models
        }
        
        # Insert the new user with retry logic
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Before inserting, check if this exact user_id already exists
                if users_collection.find_one({'_id': user_id}):
                    # ID already exists, add a numeric suffix rather than a timestamp
                    retry_count += 1
                    user_id = f"user_{username}_{retry_count}"
                    new_user['_id'] = user_id
                    new_user['user_id'] = user_id
                    continue
                
                # Insert the user
                result = users_collection.insert_one(new_user)
                print(f"User created with ID: {result.inserted_id}")
                
                # Verify the insertion
                created_user = users_collection.find_one({'_id': user_id})
                if not created_user:
                    print(f"Warning: User not found after creation: {user_id}")
                    # Try one more time with a different ID
                    retry_count += 1
                    user_id = f"user_{username}_{retry_count}"  # Use sequential suffix instead of timestamp
                    new_user['_id'] = user_id
                    new_user['user_id'] = user_id
                    continue
                
                print(f"Created user: {created_user}")
                
                # Also cleanup any existing user config files with timestamped IDs that might exist
                try:
                    cleanup_user_config_files(username)
                except Exception as e:
                    print(f"Error cleaning up user config files: {str(e)}")
                
                # Run the migration script for the new user
                try:
                    from scripts.migrate_user_data import migrate_user_data
                    migrate_user_data(email)
                    print(f"Migration completed for new user: {email}")
                except Exception as e:
                    print(f"Error running migration for new user: {str(e)}")
                
                return user_id
            except Exception as e:
                print(f"Error inserting new user into MongoDB (attempt {retry_count+1}): {str(e)}")
                
                # If it's a duplicate key error, try again with a sequential suffix
                if 'duplicate key error' in str(e):
                    retry_count += 1
                    user_id = f"user_{username}_{retry_count}"  # Use sequential suffix instead of timestamp
                    print(f"Retrying with unique ID: {user_id}")
                    
                    # Update the user_id in the document
                    new_user['_id'] = user_id
                    new_user['user_id'] = user_id
                else:
                    # For other errors, raise immediately
                    raise
            
            # If we've exhausted all retries
            raise Exception(f"Failed to create user after {max_retries} attempts")
    except Exception as e:
        import traceback
        print(f"Error creating/updating user: {e}")
        traceback.print_exc()
        # Still return a user ID even if there was an error
        return user_id

def get_user_by_email(email):
    """Get user by email"""
    if users_collection is not None:
        return users_collection.find_one({'email': email})
    else:
        # Use in-memory fallback
        for user_id, user in in_memory_users.items():
            if user.get('email') == email:
                return user.copy()
    return None

def get_current_user():
    """Get the current user from the request context"""
    if hasattr(g, 'user'):
        return g.user
    return None

def get_current_user_id():
    """Get the current user ID from the request context"""
    user = get_current_user()
    if user:
        return user['_id']
    return None

def cleanup_user_config_files(username):
    """
    Clean up any duplicate user config files with timestamps.
    Consolidate them into a single, standard-named config file.
    """
    import os
    import json
    import glob
    
    # Get the path to the user configs directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    user_config_dir = os.path.join(base_dir, 'data', 'user_configs')
    
    if not os.path.exists(user_config_dir):
        return  # Nothing to clean up
    
    # Get all config files for this username (both with and without timestamps)
    pattern = os.path.join(user_config_dir, f"user_{username}*_model_config.json")
    config_files = glob.glob(pattern)
    
    if not config_files:
        return  # No files to consolidate
    
    # Target file (standard format without timestamp)
    standard_file = os.path.join(user_config_dir, f"user_{username}_model_config.json")
    
    # If multiple files exist, consolidate them
    if len(config_files) > 1 or (len(config_files) == 1 and config_files[0] != standard_file):
        # Start with an empty config
        consolidated_config = {}
        
        # Read all configs and merge (prioritizing the standard file if it exists)
        for file_path in sorted(config_files, key=lambda x: x == standard_file):
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                    
                # If this config has a fine-tuned model and is marked as trained, use it
                if config.get('trained', False) and config.get('fine_tuned_model'):
                    consolidated_config.update(config)
                    print(f"Using config from {file_path} (has trained model)")
                # Otherwise just update with any available fields
                elif not consolidated_config:
                    consolidated_config.update(config)
                    print(f"Using config from {file_path} (first available)")
            except Exception as e:
                print(f"Error reading config from {file_path}: {e}")
        
        # Write the consolidated config to the standard file
        if consolidated_config:
            try:
                with open(standard_file, 'w') as f:
                    json.dump(consolidated_config, f, indent=2)
                print(f"Created consolidated config at {standard_file}")
                
                # Delete all other files except the standard one
                for file_path in config_files:
                    if file_path != standard_file:
                        try:
                            os.remove(file_path)
                            print(f"Removed duplicate config: {file_path}")
                        except Exception as e:
                            print(f"Error removing duplicate config {file_path}: {e}")
            except Exception as e:
                print(f"Error writing consolidated config: {e}")

# Password hashing utilities
def hash_password(password):
    """Hash a password using bcrypt"""
    # Convert string to bytes
    password_bytes = password.encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for storage
    return hashed.decode('utf-8')

def verify_password(password, hashed_password):
    """Verify a password against its hash"""
    try:
        # Convert strings to bytes
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        # Verify password
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False
