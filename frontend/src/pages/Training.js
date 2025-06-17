import React, { useState, useEffect } from 'react';
import { Container, Typography, Button, Box, Paper, CircularProgress, Alert, Snackbar, Divider } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import axios from '../api/axios';
import DataSourceIntegration from '../components/DataSourceIntegration';

const Training = () => {
  // We'll keep the navigate hook for potential future use
  const navigate = useNavigate();
  const [dataSourcesAdded, setDataSourcesAdded] = useState([]);
  const [fineTuningInProgress, setFineTuningInProgress] = useState(false);
  const [fineTuningComplete, setFineTuningComplete] = useState(false);
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  const [isResettingTraining, setIsResettingTraining] = useState(false);
  
  // Authentication and training state
  const [isGmailAuthenticated, setIsGmailAuthenticated] = useState(false);
  const [isCombiningData, setIsCombiningData] = useState(false);
  const [combinedTrainingResult, setCombinedTrainingResult] = useState(null);

  // Test API connection and check fine-tuning status on component mount
  useEffect(() => {
    const initializeApp = async () => {
      console.log('Initializing Training page...');
      
      // Test basic API connectivity
      try {
        console.log('Testing API connection...');
        const response = await axios.get('/api/test');
        console.log('✅ Test endpoint response:', response.data);
      } catch (error) {
        console.error('❌ Error testing API connection:', error);
        // Don't show notification yet, let's try the other endpoints
      }
      
      // Check fine-tuning status - independent of other API calls
      try {
        console.log('Checking fine-tuning status...');
        await fetchTrainingStatus();
        console.log('✅ Fine-tuning status checked successfully');
      } catch (error) {
        console.error('❌ Error checking fine-tuning status:', error);
        // Only show notification if this specific call fails
        setNotification({
          open: true,
          message: `Could not check training status: ${error.message}. Some features may be limited.`,
          severity: 'warning'
        });
      }
      
      // Check Gmail authentication status - independent of other API calls
      try {
        console.log('Checking Gmail authentication status...');
        await checkGmailAuthStatus();
        console.log('✅ Gmail authentication status checked successfully');
      } catch (error) {
        console.error('❌ Error checking Gmail authentication:', error);
        // Don't show notification for this, it's not critical
      }
    };
    
    initializeApp();
    
    // Set up interval to check fine-tuning status every 30 seconds
    const statusCheckInterval = setInterval(async () => {
      if (fineTuningInProgress && !fineTuningComplete) {
        try {
          const statusResponse = await axios.get('/api/fine-tuning-status');
          if (statusResponse.data.trained) {
            setFineTuningInProgress(false);
            setFineTuningComplete(true);
            setNotification({
              open: true,
              message: 'Your Alexis AI has been successfully trained and is ready to chat!',
              severity: 'success'
            });
          }
        } catch (error) {
          console.error('Error checking fine-tuning status:', error);
        }
      }
    }, 30000);
    
    return () => clearInterval(statusCheckInterval);
  }, [fineTuningInProgress, fineTuningComplete]);

  const fetchTrainingStatus = async () => {
    try {
      const statusResponse = await axios.get('/api/fine-tuning-status');
      console.log('Fine-tuning status:', statusResponse.data);
      
      // Update state based on the response
      setFineTuningInProgress(statusResponse.data.in_progress);
      setFineTuningComplete(statusResponse.data.trained);
      
      return statusResponse.data;
    } catch (error) {
      console.error('Error fetching training status:', error);
      setNotification({
        open: true,
        message: 'Error checking training status',
        severity: 'error'
      });
    }
  };

  // This function is no longer needed as we're using the GmailOAuthButton component
  // in the DataSourceIntegration component
  
  // Check Gmail authentication on component mount
  useEffect(() => {
    checkGmailAuthStatus();
  }, []);

  // Handle combining data and retraining
  const handleCombineDataAndRetrain = async () => {
    setIsCombiningData(true);
    setCombinedTrainingResult(null);
    
    try {
      // Use the new lightweight endpoint that starts training in the background
      const response = await axios.post('/api/start-training');
      
      // Training has started in the background, update UI accordingly
      setCombinedTrainingResult({
        success: true,
        message: response.data.message || 'Training process started in the background. This may take 30-60 minutes to complete.'
      });
      
      // Show notification
      setNotification({
        open: true,
        message: response.data.message || 'Your Alexis AI training has started in the background. This process typically takes 30-60 minutes to complete.',
        severity: 'info'
      });
      
      // Set fine-tuning in progress to enable status polling
      setFineTuningInProgress(true);
      fetchTrainingStatus();
      
    } catch (error) {
      console.error('Error starting training process:', error);
      setCombinedTrainingResult({
        success: false,
        message: error.response?.data?.message || error.message
      });
      
      // Show error notification
      setNotification({
        open: true,
        message: `Error starting training process: ${error.response?.data?.message || error.message}`,
        severity: 'error'
      });
    } finally {
      setIsCombiningData(false);
    }
  };

  // Check Gmail authentication status using the new OAuth handler
  const checkGmailAuthStatus = async () => {
    try {
      // Get the current user ID from the auth token if available
      const user = localStorage.getItem('user');
      const userId = user ? JSON.parse(user).id : 'default';
      
      // Add the user_id as a query parameter
      const response = await axios.get(`/api/oauth/status/gmail?user_id=${userId}`);
      setIsGmailAuthenticated(response.data.authenticated);
      return response.data; // Return the data for the caller
    } catch (error) {
      console.error('Error checking Gmail auth status:', error);
      // Don't throw the error, just return a default value
      return { authenticated: false, error: error.message };
    }
  };

  // This function is now handled in the DataSourceIntegration component
  // with the GmailOAuthButton and email extraction UI

  // Handle data source added
  const handleDataSourceAdded = (data) => {
    console.log('Data source added:', data);
    
    // Add to data sources array
    setDataSourcesAdded(prev => {
      // Check if this source type already exists
      if (!prev.some(source => source.source === data.source)) {
        return [...prev, data];
      }
      return prev;
    });
    
    // Show notification
    setNotification({
      open: true,
      message: `Successfully added ${data.source} data!`,
      severity: 'success'
    });
  };

  // Handle notification close
  const handleNotificationClose = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setNotification({ ...notification, open: false });
  };

  // Render Gmail authentication and extraction UI
  // This section is now handled in the DataSourceIntegration component
  const renderGmailSection = () => {
    // Return empty since Gmail integration is now in the DataSourceIntegration component
    return null;
  };

  // Render the combine data and retrain UI
  const renderCombineDataSection = () => {
    const hasDataSources = dataSourcesAdded.length > 0 || isGmailAuthenticated;
    
    return (
      <Box sx={{ mt: 4 }}>
        <Divider sx={{ mb: 3 }} />
        
        <Typography variant="h6" gutterBottom>
          Train Your Alexis AI
        </Typography>
        
        {!hasDataSources ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            Add at least one data source above before training your Alexis AI.
          </Alert>
        ) : (
          <>
            <Typography variant="body2" paragraph>
              Combine your data sources and start training your Alexis AI. This process will:
              <ul>
                <li>Combine all your data sources (iMessage, Gmail)</li>
                <li>Build a personalized RAG database</li>
                <li>Create Letta memories from your data</li>
                <li>Fine-tune a GPT-4o-mini model on your communication style</li>
              </ul>
            </Typography>
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Data sources ready for training:
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {dataSourcesAdded.map((source, index) => (
                  <Paper key={index} sx={{ px: 2, py: 1, bgcolor: 'primary.light', color: 'white' }}>
                    <Typography variant="body2">
                      {source.source.charAt(0).toUpperCase() + source.source.slice(1)} {source.count ? `(${source.count})` : ''}
                    </Typography>
                  </Paper>
                ))}
                {isGmailAuthenticated && !dataSourcesAdded.some(source => source.source === 'email') && (
                  <Paper sx={{ px: 2, py: 1, bgcolor: 'primary.light', color: 'white' }}>
                    <Typography variant="body2">
                      Gmail (authenticated)
                    </Typography>
                  </Paper>
                )}
              </Box>
            </Box>
            
            <Button 
              variant="contained" 
              color="primary" 
              size="large"
              fullWidth
              onClick={handleCombineDataAndRetrain}
              disabled={isCombiningData || fineTuningInProgress}
              startIcon={isCombiningData ? <CircularProgress size={20} /> : null}
              sx={{ mb: 2 }}
            >
              {isCombiningData ? 'Processing...' : fineTuningInProgress ? 'Training in Progress...' : 'Process iMessage Data & Train Alexis AI'}
            </Button>
            
            {fineTuningInProgress && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Alexis AI is currently being trained. This process may take some time (typically 1-2 hours). You can close this page and come back later.
              </Alert>
            )}
            
            {fineTuningComplete && (
              <Alert severity="success" sx={{ mb: 2 }}>
                Alexis AI has been successfully trained and is ready to use! Go to the Chat page to test your message drafts.
              </Alert>
            )}
            
            {combinedTrainingResult && (
              <Paper elevation={2} sx={{ p: 2, mb: 3, bgcolor: combinedTrainingResult.success ? 'success.light' : 'error.light' }}>
                <Typography variant="body1">
                  {combinedTrainingResult.message}
                </Typography>
                {combinedTrainingResult.success && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="body2">
                      iMessages: {combinedTrainingResult.imessage_count || 0}
                    </Typography>
                    <Typography variant="body2">
                      Total training examples: {combinedTrainingResult.total_count || 0}
                    </Typography>
                  </Box>
                )}
              </Paper>
            )}
          </>
        )}
      </Box>
    );
  };

  const handleResetTraining = async () => {
    try {
      setIsResettingTraining(true);
      const response = await axios.post('/api/reset-training-status');
      
      if (response.data.success) {
        setNotification({
          open: true,
          message: 'Training status reset successfully. You can now start a new training job.',
          severity: 'success'
        });
        
        // Update UI state
        setFineTuningComplete(false);
        setFineTuningInProgress(false);
        setCombinedTrainingResult(null);
        
        // Refresh training status
        await fetchTrainingStatus();
      } else {
        setNotification({
          open: true,
          message: response.data.message || 'Failed to reset training status.',
          severity: 'error'
        });
      }
    } catch (error) {
      console.error('Error resetting training status:', error);
      setNotification({
        open: true,
        message: `Error resetting training status: ${error.message}`,
        severity: 'error'
      });
    } finally {
      setIsResettingTraining(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 8, minHeight: 'calc(100vh - 200px)' }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h5">
            Train Alexis AI
          </Typography>
          
          {fineTuningComplete && (
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button 
                variant="outlined" 
                color="secondary"
                size="medium"
                onClick={handleResetTraining}
                disabled={isResettingTraining}
                startIcon={isResettingTraining ? <CircularProgress size={20} /> : null}
                sx={{ height: 40 }}
              >
                {isResettingTraining ? 'Resetting...' : 'Reset Training'}
              </Button>
              <Button 
                variant="contained" 
                color="success"
                size="medium"
                onClick={() => navigate('/chat')}
                sx={{ height: 40 }}
              >
                Go to Chat Page
              </Button>
            </Box>
          )}
          
          {fineTuningInProgress && !fineTuningComplete && (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body2" color="primary" sx={{ mr: 1 }}>
                Training in progress...
              </Typography>
              <CircularProgress size={20} />
            </Box>
          )}
        </Box>
        
        <Typography variant="body1" paragraph>
          Create your personalized message drafting assistant by giving it access to your iMessage data. The more data you provide, the more accurately Alexis AI will reflect your communication style.
        </Typography>
        
        <Alert severity="info" sx={{ mb: 3 }}>
          Your data is processed locally and used only to train Alexis AI to draft messages in your style. We never share your data with third parties.
        </Alert>
        
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            iMessage Data
          </Typography>
          <DataSourceIntegration onDataAdded={handleDataSourceAdded} />
        </Box>
        
        {/* Gmail integration is now handled in the DataSourceIntegration component */}
        
        {renderCombineDataSection()}
      </Paper>
      
      <Snackbar 
        open={notification.open} 
        autoHideDuration={6000} 
        onClose={handleNotificationClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleNotificationClose} severity={notification.severity} sx={{ width: '100%' }}>
          {notification.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default Training;
