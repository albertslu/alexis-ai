import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Grid, 
  Button, 
  Card, 
  CardContent, 
  CardActions,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Alert
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import MessageIcon from '@mui/icons-material/Message';
import EmailIcon from '@mui/icons-material/Email';
import SpeedIcon from '@mui/icons-material/Speed';
import ModelTrainingIcon from '@mui/icons-material/ModelTraining';
import { useAuth } from '../contexts/AuthContext';
import axios from '../api/axios';
import { useNavigate } from 'react-router-dom';

const Dashboard = () => {
  const { currentUser, getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [trainingStatus, setTrainingStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Fetch training status on component mount
  useEffect(() => {
    const fetchTrainingStatus = async () => {
      try {
        setIsLoading(true);
        const response = await axios.get('/api/training/status', {
          headers: getAuthHeader()
        });
        setTrainingStatus(response.data);
        setError(null);
      } catch (err) {
        console.error('Error fetching training status:', err);
        setError('Failed to load training status');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchTrainingStatus();
  }, [getAuthHeader]);
  
  // Navigate to different sections
  const navigateToIMessage = () => navigate('/imessage');
  const navigateToTraining = () => navigate('/training');
  const navigateToDataSources = () => navigate('/training#data-sources');
  
  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      {/* Welcome Section */}
      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Welcome to Alexis AI, {currentUser?.name || 'User'}!
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Text at the speed of thought with AI-powered message suggestions. Alexis AI analyzes your conversation context 
          and provides personalized message suggestions that match your communication style.
        </Typography>
        <Typography variant="body2" color="text.secondary">
          <strong>How it works:</strong> Open iMessage, and Alexis AI will automatically detect your active conversations 
          and provide contextual suggestions in real-time through a subtle overlay.
        </Typography>
      </Paper>
      
      {/* Status Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Alexis AI Status Card */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <ModelTrainingIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Alexis AI Status
              </Typography>
              <Divider sx={{ my: 1 }} />
              
              {isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : error ? (
                <Alert severity="error">{error}</Alert>
              ) : (
                <List dense>
                  <ListItem>
                    <ListItemText 
                      primary="Training Status" 
                      secondary={trainingStatus?.trained ? 'Ready for Message Suggestions' : 'Needs Training'} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Model" 
                      secondary={trainingStatus?.model_id ? 'Personalized Model Active' : 'Using Base Model'} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Last Updated" 
                      secondary={trainingStatus?.last_updated ? new Date(trainingStatus.last_updated).toLocaleString() : 'Never'} 
                    />
                  </ListItem>
                </List>
              )}
            </CardContent>
            <CardActions>
              <Button 
                variant="contained" 
                color="primary" 
                onClick={navigateToTraining}
                disabled={isLoading}
              >
                {trainingStatus?.trained ? 'Retrain Alexis AI' : 'Train Alexis AI'}
              </Button>
              {trainingStatus?.trained && (
                <Button 
                  variant="outlined" 
                  onClick={navigateToIMessage}
                  disabled={isLoading}
                >
                  Launch iMessage Suggestions
                </Button>
              )}
            </CardActions>
          </Card>
        </Grid>
        
        {/* Data Sources Card */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Training Data Sources
              </Typography>
              <Divider sx={{ my: 1 }} />
              
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    <MessageIcon />
                  </ListItemIcon>
                  <ListItemText 
                    primary="iMessage History" 
                    secondary="Train Alexis AI on your messaging style from your iMessage conversations" 
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <EmailIcon />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Gmail (Optional)" 
                    secondary="Include email writing style for more comprehensive training" 
                  />
                </ListItem>
              </List>
            </CardContent>
            <CardActions>
              <Button 
                variant="contained" 
                color="primary" 
                onClick={navigateToDataSources}
              >
                Configure Training Data
              </Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>
      
      {/* Quick Actions */}
      <Typography variant="h5" gutterBottom>
        Quick Actions
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={4}>
          <Button 
            variant="outlined" 
            fullWidth 
            startIcon={<SpeedIcon />}
            onClick={navigateToIMessage}
            sx={{ py: 1.5 }}
          >
            Launch Message Suggestions
          </Button>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Button 
            variant="outlined" 
            fullWidth 
            startIcon={<ModelTrainingIcon />}
            onClick={navigateToTraining}
            sx={{ py: 1.5 }}
          >
            Training & Setup
          </Button>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Button 
            variant="outlined" 
            fullWidth 
            startIcon={<PersonIcon />}
            onClick={() => navigate('/feedback')}
            sx={{ py: 1.5 }}
          >
            Provide Feedback
          </Button>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
