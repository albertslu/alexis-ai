const { app } = require('electron');
const path = require('path');
const fs = require('fs');

// This script checks path resolution for the overlay agent
app.whenReady().then(() => {
  const appPath = app.getAppPath();
  const isAsar = appPath.includes('app.asar');
  
  console.log(`App path: ${appPath}`);
  console.log(`Is ASAR: ${isAsar}`);
  
  // Check development path
  const devPath = path.join(appPath, 'resources', 'overlay-agent.app', 'Contents', 'MacOS', 'overlay-agent');
  console.log(`Development path: ${devPath}`);
  console.log(`Development path exists: ${fs.existsSync(devPath)}`);
  
  // Check production path
  const prodPath = path.join(path.dirname(appPath), 'resources', 'overlay-agent.app', 'Contents', 'MacOS', 'overlay-agent');
  console.log(`Production path: ${prodPath}`);
  console.log(`Production path exists: ${fs.existsSync(prodPath)}`);
  
  // Check if the agent is executable
  try {
    fs.accessSync(prodPath, fs.constants.X_OK);
    console.log('Agent is executable');
  } catch (err) {
    console.log(`Agent is NOT executable: ${err.message}`);
  }
});
