import React from 'react';
import { Typography, Button, Container, Paper, Box } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const Welcome = () => {
  const navigate = useNavigate();

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ p: 4, mt: 4, textAlign: 'center' }}>
        <Box className="clone-avatar">AI</Box>
        <Typography variant="h2" gutterBottom>
          Welcome to Alexis AI
        </Typography>
        <Typography variant="h5" color="textSecondary" paragraph>
          Instantly draft iMessages for you
        </Typography>
        <Typography paragraph sx={{ mb: 4 }}>
          Alexis AI provides contextual message suggestions to help you respond quickly and naturally in your conversations.
          Train it on your communication style, then get real-time suggestions as you text in iMessage.
        </Typography>
        <Button 
          variant="contained" 
          size="large" 
          onClick={() => navigate('/training')}
          sx={{ mr: 2 }}
        >
          Start Training
        </Button>
        <Button 
          variant="outlined" 
          size="large" 
          onClick={() => navigate('/imessage')}
        >
          Launch Message Suggestions
        </Button>
      </Paper>
    </Container>
  );
};

export default Welcome;
