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
  Phone as PhoneIcon
} from '@mui/icons-material';

const AutoResponsePage = () => {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState({
    active: false,
    schedule: {
      active: false,
      channels: {
        text: false,
        email: false
      },
      schedule: {
        enabled: false,
        start_time: "09:00",
        end_time: "17:00",
        days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
      },
      confidence_threshold: 0.7,
      auto_response_enabled_until: null
    }
  });
  const [duration, setDuration] = useState(4);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("17:00");
  const [selectedDays, setSelectedDays] = useState([]);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.7);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [emailStatus, setEmailStatus] = useState('not_configured');
  const [twilioStatus, setTwilioStatus] = useState('not_configured');
  
  // Mac Message Listener state
  const [macListenerStatus, setMacListenerStatus] = useState({
    status: 'stopped',
    pid: null,
    config: {
      auto_respond: false,
      check_interval: 5,
      allowed_numbers: []
    }
  });
  const [newPhoneNumber, setNewPhoneNumber] = useState('');
  const [checkInterval, setCheckInterval] = useState(5);
  const [autoRespond, setAutoRespond] = useState(false);
  const [allowedNumbers, setAllowedNumbers] = useState('');

  // Gmail Listener State
  const [gmailListenerStatus, setGmailListenerStatus] = useState({
    status: 'stopped',
    pid: null,
    config: {
      check_interval: 60,
      auto_respond: false,
      confidence_threshold: 0.7,
      max_emails_per_check: 10,
      filter_rules: {
        ignore_noreply: true,
        ignore_subscriptions: true,
        allowed_senders: []
      }
    },
    has_credentials: false
  });
  const [gmailCheckInterval, setGmailCheckInterval] = useState(60);
  const [gmailAutoRespond, setGmailAutoRespond] = useState(false);
  const [gmailMaxEmails, setGmailMaxEmails] = useState(10);
  const [gmailIgnoreNoreply, setGmailIgnoreNoreply] = useState(true);
  const [gmailIgnoreSubscriptions, setGmailIgnoreSubscriptions] = useState(true);
  const [newGmailSender, setNewGmailSender] = useState('');
  const [gmailAllowedSenders, setGmailAllowedSenders] = useState([]);
  const [credentialFile, setCredentialFile] = useState(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);

  const [messageLog, setMessageLog] = useState([]);
  const [showMessageLog, setShowMessageLog] = useState(false);
  const [terminalOutput, setTerminalOutput] = useState('');
  const [showTerminalOutput, setShowTerminalOutput] = useState(false);
  const [gmailTerminalOutput, setGmailTerminalOutput] = useState('');
  const [showGmailTerminalOutput, setShowGmailTerminalOutput] = useState(false);

  const [pendingEmails, setPendingEmails] = useState([]);
  const [showPendingEmails, setShowPendingEmails] = useState(false);

  useEffect(() => {
    fetchStatus();
    fetchMacListenerStatus();
    fetchGmailListenerStatus();
    fetchPendingEmails();
    
    // Initial fetch regardless of showMessageLog state
    fetchTerminalOutput();
    fetchGmailTerminalOutput();
    
    // Set up polling for message log and terminal output
    const interval = setInterval(() => {
      fetchTerminalOutput();
      fetchGmailTerminalOutput();
      fetchPendingEmails(); // Fetch pending emails regularly
      if (showMessageLog) {
        fetchMessageLog();
      }
    }, 3000); // Poll every 3 seconds
    
    return () => {
      clearInterval(interval);
    };
  }, [showMessageLog]);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/auto-response/status');
      
      // Ensure we have a valid response with the expected structure
      if (response.data && typeof response.data === 'object') {
        // Create a properly structured status object with defaults for missing properties
        const statusData = {
          active: response.data.active || false,
          schedule: {
            active: response.data.schedule?.active || false,
            channels: {
              text: response.data.schedule?.channels?.text || false,
              email: response.data.schedule?.channels?.email || false
            },
            schedule: {
              enabled: response.data.schedule?.schedule?.enabled || false,
              start_time: response.data.schedule?.schedule?.start_time || "09:00",
              end_time: response.data.schedule?.schedule?.end_time || "17:00",
              days: response.data.schedule?.schedule?.days || ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            },
            confidence_threshold: response.data.schedule?.confidence_threshold || 0.7,
            auto_response_enabled_until: response.data.schedule?.auto_response_enabled_until || null
          }
        };
        
        setStatus(statusData);
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching auto-response status:', err);
      setError('Failed to load auto-response status. Please try again later.');
      setLoading(false);
    }
  };

  const fetchMacListenerStatus = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/mac-listener/status');
      
      // Ensure we have a valid config object
      const safeResponse = {
        ...response.data,
        config: response.data.config || {
          auto_respond: false,
          check_interval: 5,
          allowed_numbers: []
        }
      };
      
      setMacListenerStatus(safeResponse);
      
      // Update the related state variables
      if (safeResponse.config) {
        setCheckInterval(safeResponse.config.check_interval || 5);
        setAutoRespond(safeResponse.config.auto_respond !== undefined ? safeResponse.config.auto_respond : false);
        setAllowedNumbers(Array.isArray(safeResponse.config.allowed_numbers) ? safeResponse.config.allowed_numbers.join(', ') : '');
      }
    } catch (err) {
      console.error('Error fetching Mac listener status:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchGmailListenerStatus = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/gmail-listener/status');
      
      if (response.data && typeof response.data === 'object') {
        setGmailListenerStatus({
          status: response.data.status || 'stopped',
          pid: response.data.pid || null,
          config: response.data.config || {
            check_interval: 60,
            auto_respond: false,
            confidence_threshold: 0.7,
            max_emails_per_check: 10,
            filter_rules: {
              ignore_noreply: true,
              ignore_subscriptions: true,
              allowed_senders: []
            }
          },
          has_credentials: response.data.has_credentials || false
        });
        
        // Update local state from config
        if (response.data.config) {
          setGmailCheckInterval(response.data.config.check_interval || 60);
          setGmailAutoRespond(response.data.config.auto_respond !== undefined ? response.data.config.auto_respond : false);
          setConfidenceThreshold(response.data.config.confidence_threshold || 0.7);
          setGmailMaxEmails(response.data.config.max_emails_per_check || 10);
          
          if (response.data.config.filter_rules) {
            setGmailIgnoreNoreply(response.data.config.filter_rules.ignore_noreply !== undefined ? 
              response.data.config.filter_rules.ignore_noreply : true);
            setGmailIgnoreSubscriptions(response.data.config.filter_rules.ignore_subscriptions !== undefined ? 
              response.data.config.filter_rules.ignore_subscriptions : true);
            setGmailAllowedSenders(response.data.config.filter_rules.allowed_senders || []);
          }
        }
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching Gmail Listener status:', err);
      setError('Failed to load Gmail Listener status. Please try again later.');
      setLoading(false);
    }
  };

  const fetchMessageLog = async () => {
    try {
      const response = await axios.get('/api/mac-listener/log');
      if (response.data && response.data.messages) {
        setMessageLog(response.data.messages);
      }
    } catch (err) {
      console.error('Error fetching message log:', err);
    }
  };

  const fetchTerminalOutput = async () => {
    try {
      const response = await axios.get('/api/mac-listener/terminal-output');
      if (response.data && response.data.output) {
        setTerminalOutput(response.data.output);
      }
    } catch (err) {
      console.error('Error fetching terminal output:', err);
    }
  };

  const fetchGmailTerminalOutput = async () => {
    try {
      const response = await axios.get('/api/gmail-listener/terminal-output');
      if (response.data && response.data.output) {
        setGmailTerminalOutput(response.data.output);
      }
    } catch (err) {
      console.error('Error fetching Gmail terminal output:', err);
    }
  };

  const fetchPendingEmails = async () => {
    try {
      const response = await axios.get('/api/gmail-listener/pending');
      if (response.data && response.data.pending) {
        setPendingEmails(response.data.pending);
      }
    } catch (err) {
      console.error('Error fetching pending emails:', err);
    }
  };

  const handleEnableAutoResponse = async (channel, duration) => {
    try {
      setLoading(true);
      const response = await axios.post('/api/auto-response/enable', {
        duration_hours: duration,
        channel: channel
      });
      setStatus(response.data);
      setSuccess(`Auto-response enabled for ${duration} hours on ${channel}`);
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error enabling auto-response:', err);
      setError('Failed to enable auto-response. Please try again later.');
      setLoading(false);
    }
  };

  const handleDisableAutoResponse = async () => {
    try {
      setLoading(true);
      const response = await axios.post('/api/auto-response/disable');
      setStatus(response.data);
      setSuccess('Auto-response disabled');
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error disabling auto-response:', err);
      setError('Failed to disable auto-response. Please try again later.');
      setLoading(false);
    }
  };

  const handleUpdateSchedule = async () => {
    try {
      setLoading(true);
      
      const updatedSchedule = {
        channels: {
          text: status.schedule?.channels?.text || false,
          email: status.schedule?.channels?.email || false
        },
        schedule: {
          enabled: status.schedule?.schedule?.enabled || false,
          start_time: startTime,
          end_time: endTime,
          days: selectedDays
        },
        confidence_threshold: confidenceThreshold
      };
      
      const response = await axios.post('/api/auto-response/schedule', updatedSchedule);
      setStatus(response.data);
      setSuccess('Schedule updated successfully');
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error updating schedule:', err);
      setError('Failed to update schedule. Please try again later.');
      setLoading(false);
    }
  };

  const handleToggleChannel = async (channel) => {
    try {
      setLoading(true);
      setError(null); // Clear any previous errors
      
      // Get current channels state with fallback to empty object
      const channels = status.schedule?.channels || {};
      
      // Create updated channels object with the toggled channel
      const updatedChannels = {
        ...channels,
        [channel]: !channels[channel]
      };
      
      // Create the complete updated schedule object
      const updatedSchedule = {
        ...status.schedule,
        channels: updatedChannels
      };
      
      // Send the update request
      const response = await axios.post('/api/auto-response/schedule', updatedSchedule);
      
      // Update local state with the response
      if (response.data && typeof response.data === 'object') {
        setStatus(response.data);
        const isEnabled = response.data.schedule?.channels?.[channel] || false;
        setSuccess(`${channel} channel ${isEnabled ? 'enabled' : 'disabled'}`);
      } else {
        throw new Error('Invalid response format');
      }
      
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error(`Error toggling ${channel} channel:`, err);
      setError(`Failed to toggle ${channel} channel. Please try again later.`);
      setLoading(false);
    }
  };

  const handleToggleScheduleEnabled = async () => {
    try {
      setLoading(true);
      
      const scheduleSettings = status.schedule?.schedule || {};
      const updatedSchedule = {
        ...status.schedule,
        schedule: {
          ...scheduleSettings,
          enabled: !scheduleSettings.enabled
        }
      };
      
      const response = await axios.post('/api/auto-response/schedule', updatedSchedule);
      setStatus(response.data);
      setSuccess(`Schedule ${updatedSchedule.schedule.enabled ? 'enabled' : 'disabled'}`);
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error toggling schedule:', err);
      setError('Failed to toggle schedule. Please try again later.');
      setLoading(false);
    }
  };

  const handleDayToggle = (day) => {
    const newSelectedDays = selectedDays.includes(day)
      ? selectedDays.filter(d => d !== day)
      : [...selectedDays, day];
    
    setSelectedDays(newSelectedDays);
  };

  const getAllowedNumbersArray = () => {
    if (!allowedNumbers) return [];
    return allowedNumbers.split(',').map(num => num.trim()).filter(num => num);
  };

  const handleStartMacListener = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Prepare the configuration
      const config = {
        auto_respond: autoRespond,
        check_interval: checkInterval,
        allowed_numbers: getAllowedNumbersArray()
      };
      
      console.log('Starting Mac listener with config:', config);
      
      const response = await axios.post('/api/mac-listener/start', config);
      
      if (response.data && response.data.status) {
        // Ensure we have a valid config object
        const safeResponse = {
          ...response.data,
          config: response.data.config || {
            auto_respond: autoRespond,
            check_interval: checkInterval,
            allowed_numbers: getAllowedNumbersArray()
          }
        };
        
        setMacListenerStatus(safeResponse);
        setSuccess(`Mac Message Listener started successfully${config.allowed_numbers.length ? ' for allowed numbers' : ''}`);
        
        // Refresh the status after a short delay
        setTimeout(() => {
          fetchMacListenerStatus();
        }, 1000);
      } else if (response.data && response.data.error) {
        setError(response.data.error);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err) {
      console.error('Error starting Mac listener:', err);
      setError(`Failed to start Mac Message Listener: ${err.response?.data?.error || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStopMacListener = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Stopping Mac listener');
      
      const response = await axios.post('/api/mac-listener/stop');
      
      if (response.data) {
        // Make sure we update our local state with the response data
        setMacListenerStatus(response.data);
        
        // Also update our local state variables to match
        if (response.data.config) {
          setCheckInterval(response.data.config.check_interval || 5);
          setAutoRespond(response.data.config.auto_respond !== undefined ? response.data.config.auto_respond : false);
          setAllowedNumbers(response.data.config.allowed_numbers ? response.data.config.allowed_numbers.join(', ') : '');
        }
        
        setSuccess('Mac Message Listener stopped successfully');
        
        // Refresh the status after a short delay
        setTimeout(() => {
          fetchMacListenerStatus();
        }, 1000);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err) {
      console.error('Error stopping Mac listener:', err);
      setError(`Failed to stop Mac Message Listener: ${err.response?.data?.error || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const updateMacListenerConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.post('/api/mac-listener/config', {
        auto_respond: autoRespond,
        check_interval: checkInterval,
        allowed_numbers: macListenerStatus.config.allowed_numbers
      });
      setMacListenerStatus(response.data);
      setSuccess('Mac Message Listener configuration updated successfully');
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error updating Mac Message Listener configuration:', err);
      setError('Failed to update Mac Message Listener configuration. Please try again later.');
      setLoading(false);
    }
  };

  const addAllowedNumber = () => {
    if (!newPhoneNumber) return;
    
    // Format the phone number if needed
    let formattedNumber = newPhoneNumber.trim();
    
    // Check if the number is already in the list
    if (macListenerStatus.config.allowed_numbers.includes(formattedNumber)) {
      setError('This phone number is already in the allowed list');
      setTimeout(() => setError(null), 3000);
      return;
    }
    
    // Add the number to the list
    const updatedNumbers = [...macListenerStatus.config.allowed_numbers, formattedNumber];
    setMacListenerStatus({
      ...macListenerStatus,
      config: {
        ...macListenerStatus.config,
        allowed_numbers: updatedNumbers
      }
    });
    
    // Clear the input field
    setNewPhoneNumber('');
  };

  const removeAllowedNumber = (number) => {
    const updatedNumbers = macListenerStatus.config.allowed_numbers.filter(n => n !== number);
    setMacListenerStatus({
      ...macListenerStatus,
      config: {
        ...macListenerStatus.config,
        allowed_numbers: updatedNumbers
      }
    });
  };

  const startGmailListener = async () => {
    try {
      setLoading(true);
      
      const config = {
        check_interval: gmailCheckInterval,
        auto_respond: gmailAutoRespond,
        confidence_threshold: confidenceThreshold,
        max_emails_per_check: gmailMaxEmails,
        filter_rules: {
          ignore_noreply: gmailIgnoreNoreply,
          ignore_subscriptions: gmailIgnoreSubscriptions,
          allowed_senders: gmailAllowedSenders
        }
      };
      
      const response = await axios.post('/api/gmail-listener/start', config);
      await fetchGmailListenerStatus();
      setSuccess('Gmail Listener started successfully');
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error starting Gmail Listener:', err);
      setError('Failed to start Gmail Listener. Please try again later.');
      setLoading(false);
    }
  };

  const stopGmailListener = async () => {
    try {
      setLoading(true);
      const response = await axios.post('/api/gmail-listener/stop');
      await fetchGmailListenerStatus();
      setSuccess('Gmail Listener stopped successfully');
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error stopping Gmail Listener:', err);
      setError('Failed to stop Gmail Listener. Please try again later.');
      setLoading(false);
    }
  };

  const updateGmailConfig = async () => {
    try {
      setLoading(true);
      
      const config = {
        check_interval: gmailCheckInterval,
        auto_respond: gmailAutoRespond,
        confidence_threshold: confidenceThreshold,
        max_emails_per_check: gmailMaxEmails,
        filter_rules: {
          ignore_noreply: gmailIgnoreNoreply,
          ignore_subscriptions: gmailIgnoreSubscriptions,
          allowed_senders: gmailAllowedSenders
        }
      };
      
      const response = await axios.post('/api/gmail-listener/config', config);
      setSuccess('Gmail configuration updated successfully');
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error updating Gmail configuration:', err);
      setError('Failed to update Gmail configuration. Please try again later.');
      setLoading(false);
    }
  };

  const handleAddGmailSender = () => {
    if (newGmailSender && !gmailAllowedSenders.includes(newGmailSender)) {
      setGmailAllowedSenders([...gmailAllowedSenders, newGmailSender]);
      setNewGmailSender('');
    }
  };

  const handleRemoveGmailSender = (sender) => {
    setGmailAllowedSenders(gmailAllowedSenders.filter(s => s !== sender));
  };

  const handleCredentialUpload = async () => {
    if (!credentialFile) {
      setError('Please select a credentials file first');
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('credentials', credentialFile);
      
      const response = await axios.post('/api/gmail-listener/credentials', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setUploadDialogOpen(false);
      setCredentialFile(null);
      await fetchGmailListenerStatus();
      setSuccess('Credentials uploaded successfully');
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error uploading credentials:', err);
      setError('Failed to upload credentials. Please try again later.');
      setLoading(false);
    }
  };

  const handleApproveEmail = async (emailId) => {
    try {
      setLoading(true);
      const response = await axios.post('/api/gmail-listener/approve', { email_id: emailId });
      
      if (response.data && response.data.success) {
        setSuccess('Email response approved and sent successfully');
        // Remove from pending list
        setPendingEmails(pendingEmails.filter(email => email.id !== emailId));
      } else {
        setError('Failed to approve email response');
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error approving email response:', err);
      setError('Failed to approve email response');
      setLoading(false);
    }
  };

  const handleRejectEmail = async (emailId) => {
    try {
      setLoading(true);
      const response = await axios.post('/api/gmail-listener/reject', { email_id: emailId });
      
      if (response.data && response.data.success) {
        setSuccess('Email response rejected successfully');
        // Remove from pending list
        setPendingEmails(pendingEmails.filter(email => email.id !== emailId));
      } else {
        setError('Failed to reject email response');
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error rejecting email response:', err);
      setError('Failed to reject email response');
      setLoading(false);
    }
  };

  const renderMacListenerStatus = () => {
    if (!macListenerStatus || !macListenerStatus.config) {
      return <Typography>Loading Mac listener status...</Typography>;
    }

    return (
      <>
        <Typography variant="body2" sx={{ mb: 1 }}>
          Status: <strong>{macListenerStatus.status === 'running' ? 'Running' : 'Stopped'}</strong>
          {macListenerStatus.status === 'running' && macListenerStatus.pid && (
            <> (PID: {macListenerStatus.pid})</>
          )}
        </Typography>
        
        <Typography variant="body2" sx={{ mb: 1 }}>
          Auto-respond: <strong>{macListenerStatus.config.auto_respond ? 'Enabled' : 'Disabled'}</strong>
        </Typography>
        
        <Typography variant="body2" sx={{ mb: 1 }}>
          Check interval: <strong>{macListenerStatus.config.check_interval || 5} seconds</strong>
        </Typography>
      </>
    );
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Auto-Response Control Panel
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}
      
      {/* Mac Message Listener Control */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              <PhoneIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Mac Message Listener Control
            </Typography>
            <IconButton onClick={fetchMacListenerStatus} size="small">
              <RefreshIcon />
            </IconButton>
          </Box>
          
          <Chip 
            icon={macListenerStatus.status === 'running' ? <CheckIcon /> : <CloseIcon />}
            label={macListenerStatus.status === 'running' ? 'Running' : 'Stopped'}
            color={macListenerStatus.status === 'running' ? 'success' : 'default'}
            sx={{ mb: 2 }}
          />
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" gutterBottom>Configuration</Typography>
                
                <FormControlLabel
                  control={
                    <Switch
                      checked={autoRespond}
                      onChange={(e) => setAutoRespond(e.target.checked)}
                      disabled={macListenerStatus.status === 'running'}
                    />
                  }
                  label="Auto-respond to messages"
                />
                
                <Box sx={{ mt: 2 }}>
                  <Typography gutterBottom>Check Interval (seconds)</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Slider
                      value={checkInterval}
                      onChange={(e, newValue) => setCheckInterval(newValue)}
                      min={1}
                      max={60}
                      disabled={macListenerStatus.status === 'running'}
                      sx={{ mr: 2, flexGrow: 1 }}
                    />
                    <TextField
                      value={checkInterval}
                      onChange={(e) => {
                        const value = parseInt(e.target.value);
                        if (!isNaN(value) && value > 0) {
                          setCheckInterval(value);
                        }
                      }}
                      disabled={macListenerStatus.status === 'running'}
                      inputProps={{ min: 1, max: 60 }}
                      sx={{ width: '60px' }}
                    />
                  </Box>
                </Box>
                
                {/* Add duration control here */}
                {macListenerStatus.status === 'running' && (
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
                        onClick={() => handleEnableAutoResponse('text', duration)}
                      >
                        Set Auto-stop
                      </Button>
                    </Box>
                  </Box>
                )}
                
                <Box sx={{ mt: 2 }}>
                  <Typography gutterBottom>Allowed Phone Numbers</Typography>
                  <TextField
                    fullWidth
                    placeholder="Comma-separated list of phone numbers"
                    value={allowedNumbers}
                    onChange={(e) => setAllowedNumbers(e.target.value)}
                    disabled={macListenerStatus.status === 'running'}
                    helperText="Will only respond to these contacts."
                    sx={{ mb: 2 }}
                  />
                </Box>
                
                {macListenerStatus.status !== 'running' && (
                  <Button
                    variant="contained"
                    color="primary"
                    fullWidth
                    onClick={updateMacListenerConfig}
                    disabled={loading}
                  >
                    UPDATE CONFIGURATION
                  </Button>
                )}
              </Box>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box>
                <Typography variant="subtitle1" gutterBottom>Mac Message Listener Status</Typography>
                <Typography variant="body2">
                  <strong>Status:</strong> {macListenerStatus.status === 'running' ? 'Running' : 'Stopped'}
                </Typography>
                <Typography variant="body2">
                  <strong>Auto-respond:</strong> {macListenerStatus.config.auto_respond ? 'Enabled' : 'Disabled'}
                </Typography>
                <Typography variant="body2">
                  <strong>Check interval:</strong> {macListenerStatus.config.check_interval} seconds
                </Typography>
                
                {macListenerStatus.config.allowed_numbers && macListenerStatus.config.allowed_numbers.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2"><strong>Allowed Phone Numbers:</strong></Typography>
                    <List dense>
                      {macListenerStatus.config.allowed_numbers.map((number, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <PhoneIcon fontSize="small" />
                          </ListItemIcon>
                          <ListItemText primary={number} />
                          <ListItemSecondaryAction>
                            <IconButton 
                              edge="end" 
                              onClick={() => removeAllowedNumber(number)}
                              disabled={macListenerStatus.status === 'running'}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </ListItemSecondaryAction>
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </Box>
            </Grid>
          </Grid>
          
          <Divider sx={{ my: 2 }} />
          
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
            {macListenerStatus.status !== 'running' ? (
              <Button
                variant="contained"
                color="success"
                startIcon={<PlayArrowIcon />}
                onClick={handleStartMacListener}
                disabled={loading}
              >
                START LISTENER
              </Button>
            ) : (
              <Button
                variant="contained"
                color="error"
                startIcon={<StopIcon />}
                onClick={handleStopMacListener}
                disabled={loading}
              >
                STOP LISTENER
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>
      
      {/* Gmail Listener Control */}
      <Card sx={{ mb: 3 }}>
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
                        onClick={() => handleEnableAutoResponse('email', duration)}
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
                        checked={gmailIgnoreNoreply}
                        onChange={(e) => setGmailIgnoreNoreply(e.target.checked)}
                        disabled={gmailListenerStatus.status === 'running'}
                      />
                    }
                    label="Ignore no-reply emails"
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={gmailIgnoreSubscriptions}
                        onChange={(e) => setGmailIgnoreSubscriptions(e.target.checked)}
                        disabled={gmailListenerStatus.status === 'running'}
                      />
                    }
                    label="Ignore subscription emails"
                  />
                </Box>
                
                {gmailListenerStatus.status !== 'running' && (
                  <Button
                    variant="contained"
                    color="primary"
                    fullWidth
                    onClick={updateGmailConfig}
                    disabled={loading}
                    sx={{ mt: 2 }}
                  >
                    UPDATE CONFIGURATION
                  </Button>
                )}
              </Box>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box>
                <Typography variant="subtitle1" gutterBottom>Allowed Senders</Typography>
                {gmailAllowedSenders.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No restrictions - will respond to all senders
                  </Typography>
                ) : (
                  <List dense>
                    {gmailAllowedSenders.map((sender, index) => (
                      <ListItem key={index}>
                        <ListItemText primary={sender} />
                        <ListItemSecondaryAction>
                          <IconButton 
                            edge="end" 
                            onClick={() => handleRemoveGmailSender(sender)}
                            disabled={gmailListenerStatus.status === 'running'}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                )}
                
                <Box sx={{ display: 'flex', mt: 2 }}>
                  <TextField
                    placeholder="Sender Email"
                    value={newGmailSender}
                    onChange={(e) => setNewGmailSender(e.target.value)}
                    disabled={gmailListenerStatus.status === 'running'}
                    fullWidth
                  />
                  <Button
                    onClick={handleAddGmailSender}
                    disabled={!newGmailSender || gmailListenerStatus.status === 'running'}
                    sx={{ ml: 1 }}
                  >
                    ADD
                  </Button>
                </Box>
                
                <Button
                  variant="outlined"
                  fullWidth
                  onClick={() => setGmailAllowedSenders([])}
                  disabled={gmailAllowedSenders.length === 0 || gmailListenerStatus.status === 'running'}
                  sx={{ mt: 2 }}
                >
                  SAVE ALLOWED SENDERS
                </Button>
                
                <Divider sx={{ my: 2 }} />
                
                <Typography variant="subtitle1" gutterBottom>Credentials</Typography>
                <Button
                  variant="contained"
                  color="primary"
                  fullWidth
                  startIcon={<UploadIcon />}
                  onClick={() => setUploadDialogOpen(true)}
                  disabled={gmailListenerStatus.status === 'running'}
                >
                  UPLOAD CREDENTIALS
                </Button>
              </Box>
            </Grid>
          </Grid>
          
          <Divider sx={{ my: 2 }} />
          
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
            {gmailListenerStatus.status !== 'running' ? (
              <Button
                variant="contained"
                color="success"
                startIcon={<PlayArrowIcon />}
                onClick={startGmailListener}
                disabled={loading || !gmailListenerStatus.has_credentials}
              >
                START LISTENER
              </Button>
            ) : (
              <Button
                variant="contained"
                color="error"
                startIcon={<StopIcon />}
                onClick={stopGmailListener}
                disabled={loading}
              >
                STOP LISTENER
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>
      
      {/* Pending Email Responses Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              <EmailIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Pending Email Responses
            </Typography>
            <Button 
              size="small" 
              startIcon={<RefreshIcon />} 
              onClick={fetchPendingEmails}
            >
              Refresh
            </Button>
          </Box>
          
          <Divider sx={{ mb: 2 }} />
          
          {pendingEmails.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
              No pending email responses
            </Typography>
          ) : (
            <List>
              {pendingEmails.map((email) => (
                <Paper key={email.id} sx={{ mb: 2, p: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                    Subject: {email.email_details.subject}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    From: {email.email_details.sender}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Received: {new Date(parseInt(email.email_details.timestamp)).toLocaleString()}
                  </Typography>
                  
                  <Box sx={{ mt: 2, mb: 2 }}>
                    <Typography variant="subtitle2">Original Email:</Typography>
                    <Paper variant="outlined" sx={{ p: 1, mb: 2, maxHeight: '300px', overflow: 'auto' }}>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {email.email_details.body}
                      </Typography>
                    </Paper>
                    
                    <Typography variant="subtitle2">Generated Response:</Typography>
                    <Paper variant="outlined" sx={{ p: 1, maxHeight: '150px', overflow: 'auto' }}>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {email.response}
                      </Typography>
                    </Paper>
                  </Box>
                  
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                    <Button 
                      variant="outlined" 
                      color="error" 
                      onClick={() => handleRejectEmail(email.id)}
                      startIcon={<CloseIcon />}
                    >
                      Reject
                    </Button>
                    <Button 
                      variant="contained" 
                      color="success" 
                      onClick={() => handleApproveEmail(email.id)}
                      startIcon={<CheckIcon />}
                    >
                      Approve & Send
                    </Button>
                  </Box>
                </Paper>
              ))}
            </List>
          )}
        </CardContent>
      </Card>
      
      {/* Message Log Section */}
      <Box mt={4}>
        <Card>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="h6">Message Log</Typography>
              <Button 
                variant="outlined" 
                color="primary" 
                onClick={() => setShowMessageLog(!showMessageLog)}
              >
                {showMessageLog ? 'Hide Log' : 'Show Log'}
              </Button>
            </Box>
            
            {showMessageLog && (
              <>
                <Box mt={2} mb={2} display="flex" justifyContent="space-between" alignItems="center">
                  <Button 
                    variant="contained" 
                    color="primary" 
                    onClick={() => {
                      fetchMessageLog();
                      fetchTerminalOutput();
                      fetchGmailTerminalOutput();
                    }}
                    startIcon={<RefreshIcon />}
                    size="small"
                  >
                    Refresh Log
                  </Button>
                  
                  <Box>
                    <Button
                      variant="outlined"
                      color="secondary"
                      onClick={() => setShowTerminalOutput(!showTerminalOutput)}
                      size="small"
                      sx={{ mr: 1 }}
                    >
                      {showTerminalOutput ? 'Hide Mac Output' : 'Show Mac Output'}
                    </Button>
                    
                    <Button
                      variant="outlined"
                      color="info"
                      onClick={() => setShowGmailTerminalOutput(!showGmailTerminalOutput)}
                      size="small"
                    >
                      {showGmailTerminalOutput ? 'Hide Gmail Output' : 'Show Gmail Output'}
                    </Button>
                  </Box>
                </Box>
                
                {showTerminalOutput && (
                  <Box 
                    maxHeight="200px" 
                    overflow="auto" 
                    border="1px solid #eee" 
                    p={2} 
                    borderRadius={1} 
                    mb={2}
                    bgcolor="#f5f5f5"
                    fontFamily="monospace"
                    fontSize="0.8rem"
                    whiteSpace="pre-wrap"
                  >
                    <Typography variant="subtitle2" gutterBottom>Mac Message Listener Output:</Typography>
                    {terminalOutput ? terminalOutput : 'No terminal output available'}
                  </Box>
                )}
                
                {showGmailTerminalOutput && (
                  <Box 
                    maxHeight="200px" 
                    overflow="auto" 
                    border="1px solid #eee" 
                    p={2} 
                    borderRadius={1} 
                    mb={2}
                    bgcolor="#f5f5f5"
                    fontFamily="monospace"
                    fontSize="0.8rem"
                    whiteSpace="pre-wrap"
                  >
                    <Typography variant="subtitle2" gutterBottom>Gmail Listener Output:</Typography>
                    {gmailTerminalOutput ? gmailTerminalOutput : 'No Gmail terminal output available'}
                  </Box>
                )}
                
                <Box maxHeight="300px" overflow="auto" border="1px solid #eee" p={2} borderRadius={1}>
                  {messageLog.length > 0 ? (
                    <List>
                      {messageLog.map((message, index) => (
                        <ListItem
                          key={index}
                          divider={index < messageLog.length - 1}
                          sx={{
                            backgroundColor: message.from === 'Contact' ? 'rgba(0, 0, 0, 0.02)' : 'transparent'
                          }}
                        >
                          <ListItemText
                            primary={
                              <Typography>
                                <strong>{message.from}</strong> - {new Date(message.timestamp).toLocaleString()}
                              </Typography>
                            }
                            secondary={
                              <Box sx={{ mt: 1 }}>
                                <Typography 
                                  variant="body2" 
                                  component="div" 
                                  sx={{ 
                                    mb: message.response ? 1.5 : 0,
                                    p: 1,
                                    borderRadius: 1,
                                    backgroundColor: message.from === 'Contact' ? 'rgba(0, 0, 0, 0.05)' : 'transparent',
                                    display: 'inline-block',
                                    maxWidth: '85%'
                                  }}
                                >
                                  {message.text}
                                </Typography>
                                
                                {message.response && (
                                  <Typography 
                                    variant="body2" 
                                    color="primary" 
                                    component="div" 
                                    sx={{ 
                                      p: 1, 
                                      borderRadius: 1,
                                      backgroundColor: 'rgba(33, 150, 243, 0.05)',
                                      display: 'inline-block',
                                      maxWidth: '85%',
                                      ml: 'auto',
                                      textAlign: 'right'
                                    }}
                                  >
                                    {message.response}
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Typography color="textSecondary">No messages in log</Typography>
                  )}
                </Box>
              </>
            )}
          </CardContent>
        </Card>
      </Box>
      
      {/* Credentials Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={() => setUploadDialogOpen(false)}>
        <DialogTitle>Upload Gmail API Credentials</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph sx={{ mt: 1 }}>
            Upload your credentials.json file from the Google Cloud Console to enable Gmail integration.
          </Typography>
          
          <Box sx={{ mt: 2 }}>
            <input
              accept=".json"
              style={{ display: 'none' }}
              id="credentials-file-upload"
              type="file"
              onChange={(e) => setCredentialFile(e.target.files[0])}
            />
            <label htmlFor="credentials-file-upload">
              <Button variant="outlined" component="span" startIcon={<UploadIcon />}>
                Select Credentials File
              </Button>
            </label>
            
            {credentialFile && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                Selected: {credentialFile.name}
              </Typography>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleCredentialUpload} 
            color="primary" 
            disabled={!credentialFile}
          >
            Upload
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AutoResponsePage;
