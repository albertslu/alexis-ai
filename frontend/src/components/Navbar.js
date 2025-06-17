import React, { useState, useEffect } from 'react';
import { AppBar, Toolbar, Typography, Button, Box, Tooltip, CircularProgress } from '@mui/material';
import { Link as RouterLink, useNavigate, useLocation } from 'react-router-dom';
import SystemUpdateIcon from '@mui/icons-material/SystemUpdate';
import { usePlatform } from '../contexts/PlatformContext';

const Navbar = ({ webOnly = false }) => {
  const { isElectron, isWeb } = usePlatform();
  const navigate = useNavigate();
  const location = useLocation();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userName, setUserName] = useState('');
  
  // Update state
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [updateDownloaded, setUpdateDownloaded] = useState(false);
  const [updateInfo, setUpdateInfo] = useState(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  
  useEffect(() => {
    // Check if user is logged in by looking for token in localStorage
    const token = localStorage.getItem('token');
    const userJson = localStorage.getItem('user');
    
    setIsLoggedIn(!!token);
    
    if (userJson) {
      try {
        const user = JSON.parse(userJson);
        setUserName(user.name || user.email);
      } catch (error) {
        console.error('Error parsing user data:', error);
      }
    }
    
    console.log('Auth state checked - Token exists:', !!token);
  }, [location.pathname]); // Re-check when route changes
  
  // Check for updates when component mounts
  useEffect(() => {
    // Only run in Electron environment
    if (window.electron) {
      // Check update status initially
      checkUpdateStatus();
      
      // Set up event listeners for update events
      window.electron.updates.onAvailable((info) => {
        console.log('Update available:', info);
        setUpdateAvailable(true);
        setUpdateInfo(info);
      });
      
      window.electron.updates.onDownloaded((info) => {
        console.log('Update downloaded:', info);
        setUpdateDownloaded(true);
        setUpdateInfo(info);
        setIsDownloading(false);
      });
      
      window.electron.updates.onProgress((progress) => {
        console.log('Download progress:', progress.percent);
        setDownloadProgress(progress.percent);
      });
      
      window.electron.updates.onError((error) => {
        console.error('Update error:', error);
        setIsDownloading(false);
      });
    }
  }, []);
  
  // Function to check current update status
  const checkUpdateStatus = async () => {
    if (window.electron) {
      try {
        const status = await window.electron.updates.getStatus();
        setUpdateAvailable(status.updateAvailable);
        setUpdateDownloaded(status.updateDownloaded);
        setUpdateInfo(status.updateInfo);
      } catch (error) {
        console.error('Error checking update status:', error);
      }
    }
  };

  const handleLogout = () => {
    // Clear authentication token and user info
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    console.log('User logged out');
    
    // Update state
    setIsLoggedIn(false);
    setUserName('');
    
    // Redirect to login page
    navigate('/login');
  };
  
  // Handle update button click
  const handleUpdateClick = async () => {
    if (window.electron) {
      if (updateDownloaded) {
        // Install the update
        console.log('Installing update...');
        await window.electron.updates.install();
      } else if (updateAvailable) {
        // Download the update
        console.log('Downloading update...');
        setIsDownloading(true);
        await window.electron.updates.download();
      } else {
        // Check for updates
        console.log('Checking for updates...');
        await window.electron.updates.check();
      }
    }
  };

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Alexis AI
        </Typography>
        <Box>
          <Button color="inherit" component={RouterLink} to="/dashboard">
            Dashboard
          </Button>
          
          {/* Show these buttons only in Electron or if not webOnly */}
          {(!webOnly && isWeb) || isElectron ? (
            <>
              <Button color="inherit" component={RouterLink} to="/how-it-works">
                How It Works
              </Button>
              <Button color="inherit" component={RouterLink} to="/training">
                Training
              </Button>
              <Button color="inherit" component={RouterLink} to="/imessage">
                iMessage
              </Button>
            </>
          ) : null}
          
          {/* Web-only buttons */}
          {webOnly && isWeb && (
            <>
              <Button color="inherit" component={RouterLink} to="/account">
                My Account
              </Button>
              <Button color="inherit" component={RouterLink} to="/download">
                Download App
              </Button>
            </>
          )}
          
          {/* Update button - only shown in Electron environment when updates are available */}
          {window.electron && (updateAvailable || updateDownloaded) && (
            <Tooltip title={updateDownloaded ? "Restart to install update" : "Download update"}>
              <Button 
                color="secondary" 
                variant="contained" 
                onClick={handleUpdateClick}
                sx={{ 
                  ml: 1, 
                  backgroundColor: updateDownloaded ? '#4caf50' : '#2196f3',
                  '&:hover': {
                    backgroundColor: updateDownloaded ? '#388e3c' : '#1976d2'
                  }
                }}
                startIcon={isDownloading ? <CircularProgress size={16} color="inherit" /> : <SystemUpdateIcon />}
              >
                {updateDownloaded ? 'Restart' : (isDownloading ? `${Math.round(downloadProgress)}%` : 'Update')}
              </Button>
            </Tooltip>
          )}

          {isLoggedIn && (
            <>
              <Button color="inherit" disabled>
                {userName || 'User'}
              </Button>
              <Button color="inherit" onClick={handleLogout}>
                Logout
              </Button>
            </>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
