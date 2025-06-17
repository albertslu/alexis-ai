import React from 'react';
import { Box, Typography, Button, Container, Grid, Paper, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import EmailIcon from '@mui/icons-material/Email';
import MessageIcon from '@mui/icons-material/Message';
import PersonIcon from '@mui/icons-material/Person';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import SpeedIcon from '@mui/icons-material/Speed';
import SecurityIcon from '@mui/icons-material/Security';
import DownloadIcon from '@mui/icons-material/Download';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: '#f5f7fa' }}>
      {/* Hero Section */}
      <Box 
        sx={{ 
          py: 10, 
          background: 'linear-gradient(45deg, #2196f3 30%, #21cbf3 90%)',
          color: 'white'
        }}
      >
        <Container maxWidth="lg">
          <Grid container spacing={6} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="h2" component="h1" gutterBottom fontWeight="bold">
                Your Personal Alexis AI
              </Typography>
              <Typography variant="h5" paragraph>
                Get smart iMessage suggestions in your own communication style
              </Typography>
              <Box sx={{ mt: 4 }}>
                <Button 
                  variant="contained" 
                  size="large" 
                  onClick={() => navigate('/signup')}
                  sx={{ 
                    mr: 2, 
                    bgcolor: 'white', 
                    color: '#2196f3',
                    '&:hover': {
                      bgcolor: '#f0f0f0',
                    }
                  }}
                >
                  Sign Up
                </Button>
                <Button 
                  variant="outlined" 
                  size="large" 
                  onClick={() => navigate('/login')}
                  sx={{ 
                    color: 'white', 
                    borderColor: 'white',
                    mr: 2,
                    '&:hover': {
                      borderColor: '#f0f0f0',
                      bgcolor: 'rgba(255,255,255,0.1)',
                    }
                  }}
                >
                  Login
                </Button>
                <Button 
                  variant="outlined" 
                  size="large" 
                  href="https://aiclone-downloads.s3.amazonaws.com/Alexis%20AI-1.0.0.dmg"
                  startIcon={<DownloadIcon />}
                  sx={{ 
                    color: 'white', 
                    borderColor: 'white',
                    '&:hover': {
                      borderColor: '#f0f0f0',
                      bgcolor: 'rgba(255,255,255,0.1)',
                    }
                  }}
                >
                  Download App
                </Button>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box 
                sx={{ 
                  width: '100%', 
                  maxWidth: 500,
                  display: { xs: 'none', md: 'block' },
                  mx: 'auto',
                  borderRadius: 2,
                  overflow: 'hidden',
                  boxShadow: 3
                }}
              >
                <video
                  autoPlay
                  muted
                  loop
                  playsInline
                  style={{ width: '100%', height: 'auto' }}
                >
                  <source src="/demo-video.mp4" type="video/mp4" />
                  Your browser does not support the video tag.
                </video>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Typography variant="h3" component="h2" align="center" gutterBottom>
          How It Works
        </Typography>
        <Typography variant="h6" align="center" color="textSecondary" paragraph>
          Ready to create your Alexis AI in three simple steps
        </Typography>
        
        <Grid container spacing={4} sx={{ mt: 4 }}>
          <Grid item xs={12} md={4}>
            <Paper elevation={2} sx={{ p: 3, height: '100%', borderRadius: 2 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 2 }}>
                <Box
                  sx={{
                    bgcolor: '#e3f2fd',
                    borderRadius: '50%',
                    p: 2,
                    mb: 2
                  }}
                >
                  <PersonIcon fontSize="large" color="primary" />
                </Box>
                <Typography variant="h5" component="h3" gutterBottom>
                  Connect Your Data
                </Typography>
              </Box>
              <Typography align="center">
                Link your iMessages to provide training data.
              </Typography>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Paper elevation={2} sx={{ p: 3, height: '100%', borderRadius: 2 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 2 }}>
                <Box
                  sx={{
                    bgcolor: '#e3f2fd',
                    borderRadius: '50%',
                    p: 2,
                    mb: 2
                  }}
                >
                  <AutorenewIcon fontSize="large" color="primary" />
                </Box>
                <Typography variant="h5" component="h3" gutterBottom>
                  Alexis
                </Typography>
              </Box>
              <Typography align="center">
                Our system analyzes your communication style and creates your personalized Alexis AI.
              </Typography>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Paper elevation={2} sx={{ p: 3, height: '100%', borderRadius: 2 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 2 }}>
                <Box
                  sx={{
                    bgcolor: '#e3f2fd',
                    borderRadius: '50%',
                    p: 2,
                    mb: 2
                  }}
                >
                  <MessageIcon fontSize="large" color="primary" />
                </Box>
                <Typography variant="h5" component="h3" gutterBottom>
                  Auto-Respond
                </Typography>
              </Box>
              <Typography align="center">
                Generate iMessages for you in your style.
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Container>

      {/* Benefits Section */}
      <Box sx={{ bgcolor: '#f0f7ff', py: 8 }}>
        <Container maxWidth="lg">
          <Typography variant="h3" component="h2" align="center" gutterBottom>
            Benefits
          </Typography>
          
          <Grid container spacing={6} sx={{ mt: 2 }}>
            <Grid item xs={12} md={6}>
              <List>
                <ListItem>
                  <ListItemIcon>
                    <CheckCircleIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Save Time" 
                    secondary="Reduce time spent on routine communications"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <CheckCircleIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Maintain Relationships" 
                    secondary="Stay connected even when you're busy"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <CheckCircleIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Reduce Digital Overwhelm" 
                    secondary="Let your AI handle routine messages"
                  />
                </ListItem>
              </List>
            </Grid>
            <Grid item xs={12} md={6}>
              <List>
                <ListItem>
                  <ListItemIcon>
                    <SpeedIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Highly Personalized" 
                    secondary="Trained specifically on your communication patterns"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <SecurityIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Private & Secure" 
                    secondary="Your data is processed locally and never shared"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <EmailIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Multi-Channel Support" 
                    secondary="Works with emails, texts, and professional messages"
                  />
                </ListItem>
              </List>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* CTA Section */}
      <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
        <Typography variant="h3" component="h2" gutterBottom>
          Ready to create your Alexis AI?
        </Typography>
        <Typography variant="h6" color="textSecondary" paragraph>
          Join our early access program and be among the first to experience the future of communication.
        </Typography>
        <Button 
          variant="contained" 
          color="primary" 
          size="large"
          onClick={() => navigate('/signup')}
          sx={{ mt: 2 }}
        >
          Get Started Now
        </Button>
      </Container>

      {/* Footer */}
      <Box sx={{ bgcolor: '#1976d2', color: 'white', py: 3 }}>
        <Container maxWidth="lg">
          <Typography variant="body2" align="center">
            &copy; {new Date().getFullYear()} Alexis AI. All rights reserved.
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default LandingPage;
