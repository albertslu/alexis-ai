#!/usr/bin/env python3

"""
OAuth Handler for AI Clone

This module provides a web-based OAuth flow for Gmail and other services,
allowing users to grant access to their accounts without manual credential setup.
"""

import os
import json
import base64
import secrets
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, redirect, url_for, session, make_response
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create blueprint for routes
oauth_bp = Blueprint('oauth', __name__)

# Configuration
CLIENT_SECRETS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'credentials.json'
)

# No need to create a directory since we're using the file in the root directory

# Default scopes
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Google authentication scopes
GOOGLE_AUTH_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

# Dictionary to store user tokens in memory
user_tokens = {}

class OAuthHandler:
    """
    Handles OAuth flows for various services.
    """
    
    @staticmethod
    def get_authorization_url(service, user_id='default', redirect_uri=None):
        """
        Get the authorization URL for a service.
        
        Args:
            service: Service name (e.g., 'gmail', 'google')
            user_id: User identifier
            redirect_uri: Redirect URI after authorization
            
        Returns:
            dict: Authorization URL and state
        """
        if service == 'gmail':
            return OAuthHandler._get_gmail_auth_url(user_id, redirect_uri)
        elif service == 'google':
            return OAuthHandler._get_google_auth_url(user_id, redirect_uri)
        else:
            return {
                'status': 'error',
                'message': f'Unsupported service: {service}'
            }
    
    @staticmethod
    def _get_gmail_auth_url(user_id, redirect_uri):
        """Get Gmail authorization URL."""
        if not os.path.exists(CLIENT_SECRETS_FILE):
            return {
                'status': 'error',
                'message': 'Client secrets file not found. Please configure the application first.'
            }
        
        try:
            # Generate a random state token to prevent CSRF
            state = secrets.token_urlsafe(16)
            
            # Create the flow using the client secrets file
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                scopes=GMAIL_SCOPES,
                redirect_uri=redirect_uri
            )
            
            # Generate the authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='select_account',
                state=state
            )
            
            # Store the flow in the user's session
            session_key = f'flow_{user_id}_gmail'
            user_tokens[session_key] = {
                'flow': flow,
                'state': state,
                'created_at': datetime.now().isoformat()
            }
            
            return {
                'status': 'success',
                'auth_url': auth_url,
                'state': state
            }
        except Exception as e:
            logger.error(f'Error generating Gmail auth URL: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @staticmethod
    def _get_google_auth_url(user_id, redirect_uri):
        """Get Google authentication URL."""
        if not os.path.exists(CLIENT_SECRETS_FILE):
            return {
                'status': 'error',
                'message': 'Client secrets file not found. Please configure the application first.'
            }
        
        try:
            # Generate a random state token to prevent CSRF
            state = secrets.token_urlsafe(16)
            
            # Create the flow using the client secrets file
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                scopes=GOOGLE_AUTH_SCOPES,
                redirect_uri=redirect_uri
            )
            
            # Generate the authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='select_account',
                state=state
            )
            
            # Store the flow in the user's session
            session_key = f'flow_{user_id}_gmail'
            user_tokens[session_key] = {
                'flow': flow,
                'state': state,
                'created_at': datetime.now().isoformat()
            }
            
            return {
                'status': 'success',
                'auth_url': auth_url,
                'state': state
            }
        except Exception as e:
            logger.error(f'Error generating Gmail auth URL: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @staticmethod
    def handle_callback(service, code, state, user_id='default'):
        """
        Handle the OAuth callback.
        
        Args:
            service: Service name (e.g., 'gmail', 'google')
            code: Authorization code
            state: State token
            user_id: User identifier
            
        Returns:
            dict: Result of the callback
        """
        if service == 'gmail':
            return OAuthHandler._handle_gmail_callback(code, state, user_id)
        elif service == 'google':
            return OAuthHandler._handle_google_callback(code, state, user_id)
        else:
            return {
                'status': 'error',
                'message': f'Unsupported service: {service}'
            }
    
    @staticmethod
    def _handle_gmail_callback(code, state, user_id):
        """Handle Gmail OAuth callback."""
        session_key = f'flow_{user_id}_gmail'
        
        logger.info(f"Gmail callback handler for user_id: {user_id}")
        logger.info(f"Looking for session key: {session_key}")
        logger.info(f"Available session keys: {list(user_tokens.keys())}")
        
        if session_key not in user_tokens:
            logger.error(f"No active authorization flow found for session key: {session_key}")
            return {
                'status': 'error',
                'message': 'No active authorization flow found.'
            }
        
        stored_flow = user_tokens[session_key]['flow']
        stored_state = user_tokens[session_key]['state']
        
        logger.info(f"Stored state: {stored_state}")
        logger.info(f"Received state: {state}")
        
        # Verify state to prevent CSRF
        if state != stored_state:
            logger.error(f"Invalid state parameter. Expected: {stored_state}, Got: {state}")
            return {
                'status': 'error',
                'message': 'Invalid state parameter.'
            }
        
        try:
            logger.info(f"Exchanging authorization code for credentials...")
            # Exchange the authorization code for credentials
            stored_flow.fetch_token(code=code)
            credentials = stored_flow.credentials
            
            logger.info(f"Successfully obtained credentials. Token valid until: {credentials.expiry}")
            
            # Store the credentials for Gmail access
            store_result = OAuthHandler.store_credentials(user_id, 'gmail', credentials)
            logger.info(f"Credentials storage result: {store_result}")
            
            # Verify the credentials were stored correctly
            token_key = f'{user_id}_gmail_token'
            if token_key in user_tokens:
                logger.info(f"Verified credentials were stored with key: {token_key}")
            else:
                logger.error(f"Failed to store credentials with key: {token_key}")
            
            # Clean up the flow
            del user_tokens[session_key]
            
            # Also use this for authentication if coming from login page
            auth_purpose = request.args.get('auth_purpose')
            if auth_purpose == 'login':
                # Get the user info from Google
                service = build('oauth2', 'v2', credentials=credentials)
                user_info = service.userinfo().get().execute()
                
                # Import auth functions to avoid circular imports
                from utils.auth import create_user_from_google_profile, generate_token
                
                # Create or update the user in MongoDB
                user_id = create_user_from_google_profile(
                    user_info.get('id'),
                    {
                        'email': user_info.get('email'),
                        'name': user_info.get('name'),
                        'picture': user_info.get('picture')
                    }
                )
                
                # Generate a JWT token
                token = generate_token(user_id)
                
                return {
                    'status': 'success',
                    'token': token
                }
            
            return {
                'status': 'success',
                'message': 'Successfully authenticated with Gmail.'
            }
        except Exception as e:
            logger.error(f"Error handling Gmail callback: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @staticmethod
    def _handle_google_callback(code, state, user_id):
        """Handle Google OAuth callback for user authentication."""
        session_key = f'flow_{user_id}_gmail'  # Using the same key pattern for simplicity
        
        if session_key not in user_tokens:
            return {
                'status': 'error',
                'message': 'No active authorization flow found.'
            }
        
        stored_flow = user_tokens[session_key]['flow']
        stored_state = user_tokens[session_key]['state']
        
        # Verify state to prevent CSRF
        if state != stored_state:
            return {
                'status': 'error',
                'message': 'Invalid state parameter.'
            }
        
        try:
            # Exchange the authorization code for credentials
            stored_flow.fetch_token(code=code)
            credentials = stored_flow.credentials
            
            # Get the user info from Google
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            # Import auth functions to avoid circular imports
            from utils.auth import create_user_from_google_profile, generate_token
            
            # Create or update the user in MongoDB
            user_id = create_user_from_google_profile(
                user_info.get('id'),
                {
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture')
                }
            )
            
            # Generate a JWT token for authentication
            token = generate_token(user_id)
            
            # Clean up the flow
            del user_tokens[session_key]
            
            return {
                'status': 'success',
                'message': 'Successfully authenticated with Google.',
                'token': token,
                'user': {
                    'id': user_id,
                    'email': user_info.get('email'),
                    'name': user_info.get('name')
                }
            }
        except Exception as e:
            logger.error(f'Error handling Google callback: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @staticmethod
    def store_credentials(user_id, service, credentials):
        """
        Store user credentials in memory.
        
        Args:
            user_id: User identifier
            service: Service name
            credentials: OAuth credentials
            
        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Storing credentials for user_id: {user_id}, service: {service}")
            
            # Convert credentials to a serializable format
            creds_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            logger.info(f"Credentials data prepared: token_uri={creds_data['token_uri']}, scopes={creds_data['scopes']}")
            logger.info(f"Token expiry: {creds_data['expiry']}")
            
            # Store in memory cache
            token_key = f'{user_id}_{service}_token'
            user_tokens[token_key] = creds_data
            
            logger.info(f"Credentials successfully stored in memory with key: {token_key}")
            
            # Verify memory storage was successful
            if token_key in user_tokens:
                stored_data = user_tokens[token_key]
                if stored_data.get('token') == credentials.token:
                    logger.info(f"Credentials successfully stored in memory with key: {token_key}")
                    
                    # For debugging, list all available tokens
                    logger.info(f"All available token keys after storage: {list(user_tokens.keys())}")
                    return True
                else:
                    logger.error(f"Credentials memory storage verification failed - token mismatch")
                    return False
            else:
                logger.error(f"Credentials memory storage verification failed - key not found")
                return False
        except Exception as e:
            logger.error(f'Error storing credentials: {str(e)}')
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def get_credentials(user_id, service):
        """
        Get stored credentials for a user from memory cache.
        
        Args:
            user_id: User identifier
            service: Service name
            
        Returns:
            Credentials: OAuth credentials or None
        """
        token_key = f'{user_id}_{service}_token'
        
        logger.info(f"Looking for credentials with key: {token_key}")
        logger.info(f"Available token keys in memory: {list(user_tokens.keys())}")
        
        creds_data = None
        
        # First try to get from memory cache
        if token_key in user_tokens:
            logger.info(f"Found credentials in memory cache for {token_key}")
            creds_data = user_tokens[token_key]
        
        if not creds_data:
            logger.warning(f'No {service} credentials found for user {user_id}')
            return None
        
        try:
            logger.info(f"Found credentials data for {token_key}")
            
            # Parse expiry if it exists
            expiry = None
            if creds_data.get('expiry'):
                expiry = datetime.fromisoformat(creds_data['expiry'])
                logger.info(f"Credential expiry: {expiry}")
            
            # Create credentials object
            credentials = Credentials(
                token=creds_data['token'],
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data['token_uri'],
                client_id=creds_data['client_id'],
                client_secret=creds_data['client_secret'],
                scopes=creds_data['scopes'],
                expiry=expiry
            )
            
            # Check if credentials are expired and refresh if needed
            if credentials.expired and credentials.refresh_token:
                logger.info(f"Refreshing expired credentials for {token_key}")
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
                OAuthHandler.store_credentials(user_id, service, credentials)
                logger.info(f"Credentials refreshed successfully")
            
            return credentials
        except Exception as e:
            logger.error(f'Error creating credentials object: {str(e)}')
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def revoke_access(user_id, service):
        """
        Revoke access for a service.
        
        Args:
            user_id: User identifier
            service: Service name
            
        Returns:
            dict: Result of the revocation
        """
        token_key = f'{user_id}_{service}_token'
        
        if token_key not in user_tokens:
            return {
                'status': 'error',
                'message': f'No {service} credentials found for user {user_id}'
            }
        
        try:
            # Remove the credentials
            del user_tokens[token_key]
            
            return {
                'status': 'success',
                'message': f'Successfully revoked {service} access for user {user_id}'
            }
        except Exception as e:
            logger.error(f'Error revoking access: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @staticmethod
    def check_auth_status(user_id, service):
        """
        Check if a user is authenticated for a service.
        
        Args:
            user_id: User identifier
            service: Service name
            
        Returns:
            dict: Authentication status
        """
        token_key = f'{user_id}_{service}_token'
        
        logger.info(f"Checking auth status for user_id: {user_id}, service: {service}")
        logger.info(f"Looking for token key: {token_key}")
        logger.info(f"Available token keys: {list(user_tokens.keys())}")
        
        if token_key not in user_tokens:
            logger.warning(f"No {service} credentials found for user {user_id}")
            return {
                'authenticated': False,
                'message': f'Not authenticated with {service}'
            }
        
        try:
            creds_data = user_tokens[token_key]
            logger.info(f"Found credentials data for {token_key}")
            
            # Check if credentials have expired
            if creds_data.get('expiry'):
                expiry = datetime.fromisoformat(creds_data['expiry'])
                logger.info(f"Credential expiry: {expiry}, current time: {datetime.now()}")
                if expiry < datetime.now() and not creds_data.get('refresh_token'):
                    logger.warning(f"Credentials for {service} have expired and no refresh token is available")
                    return {
                        'authenticated': False,
                        'message': f'{service} credentials have expired'
                    }
            
            # For Gmail, verify that we can actually initialize the API service
            if service == 'gmail':
                try:
                    # Get credentials object
                    credentials = OAuthHandler.get_credentials(user_id, service)
                    if not credentials:
                        logger.error(f"Failed to get credentials object for {user_id}")
                        return {
                            'authenticated': False,
                            'message': f'Failed to retrieve valid {service} credentials'
                        }
                    
                    # Try to initialize the service to verify credentials work
                    logger.info(f"Testing Gmail API service initialization with credentials")
                    service_obj = build('gmail', 'v1', credentials=credentials)
                    
                    # Try a simple API call to verify credentials
                    profile = service_obj.users().getProfile(userId='me').execute()
                    logger.info(f"Successfully verified Gmail API credentials by retrieving profile: {profile.get('emailAddress')}")
                    
                    return {
                        'authenticated': True,
                        'message': f'Authenticated with {service}',
                        'scopes': creds_data.get('scopes', []),
                        'email': profile.get('emailAddress'),
                        'token': creds_data  # Include the token in the response
                    }
                except Exception as e:
                    logger.error(f"Error verifying Gmail API credentials: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return {
                        'authenticated': False,
                        'message': f'Error verifying {service} credentials: {str(e)}'
                    }
            
            # For other services
            return {
                'authenticated': True,
                'message': f'Authenticated with {service}',
                'scopes': creds_data.get('scopes', [])
            }
        except Exception as e:
            logger.error(f'Error checking auth status: {str(e)}')
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'authenticated': False,
                'message': str(e)
            }
            
    # This method is no longer needed as we're using the existing EmailIntegration functionality

# Register routes
@oauth_bp.route('/api/oauth/authorize/<service>', methods=['GET'])
def authorize(service):
    """Start the OAuth flow for a service."""
    # DIAGNOSTIC LOGGING - Start
    print("\n" + "="*80)
    print(f"OAUTH AUTHORIZATION STARTED FOR SERVICE: {service}")
    print(f"Request method: {request.method}")
    print(f"Request args: {request.args}")
    print(f"Request headers: {dict(request.headers)}")
    print("="*80 + "\n")
    # DIAGNOSTIC LOGGING - End
    
    user_id = request.args.get('user_id', 'default')
    redirect_uri = request.args.get('redirect_uri')
    is_desktop_app = request.args.get('desktop_app', 'false').lower() == 'true'
    use_system_browser = request.args.get('use_system_browser', 'false').lower() == 'true'
    
    # Store desktop app parameters in a session variable keyed by user_id
    # This will be retrieved during the callback
    session_key = f'oauth_params_{user_id}'
    user_tokens[session_key] = {
        'is_desktop_app': is_desktop_app,
        'use_system_browser': use_system_browser,
        'created_at': datetime.now().isoformat()
    }
    
    # Log for debugging
    print(f"OAuth authorize for user_id: {user_id}, desktop_app: {is_desktop_app}, system_browser: {use_system_browser}")
    print(f"Stored session params at key: {session_key}")
    print(f"Current user_tokens keys: {list(user_tokens.keys())}")
    
    result = OAuthHandler.get_authorization_url(service, user_id, redirect_uri)
    
    # DIAGNOSTIC LOGGING - Authorization URL
    print(f"Authorization URL: {result.get('auth_url')}")
    print(f"State token: {result.get('state')}")
    
    # Store the state token for later verification
    if result.get('state'):
        state_key = f'state_{result["state"]}'
        user_tokens[state_key] = {
            'user_id': user_id,
            'service': service,
            'is_desktop_app': is_desktop_app,
            'use_system_browser': use_system_browser,
            'created_at': datetime.now().isoformat()
        }
        print(f"Stored state data at key: {state_key}")
        print(f"State data: {user_tokens[state_key]}")
    
    if result['status'] == 'success':
        return redirect(result['auth_url'])
    else:
        return jsonify(result)

@oauth_bp.route('/api/oauth/callback/<service>', methods=['GET', 'POST', 'OPTIONS'])
def callback(service):
    """Handle the OAuth callback for a service."""
    # DIAGNOSTIC LOGGING - Start
    print("\n" + "="*80)
    print(f"OAUTH CALLBACK RECEIVED FOR SERVICE: {service}")
    print(f"Request method: {request.method}")
    print(f"Request args: {request.args}")
    print(f"Request form: {request.form}")
    print(f"Request headers: {dict(request.headers)}")
    print("="*80 + "\n")
    # DIAGNOSTIC LOGGING - End
    
    # For OPTIONS requests (CORS preflight)
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        return response
        
    # Extract parameters from either GET or POST
    code = request.args.get('code') or request.form.get('code')
    state = request.args.get('state') or request.form.get('state')
    user_id = request.args.get('user_id', 'default') or request.form.get('user_id', 'default')
    
    print(f"OAuth callback received for service: {service}")
    print(f"Initial user_id: {user_id}, state: {state}")
    print(f"Request args: {request.args}")
    
    
    # Try to extract user_id from the state token if not provided directly
    if user_id == 'default' and state:
        # The state might contain encoded information about the user
        try:
            # Look for user_id in the flow session data
            print(f"Searching for user_id in flow session data...")
            found = False
            for key in user_tokens:
                print(f"Checking key: {key}")
                if key.startswith('flow_') and key.endswith('_gmail') and user_tokens[key].get('state') == state:
                    user_id = key.replace('flow_', '').replace('_gmail', '')
                    print(f"Extracted user_id from state: {user_id}")
                    found = True
                    break
            if not found:
                print(f"Could not find matching flow session for state: {state}")
                print(f"Available keys in user_tokens: {list(user_tokens.keys())}")
        except Exception as e:
            print(f"Error extracting user_id from state: {str(e)}")
    
    # Detect desktop app based on the referrer or origin
    # If the request came from api.aiclone.space, it's likely from the desktop app
    referrer = request.headers.get('Referer', '')
    origin = request.headers.get('Origin', '')
    
    # DIAGNOSTIC LOGGING - Desktop app detection
    print(f"Referrer: {referrer}")
    print(f"Origin: {origin}")
    print(f"Looking for desktop app indicators...")
    
    is_desktop_app = False
    use_system_browser = False
    
    # Check if this is a desktop app request based on session data
    desktop_app_param = request.args.get('desktop_app')
    system_browser_param = request.args.get('use_system_browser')
    
    print(f"desktop_app param: {desktop_app_param}")
    print(f"use_system_browser param: {system_browser_param}")
    
    # Check session data for desktop app flags
    oauth_params_key = f'oauth_params_{user_id}'
    if oauth_params_key in user_tokens:
        oauth_params = user_tokens.get(oauth_params_key, {})
        session_desktop_app = oauth_params.get('is_desktop_app', False)
        session_system_browser = oauth_params.get('use_system_browser', False)
        print(f"Session data for {oauth_params_key}: {oauth_params}")
        print(f"Session desktop_app: {session_desktop_app}")
        print(f"Session system_browser: {session_system_browser}")
        
        if session_desktop_app:
            is_desktop_app = True
            use_system_browser = session_system_browser
            print(f"Using desktop app flags from session")
    
    if 'api.aiclone.space' in referrer or 'api.aiclone.space' in origin:
        print(f"Detected desktop app request based on referrer/origin")
        is_desktop_app = True
        use_system_browser = True
    
    print(f"Final user_id: {user_id}")
    print(f"Is desktop app: {is_desktop_app}, Use system browser: {use_system_browser}")
    
    
    if not code:
        print("No authorization code provided")
        return jsonify({
            'status': 'error',
            'message': 'No authorization code provided'
        })
    
    
    print(f"Handling callback for service: {service}, user_id: {user_id}")
    result = OAuthHandler.handle_callback(service, code, state, user_id)
    print(f"Callback result: {result}")
    
    # Handle different services differently
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    
    # Check if this is for authentication (login) or data access
    auth_purpose = request.args.get('auth_purpose')
    
    if auth_purpose == 'login':
        # For authentication, redirect to auth-callback with the token
        if result['status'] == 'success' and 'token' in result:
            print(f"Authentication successful, redirecting to auth-callback with token")
            return redirect(f'{frontend_url}/auth-callback?token={result["token"]}')
        else:
            error_msg = result.get('message', 'Authentication failed')
            print(f"Authentication failed: {error_msg}")
            return redirect(f'{frontend_url}/login?error={error_msg}')
    else:
        # For data access (Gmail, etc.)
        status = 'success' if result['status'] == 'success' else 'error'
        
        print(f"Data access result: {status}")
        print(f"Determining response type based on client: desktop_app={is_desktop_app}, system_browser={use_system_browser}")
        
        if is_desktop_app:
            if use_system_browser:
                # For system browser in desktop app, return a page that closes itself
                # and communicates back to the desktop app via localStorage
                print(f"Returning self-closing page for desktop app with system browser")
                return f"""
                <html>
                    <head>
                        <title>Authentication {status.capitalize()}</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                            h1 {{ color: #4285f4; }}
                            .success {{ color: #34a853; font-weight: bold; }}
                            .container {{ max-width: 600px; margin: 0 auto; }}
                            .countdown {{ font-size: 14px; margin-top: 20px; color: #666; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Authentication {status.capitalize()}</h1>
                            {'<p class="success">You have successfully authenticated with ' + service + '!</p>' if status == 'success' else '<p class="error">There was an error authenticating with ' + service + '.</p><p>Error message: ' + result.get('message', 'Unknown error') + '</p>'}
                            <p>You can close this window and return to the application.</p>
                            <p>The app will continue processing your data.</p>
                            <p class="countdown">This window will close automatically in <span id="countdown">5</span> seconds.</p>
                        </div>
                        <script>
                            // Store the OAuth result in localStorage for the desktop app to retrieve
                            try {{
                                // Set a flag that the desktop app can check
                                localStorage.setItem('aiclone_oauth_completed', 'true');
                                localStorage.setItem('aiclone_oauth_service', '{service}');
                                localStorage.setItem('aiclone_oauth_status', '{status}');
                                localStorage.setItem('aiclone_oauth_timestamp', Date.now().toString());
                                
                                // Also try to notify the opener window if it exists
                                if (window.opener) {{
                                    try {{
                                        window.opener.postMessage({{
                                            type: 'aiclone_oauth_result',
                                            service: '{service}',
                                            status: '{status}',
                                            timestamp: Date.now()
                                        }}, '*');
                                        console.log('Sent postMessage to opener');
                                    }} catch (e) {{
                                        console.error('Error sending postMessage:', e);
                                    }}
                                }}
                            }} catch (e) {{
                                console.error('Error setting localStorage:', e);
                            }}
                            
                            // Countdown and close window
                            let countdown = 5;
                            const countdownElement = document.getElementById('countdown');
                            const countdownInterval = setInterval(() => {{
                                countdown--;
                                countdownElement.textContent = countdown;
                                if (countdown <= 0) {{
                                    clearInterval(countdownInterval);
                                    window.close();
                                }}
                            }}, 1000);
                            
                            // Close the window after a delay
                            setTimeout(() => {{
                                window.close();
                            }}, 5000);
                        </script>
                    </body>
                </html>
                """
            else:
                # For embedded webview in desktop app, use the custom protocol
                print(f"Returning custom protocol page for desktop app with embedded webview")
                return f"""
                <html>
                    <head>
                        <title>Authentication Successful</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                            h1 {{ color: #4285f4; }}
                            .success {{ color: #34a853; font-weight: bold; }}
                            .container {{ max-width: 600px; margin: 0 auto; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Authentication Successful</h1>
                            <p class="success">You have successfully authenticated with {service}!</p>
                            <p>You can close this window and return to the application.</p>
                            <p>The app will continue processing your data.</p>
                        </div>
                        <script>
                            // This will be caught by the desktop app's webContents
                            window.onload = function() {{
                                 try {{
                                    console.log('OAuth callback completed, preparing to notify desktop app');
                                    
                                    // First, send a ping to keep the backend alive
                                    fetch('/api/test', {{ method: 'GET' }})
                                        .then(function(response) {{
                                            console.log('Backend ping successful');
                                            
                                            // Use window.open instead of location.href to prevent backend termination
                                            // This creates a new window without terminating the current page/request
                                            var protocolUrl = 'ai-clone://oauth-callback?service={service}&status={status}';
                                            console.log('Opening protocol URL in new window:', protocolUrl);
                                            
                                            // Create a small popup that will be caught by Electron but won't terminate this page
                                            var popup = window.open(protocolUrl, 'oauth_complete', 
                                                'width=100,height=100,left=0,top=0');
                                            
                                            // Keep pinging the backend to ensure it stays alive
                                            var pingInterval = setInterval(function() {{
                                                fetch('/api/test', {{ method: 'GET' }})
                                                    .then(function(response) {{
                                                        console.log('Backend still alive');
                                                    }})
                                                    .catch(function(error) {{
                                                        console.error('Backend ping failed:', error);
                                                    }});
                                            }}, 1000);
                                            
                                            // After 10 seconds, stop pinging
                                            setTimeout(function() {{
                                                clearInterval(pingInterval);
                                                // Close the popup if it's still open
                                                if (popup && !popup.closed) {{
                                                    popup.close();
                                                }}
                                                console.log('Finished OAuth callback process');
                                            }}, 10000);
                                        }})
                                        .catch(function(error) {{
                                            console.error('Backend ping failed:', error);
                                            // Fallback to direct navigation as last resort
                                            window.open('ai-clone://oauth-callback?service={service}&status={status}', 
                                                'oauth_complete', 'width=100,height=100');
                                        }});
                                 }} catch (e) {{
                                    console.error('Error in OAuth callback:', e);
                                    // Fallback attempt with direct navigation
                                    window.open('ai-clone://oauth-callback?service={service}&status={status}', 
                                        'oauth_complete', 'width=100,height=100');
                                 }}
                            }};
                        </script>
                    </body>
                </html>
                """
        else:
            # For web app, redirect to training page
            print(f"Redirecting to web app training page: {frontend_url}/training?service={service}&status={status}")
            return redirect(f'{frontend_url}/training?service={service}&status={status}')

@oauth_bp.route('/api/oauth/status/<service>', methods=['GET'])
def auth_status(service):
    """Check if the user is authenticated for a service."""
    user_id = request.args.get('user_id', 'default')
    
    result = OAuthHandler.check_auth_status(user_id, service)
    
    return jsonify(result)

@oauth_bp.route('/api/oauth/revoke/<service>', methods=['POST'])
def revoke(service):
    """Revoke access for a service."""
    user_id = request.args.get('user_id', 'default')
    
    result = OAuthHandler.revoke_access(user_id, service)
    
    return jsonify(result)

@oauth_bp.route('/api/oauth/gmail/extract', methods=['POST'])
def extract_emails():
    """Extract emails using OAuth credentials."""
    data = request.json
    user_id = data.get('user_id', 'default')
    days = int(data.get('days', 30))
    max_count = int(data.get('max_count', 100))
    token = data.get('token')  # Get token from request payload
    
    logger.info(f"Starting email extraction for user_id: {user_id}, days: {days}, max_count: {max_count}, token: {'provided' if token else 'not provided'}")
    
    # Use the existing EmailIntegration functionality
    try:
        from utils.email_integration import get_email_integration
        from utils.message_listener import get_message_listener_service
        
        logger.info("Successfully imported required modules")
        
        # Get message listener service without passing user_id
        try:
            message_listener_service = get_message_listener_service()
            logger.info("Successfully obtained message_listener_service")
        except Exception as e:
            logger.error(f"Error getting message_listener_service: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"Error getting message listener service: {str(e)}"
            })
        
        # If token is provided, store it for this user
        if token:
            try:
                logger.info(f"Storing Gmail token for user_id: {user_id}")
                store_token(user_id, 'gmail', token)
                logger.info("Successfully stored Gmail token")
            except Exception as e:
                logger.error(f"Error storing Gmail token: {str(e)}")
                # Continue anyway, as we'll try to use the token directly
        
        # Use get_email_integration to get or create EmailIntegration instance
        try:
            logger.info(f"Getting EmailIntegration with user_id: {user_id}")
            email_integration = get_email_integration(
                message_listener_service=message_listener_service,
                user_id=user_id,
                token=token  # Pass the token directly to EmailIntegration
            )
            logger.info("Successfully got EmailIntegration instance")
        except Exception as e:
            logger.error(f"Error getting EmailIntegration: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"Error getting email integration: {str(e)}"
            })
        
        # Extract emails using the existing method
        try:
            logger.info(f"Extracting emails with max_count: {max_count}, days: {days}")
            result = email_integration.extract_sent_emails(max_count, days)
            logger.info(f"Email extraction result: {result}")
        except Exception as e:
            logger.error(f"Error extracting emails: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"Error extracting emails: {str(e)}"
            })
        
        # Format the result to match the expected format
        return jsonify({
            'success': result.get('status') == 'success',
            'message': result.get('message', ''),
            'email_count': result.get('extracted_count', 0)
        })
    except Exception as e:
        logger.error(f"Error extracting emails: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error extracting emails: {str(e)}"
        })

@oauth_bp.route('/api/oauth/gmail/token', methods=['GET'])
def get_gmail_token():
    """Get the Gmail token for a user."""
    user_id = request.args.get('user_id', 'default')
    
    logger.info(f"Getting Gmail token for user_id: {user_id}")
    
    token_key = f'{user_id}_gmail_token'
    logger.info(f"Looking for token key: {token_key}")
    logger.info(f"Available token keys: {list(user_tokens.keys())}")
    
    if token_key not in user_tokens:
        logger.warning(f"No Gmail token found for user {user_id}")
        return jsonify({
            'success': False,
            'message': 'No Gmail token found'
        })
    
    try:
        token = user_tokens[token_key]
        logger.info(f"Found Gmail token for user {user_id}")
        
        return jsonify({
            'success': True,
            'token': token
        })
    except Exception as e:
        logger.error(f"Error getting Gmail token: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting Gmail token: {str(e)}"
        })

def store_token(user_id, service, token):
    """Store a token in memory for the given user and service."""
    token_key = f'{user_id}_{service}_token'
    user_tokens[token_key] = token
    logger.info(f"Stored token in memory with key: {token_key}")
    
    # Optional: write to a local file for persistence between restarts
    try:
        token_dir = os.path.join(os.path.expanduser('~'), '.ai-clone', 'tokens')
        os.makedirs(token_dir, exist_ok=True)
        token_file = os.path.join(token_dir, f'{token_key}.txt')
        with open(token_file, 'w') as f:
            f.write(token)
        logger.info(f"Stored token to file: {token_file}")
    except Exception as e:
        logger.warning(f"Could not store token to file: {str(e)}")
