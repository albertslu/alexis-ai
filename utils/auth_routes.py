"""
Authentication routes for AI Clone
"""
import os
import json
import datetime
from flask import Blueprint, request, jsonify, redirect, session, url_for, current_app
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import from file_auth instead of auth
from utils.auth import (
    generate_token,
    create_user_with_credentials,
    get_user_by_id,
    get_user_by_email,
    token_required,
    verify_password,
    hash_password
)
from utils.user_rag_manager import initialize_user_rag

# Create blueprint for routes
auth_bp = Blueprint('auth', __name__)

# Default admin user (for development)
DEFAULT_ADMIN = {
    'id': 'admin',
    'email': 'admin@example.com',
    'name': 'Admin User',
    'role': 'admin'
}

# Configuration
CLIENT_SECRETS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'credentials.json'
)

# Scopes for Google authentication
GOOGLE_AUTH_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

@auth_bp.route('/api/auth/test', methods=['GET'])
def test_auth():
    """Test endpoint to verify auth routes are working"""
    current_app.logger.info("Test auth endpoint called")
    return jsonify({
        'status': 'success',
        'message': 'Auth routes are working correctly',
        'timestamp': str(datetime.datetime.utcnow())
    })

@auth_bp.route('/api/auth/signup', methods=['POST'])
def signup():
    """Signup endpoint for creating a new user account"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        current_app.logger.info(f"Signup attempt for email: {email}")
        
        if not email or not password:
            current_app.logger.error("Signup failed: Email and password are required")
            return jsonify({
                'status': 'error',
                'message': 'Email and password are required'
            }), 400
        
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            current_app.logger.error(f"User already exists with email: {email}")
            return jsonify({
                'status': 'error',
                'message': 'A user with this email already exists'
            }), 400
        
        # Create new user with retry logic for MongoDB errors
        try:
            user_id = create_user_with_credentials(email, password)
            current_app.logger.info(f"Created new user with ID: {user_id}")
            
            # Verify the user was created in MongoDB
            user = get_user_by_id(user_id)
            if not user:
                # If user not found by ID, try to find by email as a fallback
                user = get_user_by_email(email)
                if user:
                    user_id = user['_id']  # Update user_id to match what's in the database
                    current_app.logger.info(f"Found user by email instead of ID. Using ID: {user_id}")
                else:
                    current_app.logger.error(f"User not found in MongoDB after creation: {email}")
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to create user account. Please try again.'
                    }), 500
        except Exception as e:
            current_app.logger.error(f"Error creating user: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Failed to create user account: {str(e)}'
            }), 500
        
        # Generate JWT token
        token = generate_token(user_id)
        current_app.logger.info(f"Generated token for new user: {user_id}")
        
        # Prepare response with complete user data
        response_data = {
            'status': 'success',
            'token': token,
            'user': {
                'id': user_id,
                'email': email,
                'name': user.get('name', email.split('@')[0].replace('.', ' ').title()),
                'model_trained': user.get('model_trained', False),
                'data_initialized': user.get('data_initialized', False),
                'has_fine_tuned_model': user.get('has_fine_tuned_model', False)
            }
        }
        current_app.logger.info(f"Signup successful for user: {email}")

        # Initialize user-specific RAG (only loads default for user_albertlu43)
        try:
            initialize_user_rag(user_id)
        except Exception as e:
            current_app.logger.error(f"Error initializing RAG for user {user_id}: {str(e)}")

        return jsonify(response_data)
    except Exception as e:
        import traceback
        current_app.logger.error(f"Signup error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Signup failed: {str(e)}'
        }), 500

@auth_bp.route('/api/auth/simple-login', methods=['POST'])
def simple_login():
    """Simple login endpoint with password authentication"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        current_app.logger.info(f"Login attempt for email: {email}")
        
        if not email or not password:
            current_app.logger.error("Login failed: Email and password are required")
            return jsonify({
                'status': 'error',
                'message': 'Email and password are required'
            }), 400
        
        # For development, we'll use a simple password check
        # In production, you would use proper password hashing
        
        # Check if user exists
        existing_user = get_user_by_email(email)
        current_app.logger.info(f"User lookup result: {existing_user is not None}")
        
        # User must exist for login
        if not existing_user:
            current_app.logger.error(f"User not found with email: {email}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid email or password'
            }), 401
        
        # Check password using secure verification
        stored_password = existing_user.get('password')
        if not stored_password:
            current_app.logger.error(f"No password stored for user: {email}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid email or password'
            }), 401
            
        # Check if password is still in plain text (for migration period)
        if stored_password == password:
            # Legacy plain text password - hash it now
            hashed_password = hash_password(password)
            # Update the user's password in the database
            from utils.auth import users_collection
            if users_collection:
                users_collection.update_one(
                    {'_id': existing_user['_id']},
                    {'$set': {'password': hashed_password}}
                )
            current_app.logger.info(f"Migrated plain text password for user: {email}")
            password_valid = True
        else:
            # Use bcrypt verification for hashed passwords
            password_valid = verify_password(password, stored_password)
        
        if not password_valid:
            current_app.logger.error(f"Invalid password for user: {email}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid email or password'
            }), 401
        
        user_id = existing_user.get('_id')
        current_app.logger.info(f"User authenticated with ID: {user_id}")
        
        # Generate JWT token
        token = generate_token(user_id)
        current_app.logger.info(f"Generated token for user: {user_id}")
        
        # Get the updated user data
        user = get_user_by_id(user_id)
        if not user:
            current_app.logger.error(f"Failed to retrieve user data for ID: {user_id}")
            user = {'_id': user_id, 'email': email, 'name': email.split('@')[0].replace('.', ' ').title()}
        
        # Prepare response with complete user data
        response_data = {
            'status': 'success',
            'token': token,
            'user': {
                'id': user_id,
                'email': email,
                'name': user.get('name', email.split('@')[0].replace('.', ' ').title()),
                'model_trained': user.get('model_trained', False),
                'data_initialized': user.get('data_initialized', False),
                'has_fine_tuned_model': user.get('has_fine_tuned_model', False)
            }
        }
        current_app.logger.info(f"Login successful for user: {email}")

        # Initialize user-specific RAG (only loads default for user_albertlu43)
        try:
            initialize_user_rag(user_id)
        except Exception as e:
            current_app.logger.error(f"Error initializing RAG for user {user_id}: {str(e)}")

        return jsonify(response_data)
    except Exception as e:
        import traceback
        current_app.logger.error(f"Login error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Login failed: {str(e)}'
        }), 500

@auth_bp.route('/api/auth/google/login', methods=['GET'])
def google_login():
    """Start the Google OAuth flow for user authentication"""
    try:
        # Create the flow using the client secrets file
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=GOOGLE_AUTH_SCOPES,
            redirect_uri='http://localhost:5002/api/oauth/callback/google'
        )
        
        # Generate the authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account'
        )
        
        # Store the state in the session
        session['google_auth_state'] = state
        
        # Redirect to the authorization URL
        return redirect(authorization_url)
    
    except Exception as e:
        current_app.logger.error(f"Error in Google login: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/google/callback', methods=['GET'])
def google_callback():
    """Handle the Google OAuth callback for user authentication"""
    try:
        # Get the state from the session
        state = session.get('google_auth_state')
        
        # Create the flow using the client secrets file
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=GOOGLE_AUTH_SCOPES,
            state=state,
            redirect_uri=url_for('auth.google_callback', _external=True)
        )
        
        # Use the authorization response to fetch the token
        flow.fetch_token(authorization_response=request.url)
        
        # Get the credentials
        credentials = flow.credentials
        
        # Build the service
        service = build('oauth2', 'v2', credentials=credentials)
        
        # Get the user info
        user_info = service.userinfo().get().execute()
        
        # Create or update the user in the database
        google_id = user_info.get('id')
        user_id = f"google_{google_id}"
        
        # Use the create_user_from_google_profile function from auth.py
        from utils.auth import create_user_from_google_profile
        user_id = create_user_from_google_profile(
            google_id,
            {
                'name': user_info.get('name'),
                'email': user_info.get('email'),
                'picture': user_info.get('picture')
            }
        )
        
        # Generate a JWT token
        token = generate_token(user_id)
        current_app.logger.info(f"Generated token for user ID: {user_id}")
        
        # Redirect to the frontend with the token
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        redirect_url = f"{frontend_url}/auth-callback?token={token}"
        current_app.logger.info(f"Redirecting to: {redirect_url}")

        # Initialize user-specific RAG (only loads default for user_albertlu43)
        try:
            initialize_user_rag(user_id)
        except Exception as e:
            current_app.logger.error(f"Error initializing RAG for user {user_id}: {str(e)}")
        
        return redirect(redirect_url)
    
    except Exception as e:
        current_app.logger.error(f"Error in Google callback: {e}")
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        error_redirect = f"{frontend_url}/auth-callback?error={str(e)}"
        return redirect(error_redirect)

@auth_bp.route('/api/oauth/callback/google', methods=['GET'])
def google_oauth_callback():
    """Handle the Google OAuth callback using the same pattern as Gmail OAuth"""
    try:
        # Get the state from the session
        state = session.get('google_auth_state')
        
        # Create the flow using the client secrets file
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=GOOGLE_AUTH_SCOPES,
            state=state,
            redirect_uri='http://localhost:5002/api/oauth/callback/google'
        )
        
        # Use the authorization response to fetch the token
        flow.fetch_token(authorization_response=request.url)
        
        # Get the credentials
        credentials = flow.credentials
        
        # Build the service
        service = build('oauth2', 'v2', credentials=credentials)
        
        # Get the user info
        user_info = service.userinfo().get().execute()
        
        # Create or update the user in the database
        google_id = user_info.get('id')
        user_id = f"google_{google_id}"
        
        # Use the create_user_from_google_profile function from auth.py
        from utils.auth import create_user_from_google_profile
        user_id = create_user_from_google_profile(
            google_id,
            {
                'name': user_info.get('name'),
                'email': user_info.get('email'),
                'picture': user_info.get('picture')
            }
        )
        
        # Generate a JWT token
        token = generate_token(user_id)
        current_app.logger.info(f"Generated token for user ID: {user_id}")
        
        # Redirect to the frontend with the token
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        redirect_url = f"{frontend_url}/auth-callback?token={token}"
        current_app.logger.info(f"Redirecting to: {redirect_url}")

        # Initialize user-specific RAG (only loads default for user_albertlu43)
        try:
            initialize_user_rag(user_id)
        except Exception as e:
            current_app.logger.error(f"Error initializing RAG for user {user_id}: {str(e)}")
        
        return redirect(redirect_url)
    
    except Exception as e:
        current_app.logger.error(f"Error in Google callback: {e}")
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        error_redirect = f"{frontend_url}/auth-callback?error={str(e)}"
        return redirect(error_redirect)

@auth_bp.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user():
    """Get the current user's profile"""
    from flask import g
    
    user = g.user
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Remove sensitive fields and include model training status
    user_data = {
        'id': user.get('_id', user.get('id')),  # MongoDB uses '_id', fallback to 'id'
        'name': user.get('name'),
        'email': user.get('email'),
        'picture': user.get('picture'),
        'role': user.get('role', 'user'),
        'created_at': user.get('created_at'),
        'last_login': user.get('last_login'),
        'model_trained': user.get('model_trained', False),
        'data_initialized': user.get('data_initialized', False),
        'has_fine_tuned_model': user.get('has_fine_tuned_model', False),
        'rag_message_count': user.get('rag_message_count', 0),
        'letta_memory_count': user.get('letta_memory_count', 0)
    }
    
    return jsonify(user_data)

@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout the user"""
    # Clear the session
    session.clear()
    
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Check if the authentication is working"""
    return jsonify({'status': 'Authentication system is working'})
