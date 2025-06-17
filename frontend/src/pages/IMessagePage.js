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
  AccessTime as AccessTimeIcon,
  Settings as SettingsIcon,
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Phone as PhoneIcon,
  Chat as ChatIcon,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';

const IMessagePage = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [duration, setDuration] = useState(4);
  
  // State for overlay settings only
  // 'enabled' is session-only and not stored in MongoDB
  const [overlayEnabled, setOverlayEnabled] = useState(false);
  const [overlaySettings, setOverlaySettings] = useState({
    suggestionCount: 3
    // Note: checkInterval is now hardcoded to 1 second in the overlay.js file
  });

  // Fetch overlay settings on component mount
  useEffect(() => {
    fetchOverlaySettings();
    
    // Listen for overlay deactivation events (when user closes the overlay)
    if (window.electron && window.electron.overlay) {
      window.electron.overlay.onDeactivated(() => {
        setOverlayEnabled(false);
        setSuccess('Native Messages assistant closed');
        setTimeout(() => setSuccess(null), 3000);
      });
    }
  }, []);

  // Handle overlay toggle - this is session-only and not persisted to MongoDB
  const handleOverlayToggle = async (e) => {
    try {
      const newEnabledState = e.target.checked;
      setOverlayEnabled(newEnabledState);
      
      // Update the Electron app with the new state
      await window.electron.overlay.updateSettings({
        ...overlaySettings,
        enabled: newEnabledState
      });
      
      // Activate or deactivate the overlay based on the toggle
      if (newEnabledState) {
        // Start both the overlay and the active chat detector
        await window.electron.overlay.activate();
        
        // Get the WebSocket URL from the Electron app
        const port = await window.electron.overlay.getPort();
        const websocketUrl = `ws://localhost:${port}`;
        
        // Start the active chat detector via the Flask API
        try {
          const response = await axios.post('/api/active-chat-detector/start', {
            websocket_url: websocketUrl
          });
          console.log('Active chat detector started:', response.data);
        } catch (detectorErr) {
          console.error('Error starting active chat detector:', detectorErr);
          // Continue even if the active chat detector fails to start
        }
        
        setSuccess('Native Messages assistant activated');
      } else {
        // Stop both the overlay and the active chat detector
        await window.electron.overlay.deactivate();
        
        // Stop the active chat detector via the Flask API
        try {
          const response = await axios.post('/api/active-chat-detector/stop');
          console.log('Active chat detector stopped:', response.data);
        } catch (detectorErr) {
          console.error('Error stopping active chat detector:', detectorErr);
          // Continue even if the active chat detector fails to stop
        }
        
        setSuccess('Native Messages assistant deactivated');
      }
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Error toggling overlay:', err);
      setError(`Failed to toggle overlay: ${err.message}`);
      setTimeout(() => setError(null), 3000);
    }
  };
  
  // Show a success message when the component mounts to indicate persistence
  useEffect(() => {
    setSuccess('Configuration saved');
    setTimeout(() => setSuccess(null), 3000);
  }, []);
  
  // Fetch overlay settings from MongoDB
  const fetchOverlaySettings = async () => {
    try {
      setLoading(true);
      
      // Get settings directly from MongoDB
      const response = await axios.get('/api/overlay-settings');
      
      if (response.data.success && response.data.settings) {
        // Update local state with settings from MongoDB
        setOverlaySettings(response.data.settings);
        
        // Also update the electron store for local access, but don't activate the overlay
        await window.electron.overlay.updateSettings({
          ...response.data.settings,
          enabled: false // Always start with overlay disabled
        });
      } else {
        throw new Error('Failed to get settings from server');
      }
    } catch (err) {
      console.error('Error fetching overlay settings:', err);
      setError('Failed to fetch overlay settings from server');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };
  
  // Update overlay settings in MongoDB
  const updateOverlaySettings = async () => {
    try {
      setLoading(true);
      
      // Only save persistent settings (suggestionCount) to MongoDB
      // Note: checkInterval is now hardcoded to 1 second in the overlay.js file
      const persistentSettings = {
        suggestionCount: overlaySettings.suggestionCount
      };
      
      // Save to MongoDB
      const response = await axios.post('/api/overlay-settings', {
        settings: persistentSettings
      });
      
      if (response.data.success) {
        // If MongoDB save is successful, update local electron store with current enabled state
        await window.electron.overlay.updateSettings({
          ...persistentSettings,
          enabled: overlayEnabled
        });
        setSuccess('Overlay settings saved successfully');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        throw new Error(response.data.message || 'Failed to save settings');
      }
    } catch (err) {
      console.error('Error updating overlay settings:', err);
      setError(`Failed to save overlay settings: ${err.message}`);
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  // All Mac Message Listener functions removed

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        iMessage Suggestions
      </Typography>
      
      <Typography variant="body1" paragraph>
        Configure how Alexis AI provides message suggestions for your iMessage conversations.
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
      
      {/* Mac Message Listener Control and Logs removed */}
      
      {/* Response Overlay Settings */}
      <Card sx={{ mt: 4, mb: 4 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              <ChatIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Native Messages Assistant
            </Typography>
            <IconButton onClick={fetchOverlaySettings} size="small">
              <RefreshIcon />
            </IconButton>
          </Box>
          
          <Typography variant="body2" color="textSecondary" paragraph>
            The native overlay agent shows AI-generated suggestions directly in your active Messages conversations and allows you to insert them with a click.
          </Typography>
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" gutterBottom>Configuration</Typography>
                
                <FormControlLabel
                  control={
                    <Switch
                      checked={overlayEnabled}
                      onChange={handleOverlayToggle}
                      disabled={loading}
                    />
                  }
                  label="Enable Native Messages Assistant"
                />
                
                <Typography variant="body2" color="textSecondary" sx={{ mt: 1, mb: 2 }}>
                  When enabled, a native assistant will appear in your menu bar and show AI-generated suggestions when Messages is active. Click any suggestion to insert it directly into your conversation.
                </Typography>
                
                <TextField
                  label="Suggestion Count"
                  type="number"
                  value={overlaySettings.suggestionCount}
                  onChange={(e) => setOverlaySettings({...overlaySettings, suggestionCount: parseInt(e.target.value) || 1})}
                  disabled={loading || !overlaySettings.enabled}
                  fullWidth
                  margin="normal"
                  InputProps={{
                    inputProps: { min: 1, max: 5 }
                  }}
                  helperText="Number of response suggestions to show (1-5)"
                />
                
                {/* Check interval is now hardcoded to 1 second in the overlay.js file */}
              </Box>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" gutterBottom>Permissions Required</Typography>
                
                <List>
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon color="success" />
                    </ListItemIcon>
                    <ListItemText 
                      primary="Full Disk Access" 
                      secondary="Required to read Messages database"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon color="success" />
                    </ListItemIcon>
                    <ListItemText 
                      primary="Accessibility" 
                      secondary="Required for overlay to insert responses"
                    />
                  </ListItem>
                </List>
                
                <Box sx={{ mt: 3 }}>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={updateOverlaySettings}
                    disabled={loading}
                    fullWidth
                  >
                    Save Overlay Settings
                  </Button>
                </Box>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Container>
  );
};

export default IMessagePage;
