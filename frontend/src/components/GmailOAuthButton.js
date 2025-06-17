import React, { useState, useEffect } from 'react';
import { Button, CircularProgress, Typography, Box, Alert } from '@mui/material';
import EmailIcon from '@mui/icons-material/Email';
import axios from 'axios';  
import { useAuth } from '../contexts/AuthContext';

/**
 * Gmail OAuth Button Component
 * 
 * This component provides a button for users to authenticate with Gmail
 * using OAuth, allowing the AI clone to access their emails for training
 * and autoresponse functionality.
 */
const GmailOAuthButton = ({ onAuthSuccess, userId = 'default' }) => {
  const [loading, setLoading] = useState(false);
  const [authStatus, setAuthStatus] = useState({ authenticated: false, message: '' });
  const [error, setError] = useState('');
  const [authInProgress, setAuthInProgress] = useState(false);
  const { currentUser } = useAuth(); // Get the current user from AuthContext

  // Check if the user is already authenticated with Gmail
  useEffect(() => {
    checkAuthStatus();
  }, []);

  // Check authentication status
  const checkAuthStatus = async () => {
    try {
      setLoading(true);
      
      // Get the JWT token from localStorage
      const token = localStorage.getItem('token');
      
      if (!token) {
        console.error('No JWT token found - user is not authenticated');
        setError('Unable to check authentication status. Please ensure you are logged in.');
        return;
      }
      
      // The user ID should be available from the currentUser context
      if (!currentUser) {
        console.error('No user data available in AuthContext');
        setError('Unable to check authentication status. Please try logging out and back in.');
        return;
      }
      
      // Try to get the user ID from either _id or id field
      const actualUserId = currentUser._id || currentUser.id;
      
      if (!actualUserId) {
        console.error('No user ID available in AuthContext', currentUser);
        setError('Unable to check authentication status. Please try logging out and back in.');
        return;
      }
      
      console.log('Checking auth status for user:', actualUserId);
      
      // Always use the production server for OAuth status checks
      // This ensures authentication state is maintained properly
      const productionApiUrl = 'https://api.aiclone.space';
      const fullUrl = `${productionApiUrl}/api/oauth/status/gmail?user_id=${actualUserId}`;
      console.log('Using production API for OAuth status check:', fullUrl);
      const response = await axios.get(fullUrl);
      console.log('OAuth status response:', JSON.stringify(response.data, null, 2));
      setAuthStatus(response.data);
      
      // If authenticated, sync the token to localStorage for local extraction
      if (response.data.authenticated) {
        try {
          console.log('User is authenticated, syncing token to localStorage');
          console.log('Response data keys:', Object.keys(response.data));
          
          // Check if the token is directly in the status response (it should be!)
          if (response.data.token) {
            console.log('Token found directly in status response, storing in localStorage');
            localStorage.setItem('gmail_token', JSON.stringify(response.data.token));
            console.log('Successfully stored token in localStorage for local extraction');
          } else {
            console.log('No token in status response - this is unexpected');
            
            // For local extraction, still try the token endpoint as fallback
            const isDesktopApp = window.navigator.userAgent.includes('Electron');
            
            if (isDesktopApp) {
              try {
                // Try checking the local backend for the token 
                const localBackendUrl = window.OAUTH_BASE_URL || 'http://localhost:5002';
                console.log(`Checking if local backend has token: ${localBackendUrl}/api/oauth/status/gmail?user_id=${actualUserId}`);
                
                const localResponse = await axios.get(`${localBackendUrl}/api/oauth/status/gmail?user_id=${actualUserId}`);
                if (localResponse.data.authenticated && localResponse.data.token) {
                  console.log('Found token in local backend, storing in localStorage');
                  localStorage.setItem('gmail_token', JSON.stringify(localResponse.data.token));
                } else {
                  console.log('Local backend does not have token, may need to reconnect Gmail');
                }
              } catch (localError) {
                console.error('Error checking local token status:', localError);
              }
            }
          }
        } catch (tokenError) {
          console.error('Error handling token:', tokenError);
        }
      } else if (response.data.authenticated) {
        console.log('User is authenticated but no token information available');
      }
      
      // Call onAuthSuccess with the authentication status if provided
      if (onAuthSuccess && response.data.authenticated) {
        onAuthSuccess(true);
      }
    } catch (error) {
      console.error('Error checking Gmail auth status:', error);
      setError('Failed to check Gmail authentication status.');
    } finally {
      setLoading(false);
    }
  };

  // Handle OAuth result when user returns from Google auth page
  useEffect(() => {
    const handleOAuthResult = () => {
      const urlParams = new URLSearchParams(window.location.search);
      const status = urlParams.get('status');
      const service = urlParams.get('service');
      
      if (service === 'gmail') {
        if (status === 'success') {
          console.log('OAuth success detected, setting authenticated state');
          setAuthStatus({ authenticated: true, message: 'Successfully authenticated with Gmail!' });
          if (onAuthSuccess) onAuthSuccess(true);
          
          // Clean up URL parameters
          window.history.replaceState({}, document.title, window.location.pathname);
          
          // Add a short delay before checking auth status to ensure the state is properly registered
          setTimeout(() => {
            console.log('Checking auth status after successful OAuth');
            checkAuthStatus();
          }, 1000);
        } else if (status === 'error') {
          setError('Failed to authenticate with Gmail. Please try again.');
          
          // Clean up URL parameters
          window.history.replaceState({}, document.title, window.location.pathname);
        }
      }
    };
    
    handleOAuthResult();
  }, [onAuthSuccess]);

  // Start the OAuth flow
  const handleAuth = () => {
    setAuthInProgress(true);
    
    // Check if running in Electron
    const isDesktopApp = window.navigator.userAgent.includes('Electron');
    
    // Get the JWT token from localStorage
    const token = localStorage.getItem('token');
    
    if (!token) {
      console.error('No JWT token found - user is not authenticated');
      setError('Authentication failed. Please ensure you are logged in before connecting Gmail.');
      setAuthInProgress(false);
      return;
    }
    
    // The user ID should be available from the currentUser context
    if (!currentUser) {
      console.error('No user data available in AuthContext');
      setError('Authentication failed. Please try logging out and back in.');
      setAuthInProgress(false);
      return;
    }
    
    // Try to get the user ID from either _id or id field
    const actualUserId = currentUser._id || currentUser.id;
    
    if (!actualUserId) {
      console.error('No user ID available in AuthContext', currentUser);
      setError('Authentication failed. Please try logging out and back in.');
      setAuthInProgress(false);
      return;
    }
    
    console.log('Starting OAuth flow for user:', actualUserId);
    
    if (isDesktopApp && window.electron) {
      // In Electron, use IPC to request OAuth through the system browser
      console.log('Requesting Gmail OAuth via Electron IPC');
      window.electron.startGmailOAuth(actualUserId)
        .then(result => {
          console.log('OAuth result:', result);
          setAuthInProgress(false);
          checkAuthStatus();
        })
        .catch(error => {
          console.error('OAuth error:', error);
          setAuthInProgress(false);
          setError('Authentication failed. Please try again.');
        });
    } else {
      // For web app, use the redirect approach
      // Always use the production server for OAuth authorization
      const productionApiUrl = 'https://api.aiclone.space';
      
      const redirectUri = isDesktopApp
        ? `${productionApiUrl}/api/oauth/callback/gmail`
        : `${window.location.origin}/api/oauth/callback/gmail`;
      
      const authorizeUrl = `${productionApiUrl}/api/oauth/authorize/gmail?user_id=${actualUserId}&redirect_uri=${encodeURIComponent(redirectUri)}`;
      console.log('Using production API for OAuth authorization:', authorizeUrl);
      window.location.href = authorizeUrl;
    }
  };

  // Revoke Gmail access
  const handleRevoke = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Get the JWT token from localStorage
      const token = localStorage.getItem('token');
      
      if (!token) {
        console.error('No JWT token found - user is not authenticated');
        setError('Unable to revoke access. Please ensure you are logged in.');
        setLoading(false);
        return;
      }
      
      // The user ID should be available from the currentUser context
      if (!currentUser) {
        console.error('No user data available in AuthContext');
        setError('Unable to revoke access. Please try logging out and back in.');
        setLoading(false);
        return;
      }
      
      // Try to get the user ID from either _id or id field
      const actualUserId = currentUser._id || currentUser.id;
      
      if (!actualUserId) {
        console.error('No user ID available in AuthContext', currentUser);
        setError('Unable to revoke access. Please try logging out and back in.');
        setLoading(false);
        return;
      }
      
      console.log('Revoking Gmail access for user:', actualUserId);
      
      // Use appropriate server based on environment
      const isDesktopApp = window.navigator.userAgent.includes('Electron');
      
      const baseUrl = isDesktopApp 
        ? (window.OAUTH_BASE_URL || 'http://localhost:5002')  // Desktop uses local backend
        : 'https://api.aiclone.space';  // Web uses production API
      
      const revokeUrl = `${baseUrl}/api/oauth/revoke/gmail?user_id=${actualUserId}`;
      console.log(`Using ${isDesktopApp ? 'local backend' : 'production API'} for OAuth revocation:`, revokeUrl);
      
      const response = await axios.post(revokeUrl);
      console.log('Revoke response:', response.data);
      
      // Remove the Gmail token from localStorage
      localStorage.removeItem('gmail_token');
      
      // Update auth status
      setAuthStatus({ authenticated: false, message: 'Disconnected from Gmail' });
      
      // Call onAuthSuccess with false to indicate revocation
      if (onAuthSuccess) onAuthSuccess(false);
    } catch (error) {
      console.error('Error revoking Gmail access:', error);
      setError('Failed to revoke Gmail access. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Render the component
  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {authStatus.authenticated ? (
        <Box>
          <Alert severity="success" sx={{ mb: 2 }}>
            <Typography variant="body1">
              Connected to Gmail! Your AI clone can now access and respond to your emails.
            </Typography>
          </Alert>
          
          <Button
            variant="outlined"
            color="error"
            onClick={handleRevoke}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <EmailIcon />}
          >
            DISCONNECT GMAIL
          </Button>
        </Box>
      ) : (
        <Button
          variant="contained"
          color="primary"
          onClick={handleAuth}
          disabled={loading || authInProgress}
          startIcon={loading || authInProgress ? <CircularProgress size={20} /> : <EmailIcon />}
        >
          CONNECT GMAIL
        </Button>
      )}
    </Box>
  );
};

export default GmailOAuthButton;
