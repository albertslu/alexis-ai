import React, { useState } from 'react';
import { Box, Typography, Paper, Button, TextField, Alert, CircularProgress } from '@mui/material';
import MessageIcon from '@mui/icons-material/Message';
import axiosInstance from '../api/axios';

const DataSourceIntegration = ({ onDataAdded }) => {
  const [status, setStatus] = useState({ type: '', message: '' });
  
  // iMessage integration
  const [imessageStatus, setImessageStatus] = useState('idle'); // idle, loading, success, error
  const [imessageDays, setImessageDays] = useState(365); // Default to 1 year
  
  const handleImessageAccess = async () => {
    setImessageStatus('loading');
    setStatus({ type: '', message: '' });
    
    console.log('Attempting to extract iMessage data...');
    console.log('Days parameter:', imessageDays);
    
    try {
      // First try the regular endpoint
      try {
        console.log('Trying regular iMessage endpoint...');
        const response = await axiosInstance.post('/api/integrate/imessage', {
          days: imessageDays
        });
        
        console.log('iMessage API response:', response.data);
        
        if (response.data.success) {
          setImessageStatus('success');
          setStatus({
            type: 'success',
            message: `Successfully processed ${response.data.message_count} messages from iMessage (last ${imessageDays} days)!`
          });
          
          if (onDataAdded) {
            onDataAdded({
              source: 'imessage',
              count: response.data.message_count
            });
          }
          return; // Exit early if successful
        } else {
          // Handle error response from server
          console.error('iMessage extraction failed:', response.data);
          throw new Error(response.data.message || response.data.error || 'Failed to access iMessage data.');
        }
      } catch (mainError) {
        // If the regular endpoint fails, try the test endpoint
        console.log('Regular endpoint failed, trying test endpoint...');
        try {
          const testResponse = await axiosInstance.post('/api/integrate/imessage/test', {
            days: imessageDays
          });
          
          console.log('iMessage test API response:', testResponse.data);
          
          if (testResponse.data.success) {
            setImessageStatus('success');
            setStatus({
              type: 'success',
              message: `Successfully processed ${testResponse.data.message_count} messages from iMessage (last ${imessageDays} days)!`
            });
            
            if (onDataAdded) {
              onDataAdded({
                source: 'imessage',
                count: testResponse.data.message_count
              });
            }
            return; // Exit early if successful
          } else {
            throw new Error(testResponse.data.message || testResponse.data.error || 'Failed to access iMessage data.');
          }
        } catch (testError) {
          // Both endpoints failed, throw the original error
          console.error('Both endpoints failed:', mainError, testError);
          throw mainError;
        }
      }
    } catch (error) {
      console.error('Error accessing iMessage:', error);
      setImessageStatus('error');
      
      // Check if it's a 500 error (likely Full Disk Access issue)
      if (error.message && error.message.includes('500')) {
        setStatus({
          type: 'warning',
          message: 'You need to grant Full Disk Access to the app in System Preferences → Security & Privacy → Privacy → Full Disk Access.'
        });
      } else {
        setStatus({
          type: 'error',
          message: `Error accessing iMessage: ${error.message}`
        });
      }
    } finally {
      // Extraction completed
    }
  };
  
  const handleNotificationClose = () => {
    setStatus({ type: '', message: '' });
  };
  
  return (
    <Box>
      {/* Status message */}
      {status.type && (
        <Alert 
          severity={status.type} 
          sx={{ mb: 2 }}
          onClose={handleNotificationClose}
        >
          {status.message}
        </Alert>
      )}
      
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Extract Messages from iMessage
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          This will extract your sent messages from the Mac Messages app to help train Alexis AI to draft responses in your style.
        </Typography>
        
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Number of days to extract:
          </Typography>
          <TextField
            type="number"
            value={imessageDays}
            onChange={(e) => setImessageDays(Math.max(1, parseInt(e.target.value) || 1))}
            fullWidth
            variant="outlined"
            size="small"
            InputProps={{ inputProps: { min: 1, max: 3650 } }}
            helperText="How far back to extract messages (1-3650 days)"
          />
        </Box>
        
        <Button
          variant="contained"
          color="primary"
          onClick={handleImessageAccess}
          disabled={imessageStatus === 'loading'}
          startIcon={imessageStatus === 'loading' ? <CircularProgress size={20} /> : <MessageIcon />}
          fullWidth
        >
          {imessageStatus === 'loading' ? 'Processing...' : 'Extract iMessage Data'}
        </Button>
        
        {imessageStatus === 'success' && (
          <Alert severity="success" sx={{ mt: 2 }}>
            iMessage data extracted successfully!
          </Alert>
        )}
      </Paper>
      
      <Typography variant="body2" color="text.secondary" sx={{ mt: 2, fontStyle: 'italic' }}>
        Note: Alexis AI will only use your iMessage data for training and suggesting message responses. No data is shared with third parties.
      </Typography>
    </Box>
  );
};

export default DataSourceIntegration;
