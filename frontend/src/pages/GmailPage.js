import React, { useState, useEffect } from 'react';
import axios from '../api/axios';
import {
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Container,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Select,
  Slider,
  Stack,
  Switch,
  TextField,
  Typography,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Tooltip,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Upload as UploadIcon,
  Email as EmailIcon,
  AccessTime as AccessTimeIcon,
  Settings as SettingsIcon,
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Check as CheckIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import GmailOAuthButton from '../components/GmailOAuthButton';

const GmailPage = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [duration, setDuration] = useState(4);
  
  // Gmail Listener State
  const [gmailListenerStatus, setGmailListenerStatus] = useState({
    status: 'stopped',
    pid: null,
    config: {
      auto_respond: false,
      check_interval: 60,
      max_emails: 5,
      respond_to_all: false,
      filter_labels: [],
      filter_from: '',
      filter_to: '',
      filter_subject: ''
    }
  });
  const [gmailAutoRespond, setGmailAutoRespond] = useState(false);
  const [gmailCheckInterval, setGmailCheckInterval] = useState(60);
  const [gmailMaxEmails, setGmailMaxEmails] = useState(5);
  const [gmailRespondToAll, setGmailRespondToAll] = useState(false);
  const [gmailFilterLabels, setGmailFilterLabels] = useState('');
  const [gmailFilterFrom, setGmailFilterFrom] = useState('');
  const [gmailFilterTo, setGmailFilterTo] = useState('');
  const [gmailFilterSubject, setGmailFilterSubject] = useState('');
  const [gmailCredentialsStatus, setGmailCredentialsStatus] = useState('not_configured');
  const [isGmailAuthenticated, setIsGmailAuthenticated] = useState(false);

  // Fetch Gmail listener status on component mount
  useEffect(() => {
    fetchGmailListenerStatus();
    checkGmailAuthStatus();
    
    // Force an update to the configuration when the page loads
    // This ensures the gmail_configs collection is created in MongoDB
    setTimeout(() => {
      updateGmailListenerConfig();
    }, 2000); // Wait 2 seconds to ensure the status has been fetched
  }, []);

  // Update local state when gmailListenerStatus changes
  useEffect(() => {
    if (gmailListenerStatus.config) {
      setGmailAutoRespond(gmailListenerStatus.config.auto_respond);
      setGmailCheckInterval(gmailListenerStatus.config.check_interval);
      setGmailMaxEmails(gmailListenerStatus.config.max_emails || 5);
      setGmailRespondToAll(gmailListenerStatus.config.respond_to_all || false);
      
      // Format filter labels for display
      if (gmailListenerStatus.config.filter_labels && gmailListenerStatus.config.filter_labels.length > 0) {
        setGmailFilterLabels(gmailListenerStatus.config.filter_labels.join(', '));
      } else {
        setGmailFilterLabels('');
      }
      
      setGmailFilterFrom(gmailListenerStatus.config.filter_from || '');
      setGmailFilterTo(gmailListenerStatus.config.filter_to || '');
      setGmailFilterSubject(gmailListenerStatus.config.filter_subject || '');
    }
  }, [gmailListenerStatus]);

  const fetchGmailListenerStatus = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/gmail-listener/status');
      setGmailListenerStatus(response.data);
    } catch (err) {
      console.error('Error fetching Gmail listener status:', err);
      setError('Failed to fetch Gmail listener status');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  const checkGmailAuthStatus = async () => {
    try {
      // Get the current user ID from the auth token if available
      const user = localStorage.getItem('user');
      const userId = user ? JSON.parse(user).id : 'default';
      
      // Add the user_id as a query parameter
      const response = await axios.get(`/api/oauth/status/gmail?user_id=${userId}`);
      setIsGmailAuthenticated(response.data.authenticated);
      
      // If authenticated, also update the credentials status
      if (response.data.authenticated) {
        setGmailCredentialsStatus('configured');
      } else {
        setGmailCredentialsStatus('not_configured');
      }
      
      return response.data;
    } catch (error) {
      console.error('Error checking Gmail auth status:', error);
      setGmailCredentialsStatus('error');
      return { authenticated: false, error: error.message };
    }
  };

  const startGmailListener = async () => {
    try {
      setLoading(true);
      
      // Parse comma-separated labels
      let parsedLabels = [];
      if (gmailFilterLabels.trim()) {
        parsedLabels = gmailFilterLabels.split(',').map(label => label.trim()).filter(label => label);
      }
      
      const response = await axios.post('/api/gmail-listener/start', {
        auto_respond: gmailAutoRespond,
        check_interval: gmailCheckInterval,
        max_emails_per_check: gmailMaxEmails,
        respond_to_all: gmailRespondToAll,
        filter_labels: parsedLabels,
        filter_from: gmailFilterFrom,
        filter_to: gmailFilterTo,
        filter_subject: gmailFilterSubject
      });
      
      setGmailListenerStatus(response.data);
      setSuccess('Gmail Listener started successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Error starting Gmail listener:', err);
      setError('Failed to start Gmail Listener. ' + (err.response?.data?.error || ''));
      setTimeout(() => setError(null), 5000);
    } finally {
      setLoading(false);
    }
  };

  const stopGmailListener = async () => {
    try {
      setLoading(true);
      const response = await axios.post('/api/gmail-listener/stop');
      setGmailListenerStatus(response.data);
      setSuccess('Gmail Listener stopped successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Error stopping Gmail listener:', err);
      setError('Failed to stop Gmail Listener');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  const updateGmailListenerConfig = async () => {
    try {
      setLoading(true);
      
      // Parse comma-separated labels
      let parsedLabels = [];
      if (gmailFilterLabels.trim()) {
        parsedLabels = gmailFilterLabels.split(',').map(label => label.trim()).filter(label => label);
      }
      
      const response = await axios.post('/api/gmail-listener/config', {
        auto_respond: gmailAutoRespond,
        check_interval: gmailCheckInterval,
        max_emails_per_check: gmailMaxEmails,
        respond_to_all: gmailRespondToAll,
        filter_labels: parsedLabels,
        filter_from: gmailFilterFrom,
        filter_to: gmailFilterTo,
        filter_subject: gmailFilterSubject
      });
      
      setGmailListenerStatus(response.data);
      setSuccess('Gmail configuration updated successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Error updating Gmail listener config:', err);
      setError('Failed to update Gmail configuration');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleGmailAuth = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/gmail-listener/auth-url');
      window.open(response.data.url, '_blank');
      setSuccess('Please complete Gmail authentication in the opened window');
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      console.error('Error getting Gmail auth URL:', err);
      setError('Failed to initiate Gmail authentication');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Gmail Auto-Response
      </Typography>
      
      <Typography variant="body1" paragraph>
        Set up your AI Clone to automatically respond to emails when you're away.
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}
      
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              <EmailIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Gmail Listener Control
            </Typography>
            <IconButton onClick={fetchGmailListenerStatus} size="small">
              <RefreshIcon />
            </IconButton>
          </Box>
          
          <Chip 
            icon={gmailListenerStatus.status === 'running' ? <CheckIcon /> : <CloseIcon />}
            label={gmailListenerStatus.status === 'running' ? 'Running' : 'Stopped'}
            color={gmailListenerStatus.status === 'running' ? 'success' : 'default'}
            sx={{ mb: 2 }}
          />
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Box>
                <Typography variant="subtitle1" gutterBottom>Configuration</Typography>
                
                <FormControlLabel
                  control={
                    <Switch
                      checked={gmailAutoRespond}
                      onChange={(e) => setGmailAutoRespond(e.target.checked)}
                      disabled={gmailListenerStatus.status === 'running'}
                    />
                  }
                  label="Auto-respond to emails"
                />
                
                <Box sx={{ mt: 2 }}>
                  <Typography gutterBottom>Check Interval (seconds)</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Slider
                      value={gmailCheckInterval}
                      onChange={(e, newValue) => setGmailCheckInterval(newValue)}
                      min={10}
                      max={300}
                      disabled={gmailListenerStatus.status === 'running'}
                      sx={{ mr: 2, flexGrow: 1 }}
                    />
                    <TextField
                      value={gmailCheckInterval}
                      onChange={(e) => {
                        const value = parseInt(e.target.value);
                        if (!isNaN(value) && value >= 10) {
                          setGmailCheckInterval(value);
                        }
                      }}
                      disabled={gmailListenerStatus.status === 'running'}
                      inputProps={{ min: 10, max: 300 }}
                      sx={{ width: '60px' }}
                    />
                  </Box>
                </Box>
                
                {/* Add duration control here */}
                {gmailListenerStatus.status === 'running' && (
                  <Box sx={{ mt: 2 }}>
                    <Typography gutterBottom>Auto-stop after (hours)</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <TextField
                        value={duration}
                        onChange={(e) => {
                          const value = parseInt(e.target.value);
                          if (!isNaN(value) && value > 0) {
                            setDuration(value);
                          }
                        }}
                        inputProps={{ min: 1, max: 24 }}
                        sx={{ width: '80px' }}
                      />
                      <Button 
                        variant="contained" 
                        color="primary"
                        onClick={() => {/* Add auto-stop functionality */}}
                      >
                        Set Auto-stop
                      </Button>
                    </Box>
                  </Box>
                )}
                
                <Box sx={{ mt: 2 }}>
                  <Typography gutterBottom>Max Emails per Check</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Slider
                      value={gmailMaxEmails}
                      onChange={(e, newValue) => setGmailMaxEmails(newValue)}
                      min={1}
                      max={20}
                      disabled={gmailListenerStatus.status === 'running'}
                      sx={{ mr: 2, flexGrow: 1 }}
                    />
                    <TextField
                      value={gmailMaxEmails}
                      onChange={(e) => {
                        const value = parseInt(e.target.value);
                        if (!isNaN(value) && value > 0) {
                          setGmailMaxEmails(value);
                        }
                      }}
                      disabled={gmailListenerStatus.status === 'running'}
                      inputProps={{ min: 1, max: 20 }}
                      sx={{ width: '60px' }}
                    />
                  </Box>
                </Box>
                
                <Box sx={{ mt: 2 }}>
                  <Typography gutterBottom>Filter Rules</Typography>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={gmailRespondToAll}
                        onChange={(e) => setGmailRespondToAll(e.target.checked)}
                        disabled={gmailListenerStatus.status === 'running'}
                      />
                    }
                    label="Respond to all recipients"
                  />
                  
                  <TextField
                    fullWidth
                    label="Filter by Labels"
                    placeholder="Comma-separated labels (e.g. Inbox, Important)"
                    value={gmailFilterLabels}
                    onChange={(e) => setGmailFilterLabels(e.target.value)}
                    disabled={gmailListenerStatus.status === 'running'}
                    sx={{ mt: 2 }}
                  />
                  
                  <TextField
                    fullWidth
                    label="Filter by Sender"
                    placeholder="Sender email or domain (e.g. @example.com)"
                    value={gmailFilterFrom}
                    onChange={(e) => setGmailFilterFrom(e.target.value)}
                    disabled={gmailListenerStatus.status === 'running'}
                    sx={{ mt: 2 }}
                  />
                  
                  <TextField
                    fullWidth
                    label="Filter by Recipient"
                    placeholder="Recipient email or domain"
                    value={gmailFilterTo}
                    onChange={(e) => setGmailFilterTo(e.target.value)}
                    disabled={gmailListenerStatus.status === 'running'}
                    sx={{ mt: 2 }}
                  />
                  
                  <TextField
                    fullWidth
                    label="Filter by Subject"
                    placeholder="Subject keywords"
                    value={gmailFilterSubject}
                    onChange={(e) => setGmailFilterSubject(e.target.value)}
                    disabled={gmailListenerStatus.status === 'running'}
                    sx={{ mt: 2 }}
                  />
                </Box>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box>
                <Typography variant="subtitle1" gutterBottom>Gmail Authentication</Typography>
                
                <Card variant="outlined" sx={{ mb: 3, p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Chip
                      label={
                        isGmailAuthenticated
                          ? 'Authenticated'
                          : gmailCredentialsStatus === 'error'
                          ? 'Authentication Error'
                          : 'Not Authenticated'
                      }
                      color={
                        isGmailAuthenticated
                          ? 'success'
                          : gmailCredentialsStatus === 'error'
                          ? 'error'
                          : 'default'
                      }
                      size="small"
                      sx={{ mr: 1 }}
                    />
                    <Typography variant="body2">
                      {isGmailAuthenticated
                        ? 'Your Gmail account is connected'
                        : gmailCredentialsStatus === 'error'
                        ? 'There was an error with your Gmail authentication'
                        : 'Gmail account not connected'}
                    </Typography>
                  </Box>
                  
                  <Box sx={{ mt: 2 }}>
                    <GmailOAuthButton 
                      onAuthSuccess={() => {
                        checkGmailAuthStatus();
                        setSuccess('Successfully connected to Gmail!');
                        setTimeout(() => setSuccess(null), 5000);
                      }}
                      disabled={gmailListenerStatus.status === 'running'}
                    />
                  </Box>
                </Card>
                
                <Box sx={{ mt: 3 }}>
                  <Typography variant="subtitle1" gutterBottom>Controls</Typography>
                  
                  {gmailListenerStatus.status === 'running' ? (
                    <Button
                      variant="contained"
                      color="error"
                      startIcon={<StopIcon />}
                      onClick={stopGmailListener}
                      disabled={loading}
                      fullWidth
                    >
                      Stop Gmail Listener
                    </Button>
                  ) : (
                    <>
                      <Button
                        variant="contained"
                        color="primary"
                        startIcon={<PlayArrowIcon />}
                        onClick={startGmailListener}
                        disabled={loading}
                        fullWidth
                        sx={{ mb: 1 }}
                      >
                        Start Gmail Listener
                      </Button>
                      
                      <Button
                        variant="outlined"
                        color="primary"
                        startIcon={<SettingsIcon />}
                        onClick={updateGmailListenerConfig}
                        disabled={loading || gmailListenerStatus.status === 'running'}
                        fullWidth
                      >
                        Update Configuration
                      </Button>
                    </>
                  )}
                </Box>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      
      <Box sx={{ mt: 4, mb: 2 }}>
        <Typography variant="h6" gutterBottom>Gmail Listener Logs</Typography>
        <Paper
          sx={{
            p: 2,
            maxHeight: '300px',
            overflow: 'auto',
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            backgroundColor: '#f5f5f5'
          }}
        >
          <pre>
            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <CircularProgress size={24} />
              </Box>
            ) : (
              "Log output will appear here when the Gmail Listener is running."
            )}
          </pre>
        </Paper>
      </Box>
    </Container>
  );
};

export default GmailPage;
