const { ipcRenderer, contextBridge } = require('electron');
const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld(
  'api', {
    onUpdateSuggestions: (callback) => {
      ipcRenderer.on('update-suggestions', (event, data) => callback(data));
    },
    hideOverlay: () => {
      ipcRenderer.send('hide-overlay');
    },
    closeOverlay: () => {
      // Use invoke to ensure the main process receives the message
      // This creates a request-response pattern that's more reliable
      ipcRenderer.invoke('overlay-close-requested')
        .then(() => console.log('Close request acknowledged by main process'))
        .catch(err => console.error('Error closing overlay:', err));
      
      // Also send the regular message as a backup
      ipcRenderer.send('close-overlay');
    },
    insertResponse: (response) => {
      ipcRenderer.send('insert-response', response);
    },
    // Handle the setup for non-activating clicks
    onSetupNonActivatingClicks: (callback) => {
      ipcRenderer.on('setup-non-activating-clicks', () => callback());
    },
    // Start dragging the window (without activating it)
    // We're using native -webkit-app-region: drag for the header
    startDrag: () => {
      console.log('Using native window dragging');
    },
    
    // Temporarily disable click-through for interactive elements
    disableClickThrough: () => {
      console.log('Requesting to disable click-through');
      ipcRenderer.send('disable-click-through');
    },
    
    // Re-enable click-through
    enableClickThrough: () => {
      console.log('Requesting to re-enable click-through');
      ipcRenderer.send('enable-click-through');
    }
  }
);
