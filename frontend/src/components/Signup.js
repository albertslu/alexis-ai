import React, { useState } from 'react';
import { Box, Typography, Button, Paper, Container, TextField, Alert, Divider } from '@mui/material';
import EmailIcon from '@mui/icons-material/Email';
import GoogleIcon from '@mui/icons-material/Google';
import { useNavigate, Link } from 'react-router-dom';
import axios from '../api/axios';
import { useAuth } from '../contexts/AuthContext';

const Signup = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGoogleSignup = () => {
    // Use exactly the same pattern as the working Gmail OAuth flow
    const redirectUri = `http://localhost:5002/api/oauth/callback/gmail`;
    console.log('Redirecting to Google OAuth:', redirectUri);
    window.location.href = `http://localhost:5002/api/oauth/authorize/gmail?user_id=default&redirect_uri=${encodeURIComponent(redirectUri)}&auth_purpose=login`;
  };
  
  const handleEmailSignup = async (e) => {
    e.preventDefault();
    setError('');
    
    // Validate passwords match
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    setLoading(true);
    
    try {
      console.log('Attempting signup with email:', email);
      
      // Use standard axios with relative URL
      const response = await axios.post('/api/auth/signup', { email, password });
      
      console.log('Signup response:', response.data);
      
      if (response.data.status === 'success') {
        console.log('Signup successful, storing token and user data');
        
        // Store token and user data in localStorage
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        
        console.log('Stored user data:', response.data.user);
        
        // Login with the token
        await login(response.data.token);
        
        // Redirect to dashboard page
        navigate('/dashboard');
      } else {
        setError(response.data.message || 'Signup failed');
      }
    } catch (err) {
      console.error('Signup error:', err);
      
      // Provide more helpful error message based on the error type
      if (err.code === 'ERR_NETWORK') {
        setError('Network error: Could not connect to the server. Please check if the backend is running.');
      } else if (err.response) {
        // The server responded with an error
        setError(err.response.data?.message || `Server error: ${err.response.status}`);
      } else {
        setError(`Signup failed: ${err.message}`);
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
            Create your account
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          
          {/* Email Signup Form */}
          <Box component="form" onSubmit={handleEmailSignup} sx={{ mt: 2 }}>
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
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
            />
            <TextField
              variant="outlined"
              margin="normal"
              required
              fullWidth
              id="confirmPassword"
              label="Confirm Password"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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
              {loading ? 'Creating Account...' : 'Sign up with Email'}
            </Button>
          </Box>
          
          <Divider sx={{ my: 3 }}>OR</Divider>
          
          <Box sx={{ mb: 2 }}>
            <Button
              variant="contained"
              fullWidth
              startIcon={<GoogleIcon />}
              onClick={handleGoogleSignup}
              disabled={loading}
              sx={{ 
                py: 1.5, 
                backgroundColor: '#4285F4',
                '&:hover': {
                  backgroundColor: '#357ae8',
                }
              }}
            >
              Sign up with Google
            </Button>
          </Box>
          
          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="body2">
              Already have an account?{' '}
              <Link to="/login" style={{ textDecoration: 'none', color: '#2196f3' }}>
                Sign in
              </Link>
            </Typography>
          </Box>
          
          <Divider sx={{ my: 3 }} />
          
          <Typography variant="body2" color="text.secondary" align="center">
            By signing up, you agree to our Terms of Service and Privacy Policy.
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default Signup;
