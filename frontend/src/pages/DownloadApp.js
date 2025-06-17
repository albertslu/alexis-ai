import React from 'react';
import { Box, Typography, Button, Paper, Grid, List, ListItem, ListItemIcon, ListItemText, Divider, Container } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import AppleIcon from '@mui/icons-material/Apple';
import SecurityIcon from '@mui/icons-material/Security';
import MessageIcon from '@mui/icons-material/Message';
import EmailIcon from '@mui/icons-material/Email';
import MemoryIcon from '@mui/icons-material/Memory';

const DownloadApp = () => {
  // Updated with the new optimized DMG file
  const downloadUrl = "https://aiclone-downloads.s3.amazonaws.com/Alexis%20AI-1.0.0.dmg"; // Actual download URL
  
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
      <Paper elevation={3} sx={{ p: 4, borderRadius: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center" sx={{ mb: 4 }}>
          Download Alexis AI Desktop App
        </Typography>
        
        <Grid container spacing={4}>
          {/* Left column - Features */}
          <Grid item xs={12} md={7}>
            <Typography variant="h6" gutterBottom>
              Why Download the Desktop App?
            </Typography>
            
            <List>
              <ListItem>
                <ListItemIcon>
                  <MessageIcon color="primary" />
                </ListItemIcon>
                <ListItemText 
                  primary="Auto-respond to iMessages" 
                  secondary="Send responses from your personal Apple ID (only available in desktop app)"
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <EmailIcon color="primary" />
                </ListItemIcon>
                <ListItemText 
                  primary="Auto-respond to Emails" 
                  secondary="Connect your Gmail account for seamless email responses"
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <MemoryIcon color="primary" />
                </ListItemIcon>
                <ListItemText 
                  primary="Personalized Alexis AI" 
                  secondary="Your Alexis AI learns from your communication style and responds like you would"
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <SecurityIcon color="primary" />
                </ListItemIcon>
                <ListItemText 
                  primary="Privacy-Focused" 
                  secondary="Your messages stay on your device, only AI processing happens in the cloud"
                />
              </ListItem>
            </List>
            
            <Divider sx={{ my: 3 }} />
            
            <Typography variant="h6" gutterBottom>
              System Requirements
            </Typography>
            
            <List>
              <ListItem>
                <ListItemIcon>
                  <AppleIcon />
                </ListItemIcon>
                <ListItemText 
                  primary="macOS 10.15 (Catalina) or newer" 
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <CheckCircleIcon />
                </ListItemIcon>
                <ListItemText 
                  primary="Apple ID signed into Messages app" 
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <CheckCircleIcon />
                </ListItemIcon>
                <ListItemText 
                  primary="4GB RAM minimum (8GB recommended)" 
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <CheckCircleIcon />
                </ListItemIcon>
                <ListItemText 
                  primary="500MB free disk space" 
                />
              </ListItem>
            </List>
          </Grid>
          
          {/* Right column - Download */}
          <Grid item xs={12} md={5}>
            <Paper 
              elevation={2} 
              sx={{ 
                p: 4, 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center',
                backgroundColor: '#f8f9fa',
                borderRadius: 2
              }}
            >
              <Typography variant="h5" gutterBottom align="center">
                Download for macOS
              </Typography>
              
              <Box sx={{ my: 3, textAlign: 'center' }}>
                <AppleIcon sx={{ fontSize: 80, color: '#555' }} />
              </Box>
              
              <Button 
                variant="contained" 
                color="primary" 
                size="large" 
                startIcon={<DownloadIcon />}
                href={downloadUrl}
                sx={{ mb: 3, py: 1.5, px: 4, borderRadius: 2 }}
              >
                Download AI Clone
              </Button>
              
              <Typography variant="body2" color="textSecondary" align="center">
                Version 1.0.0 • Released June 2025
              </Typography>
              
              <Box sx={{ mt: 4, width: '100%' }}>
                <Typography variant="subtitle1" gutterBottom>
                  After downloading:
                </Typography>
                
                <List dense>
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon fontSize="small" color="success" />
                    </ListItemIcon>
                    <ListItemText primary="Open the .dmg file and drag to Applications" />
                  </ListItem>
                  
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon fontSize="small" color="success" />
                    </ListItemIcon>
                    <ListItemText primary="Launch AI Clone from Applications" />
                  </ListItem>
                  
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon fontSize="small" color="success" />
                    </ListItemIcon>
                    <ListItemText primary="Follow the setup wizard to configure" />
                  </ListItem>
                  
                  <ListItem>
                    <ListItemIcon>
                      <WarningIcon fontSize="small" color="warning" />
                    </ListItemIcon>
                    <ListItemText 
                      primary="Grant required permissions when prompted" 
                      secondary="Full Disk Access and Automation permissions are needed for iMessage integration"
                    />
                  </ListItem>
                </List>
              </Box>
            </Paper>
            
            <Box sx={{ mt: 3, p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
              <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                Web Demo Limitations
              </Typography>
              <Typography variant="body2" color="textSecondary">
                The web version of AI Clone can only auto-respond to emails, not iMessages. 
                For full functionality including iMessage auto-response, please download the desktop app.
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default DownloadApp;
// Force deployment Sat Jun 14 02:51:33 PDT 2025
