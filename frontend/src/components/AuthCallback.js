import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Box, Typography, CircularProgress, Alert } from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

const AuthCallback = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const processAuth = async () => {
      // Get the token from the URL query parameters
      const params = new URLSearchParams(location.search);
      const token = params.get('token');
      const errorMsg = params.get('error');
      
      console.log('AuthCallback - URL params:', { token, errorMsg });
      
      if (errorMsg) {
        console.error('Auth error from URL:', errorMsg);
        setError(decodeURIComponent(errorMsg));
        return;
      }
      
      if (!token) {
        console.error('No token received in callback');
        setError('No authentication token received');
        return;
      }
      
      try {
        console.log('Attempting login with token:', token.substring(0, 10) + '...');
        // Login with the token
        await login(token);
        
        // Add a delay to ensure the login state is updated
        console.log('Login successful, redirecting to home page...');
        setTimeout(() => {
          navigate('/');
        }, 500);
      } catch (err) {
        console.error('Error during authentication:', err);
        setError('Authentication failed. Please try again.');
      }
    };
    
    processAuth();
  }, [location, login, navigate]);
  
  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      minHeight: '100vh',
      p: 3
    }}>
      {error ? (
        <Alert severity="error" sx={{ maxWidth: 500, width: '100%' }}>
          {error}
        </Alert>
      ) : (
        <>
          <CircularProgress size={60} />
          <Typography variant="h6" sx={{ mt: 3 }}>
            Completing authentication...
          </Typography>
        </>
      )}
    </Box>
  );
};

export default AuthCallback;
