"""
File-based authentication module for AI Clone
"""
import os
import json
import uuid
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, g, current_app

# File paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_EXPIRATION = datetime.timedelta(days=7)

# Initialize users file if it doesn't exist
def init_users_file():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)

# Get all users
def get_users():
    init_users_file()
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # If file is empty or invalid JSON
        return {}

# Save users
def save_users(users):
    init_users_file()
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# Generate a JWT token
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

# Decode a JWT token
def decode_token(token):
    """Decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Create or update a user
def create_or_update_user(user_id, user_data):
    """Create or update a user in the JSON file"""
    users = get_users()
    
    # Update existing user or create new one
    if user_id in users:
        users[user_id].update(user_data)
        users[user_id]['last_login'] = datetime.datetime.utcnow().isoformat()
    else:
        users[user_id] = {
            'id': user_id,
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'password': user_data.get('password'),
            'created_at': datetime.datetime.utcnow().isoformat(),
            'last_login': datetime.datetime.utcnow().isoformat(),
            'role': user_data.get('role', 'user')
        }
    
    save_users(users)
    return user_id

# Get user by ID
def get_user_by_id(user_id):
    """Get user by ID"""
    users = get_users()
    return users.get(user_id)

# Get user by email
def get_user_by_email(email):
    """Get user by email"""
    users = get_users()
    for user_id, user in users.items():
        if user.get('email') == email:
            return user
    return None

# JWT token required decorator
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
        
        # Get user
        user = get_user_by_id(user_id)
        if not user:
            current_app.logger.error(f"User not found: {user_id}")
            return jsonify({'message': 'User not found'}), 401
        
        # Store user in g object for the current request
        g.user = user
        
        return f(*args, **kwargs)
    
    return decorated

# Initialize the users file
init_users_file()
