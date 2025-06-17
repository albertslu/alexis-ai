import React, { useState, useEffect } from 'react';
import { Container, Typography, Paper, Box, Button, Grid, Divider, Card, CardContent } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import SettingsIcon from '@mui/icons-material/Settings';
import { useNavigate } from 'react-router-dom';

const AccountPage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    // Get user data from localStorage
    const userJson = localStorage.getItem('user');
    if (userJson) {
      try {
        const userData = JSON.parse(userJson);
        setUser(userData);
      } catch (error) {
        console.error('Error parsing user data:', error);
      }
    }
  }, []);

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        My Account
      </Typography>
      
      <Grid container spacing={4}>
        {/* Account Information */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Box display="flex" alignItems="center" mb={2}>
              <AccountCircleIcon fontSize="large" sx={{ mr: 2, color: 'primary.main' }} />
              <Typography variant="h5">Account Information</Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />
            
            {user ? (
              <Box>
                <Typography variant="body1"><strong>Name:</strong> {user.name || 'Not provided'}</Typography>
                <Typography variant="body1"><strong>Email:</strong> {user.email}</Typography>
                <Typography variant="body1"><strong>Account Created:</strong> {new Date(user.created_at || Date.now()).toLocaleDateString()}</Typography>
              </Box>
            ) : (
              <Typography>Loading account information...</Typography>
            )}
          </Paper>
          
          <Paper sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" mb={2}>
              <SettingsIcon fontSize="large" sx={{ mr: 2, color: 'primary.main' }} />
              <Typography variant="h5">Preferences</Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />
            
            <Typography variant="body1" paragraph>
              Web access is limited to account management. For full functionality, please download the desktop app.
            </Typography>
            
            <Button 
              variant="contained" 
              color="primary" 
              startIcon={<DownloadIcon />}
              onClick={() => navigate('/download')}
            >
              Download Desktop App
            </Button>
          </Paper>
        </Grid>
        
        {/* Usage Stats */}
        <Grid item xs={12} md={4}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>App Status</Typography>
              <Typography variant="body2" color="text.secondary">
                For full functionality including training, chat, and iMessage integration, please use the desktop app.
              </Typography>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Need Help?</Typography>
              <Typography variant="body2" paragraph>
                If you have any questions or need assistance with your account, please contact our support team.
              </Typography>
              <Button variant="outlined" size="small" fullWidth>
                Contact Support
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default AccountPage;
