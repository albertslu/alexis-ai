import React from 'react';
import { Container, Typography, Paper, Box, Divider, Grid, Card, CardContent, Button } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import MessageIcon from '@mui/icons-material/Message';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import ChatIcon from '@mui/icons-material/Chat';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SpeedIcon from '@mui/icons-material/Speed';
import StyleIcon from '@mui/icons-material/Style';

const HowItWorks = () => {
  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            <AutoAwesomeIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            How Alexis AI Works
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Personalized iMessage suggestions that make texting easier
          </Typography>
        </Box>

        <Divider sx={{ mb: 4 }} />

        {/* Step 1: Connect Your iMessage */}
        <Box sx={{ mb: 5 }}>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <Box component="span" sx={{ 
              bgcolor: 'primary.main', 
              color: 'white', 
              borderRadius: '50%', 
              width: 30, 
              height: 30, 
              display: 'inline-flex', 
              justifyContent: 'center', 
              alignItems: 'center',
              mr: 2 
            }}>
              1
            </Box>
            Connect Your iMessage
          </Typography>
          
          <Grid container spacing={3} sx={{ mt: 2 }}>
            <Grid item xs={12} md={12}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ textAlign: 'center', mb: 2 }}>
                    <MessageIcon fontSize="large" color="primary" />
                  </Box>
                  <Typography variant="h6" gutterBottom>iMessage</Typography>
                  <Typography variant="body2">
                    Connect to your Mac Messages app so Alexis AI can learn your unique texting style. The app analyzes your conversation patterns, tone, and typical responses to create message suggestions that sound just like you wrote them.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          
          <Box sx={{ mt: 2, pl: 6 }}>
            <Typography variant="body2" color="text.secondary">
              Go to the <Button component={RouterLink} to="/training" size="small" color="primary">Training</Button> page to connect your iMessage account.
            </Typography>
          </Box>
        </Box>

        {/* Step 2: Train Your Alexis AI */}
        <Box sx={{ mb: 5 }}>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <Box component="span" sx={{ 
              bgcolor: 'primary.main', 
              color: 'white', 
              borderRadius: '50%', 
              width: 30, 
              height: 30, 
              display: 'inline-flex', 
              justifyContent: 'center', 
              alignItems: 'center',
              mr: 2 
            }}>
              2
            </Box>
            Train Your Alexis AI
          </Typography>
          
          <Box sx={{ pl: 6, mb: 3 }}>
            <Typography variant="body1" paragraph>
              After connecting your iMessage, click the "Train Alexis AI" button on the Training page. This process:
            </Typography>
            
            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid item xs={12} md={6}>
                <Card sx={{ height: '100%' }}>
                  <CardContent>
                    <Box sx={{ textAlign: 'center', mb: 2 }}>
                      <StyleIcon fontSize="large" color="primary" />
                    </Box>
                    <Typography variant="h6" gutterBottom>Learns Your Style</Typography>
                    <Typography variant="body2">
                      Analyzes your message history to understand your unique writing style, including your tone, vocabulary, and typical responses to different situations.
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card sx={{ height: '100%' }}>
                  <CardContent>
                    <Box sx={{ textAlign: 'center', mb: 2 }}>
                      <SpeedIcon fontSize="large" color="primary" />
                    </Box>
                    <Typography variant="h6" gutterBottom>Creates Your Personal AI</Typography>
                    <Typography variant="body2">
                      Builds a personalized AI model that understands your unique communication style and can generate message suggestions that sound just like you wrote them.
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
            
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Training typically takes 1-2 hours to complete. You'll receive a notification when it's done.
            </Typography>
          </Box>
        </Box>

        {/* Step 3: Get Message Suggestions */}
        <Box sx={{ mb: 5 }}>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <Box component="span" sx={{ 
              bgcolor: 'primary.main', 
              color: 'white', 
              borderRadius: '50%', 
              width: 30, 
              height: 30, 
              display: 'inline-flex', 
              justifyContent: 'center', 
              alignItems: 'center',
              mr: 2 
            }}>
              3
            </Box>
            Get Message Suggestions
          </Typography>
          
          <Box sx={{ pl: 6, mb: 3 }}>
            <Typography variant="body1" paragraph>
              Once training is complete, Alexis AI will automatically provide message suggestions when you're texting:
            </Typography>
            
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <ChatIcon fontSize="large" color="primary" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h6">Instant Message Suggestions</Typography>
                    <Typography variant="body2">
                      When you're in an iMessage conversation, Alexis AI will automatically suggest responses that match your style. Simply click a suggestion to send it - no more struggling with what to say.
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
            
            <Typography variant="body2" color="text.secondary">
              The more you use Alexis AI, the better it gets at matching your style. Suggestions appear within seconds and are ready to send without editing.
            </Typography>
          </Box>
        </Box>

        {/* Step 4: Configure Settings */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <Box component="span" sx={{ 
              bgcolor: 'primary.main', 
              color: 'white', 
              borderRadius: '50%', 
              width: 30, 
              height: 30, 
              display: 'inline-flex', 
              justifyContent: 'center', 
              alignItems: 'center',
              mr: 2 
            }}>
              4
            </Box>
            Customize Your Experience
          </Typography>
          
          <Box sx={{ pl: 6 }}>
            <Typography variant="body1" paragraph>
              Personalize how Alexis AI works for you:
            </Typography>
            
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <AutorenewIcon fontSize="large" color="primary" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h6">Configure Settings</Typography>
                    <Typography variant="body2">
                      Choose which conversations to get suggestions for, adjust the suggestion overlay position, and more.
                    </Typography>
                    <Button component={RouterLink} to="/auto-response" size="small" color="primary" sx={{ mt: 1 }}>
                      Go to Settings
                    </Button>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>
        </Box>
        
        {/* Privacy Information */}
        <Box sx={{ bgcolor: '#f5f5f5', p: 3, borderRadius: 2, mt: 4 }}>
          <Typography variant="h6" gutterBottom>
            Privacy & Data Security
          </Typography>
          <Typography variant="body2">
            Your data never leaves your computer during training. We use secure, encrypted connections and never store your raw message data on our servers.
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
};

export default HowItWorks;
