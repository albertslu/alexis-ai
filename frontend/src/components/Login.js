import React, { useState } from 'react';
import { Box, Typography, Button, Paper, Container, Divider, TextField, Alert } from '@mui/material';
import GoogleIcon from '@mui/icons-material/Google';
import EmailIcon from '@mui/icons-material/Email';
import { useNavigate, Link } from 'react-router-dom';
import axios from '../api/axios';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGoogleLogin = () => {
    // Use exactly the same pattern as the working Gmail OAuth flow
    // This ensures the redirect URI matches what's configured in Google Cloud Console
    const apiBaseUrl = window.isElectron ? window.API_BASE_URL : (process.env.REACT_APP_API_URL || 'http://localhost:5002');
    const redirectUri = `${apiBaseUrl}/api/oauth/callback/gmail`;
    window.location.href = `${apiBaseUrl}/api/oauth/authorize/gmail?user_id=default&redirect_uri=${encodeURIComponent(redirectUri)}&auth_purpose=login`;
  };
  
  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      console.log('Attempting login with email:', email);
      
      // Use standard axios with relative URL
      const response = await axios.post('/api/auth/simple-login', { email, password });
      
      console.log('Login response:', response.data);
      
      if (response.data.status === 'success') {
        console.log('Login successful, storing token and user data');
        
        // Store token and user data in localStorage
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        
        // Explicitly store the user ID for OAuth flows
        // Backend might return either _id (MongoDB) or id field
        const userId = response.data.user && (response.data.user._id || response.data.user.id);
        if (userId) {
          localStorage.setItem('userId', userId);
          console.log('Stored user ID in localStorage:', userId);
        } else {
          console.warn('No user ID found in response data:', response.data.user);
        }
        
        console.log('Stored user data:', response.data.user);
        
        // Login with the token
        await login(response.data.token);
        
        // Redirect to dashboard page
        navigate('/dashboard');
      } else {
        setError(response.data.message || 'Login failed');
      }
    } catch (err) {
      console.error('Login error:', err);
      
      // Provide more helpful error message based on the error type
      if (err.code === 'ERR_NETWORK') {
        setError('Network error: Could not connect to the server. Please check if the backend is running.');
      } else if (err.response) {
        // The server responded with an error
        setError(err.response.data?.message || `Server error: ${err.response.status}`);
      } else {
        setError(`Login failed: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Alexis AI
          </Typography>
          
          <Typography variant="h6" component="h2" gutterBottom align="center">
            Sign in to your account
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          
          {/* Simple Email Login Form */}
          <Box component="form" onSubmit={handleEmailLogin} sx={{ mt: 2 }}>
            <TextField
              variant="outlined"
              margin="normal"
              required
              fullWidth
              id="email"
              label="Email Address"
              name="email"
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />
            <TextField
              variant="outlined"
              margin="normal"
              required
              fullWidth
              id="password"
              label="Password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              color="primary"
              startIcon={<EmailIcon />}
              sx={{ mt: 2, mb: 2, py: 1.5 }}
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Sign in with Email'}
            </Button>
          </Box>
          
          <Divider sx={{ my: 3 }}>OR</Divider>
          
          <Box sx={{ mb: 2 }}>
            <Button
              variant="contained"
              fullWidth
              startIcon={<GoogleIcon />}
              onClick={handleGoogleLogin}
              disabled={loading}
              sx={{ 
                py: 1.5, 
                backgroundColor: '#4285F4',
                '&:hover': {
                  backgroundColor: '#357ae8',
                }
              }}
            >
              Sign in with Google
            </Button>
          </Box>
          
          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="body2">
              Don't have an account?{' '}
              <Link to="/signup" style={{ textDecoration: 'none', color: '#2196f3' }}>
                Sign up
              </Link>
            </Typography>
          </Box>
          
          <Divider sx={{ my: 3 }} />
          
          <Typography variant="body2" color="text.secondary" align="center">
            By signing in, you agree to our Terms of Service and Privacy Policy.
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default Login;
