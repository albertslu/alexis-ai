// Preload script for Electron
const { ipcRenderer } = require('electron');

// Since contextIsolation is disabled, we can directly modify the window object
window.electron = {
  // API for message listener
  messageListener: {
    start: () => ipcRenderer.invoke('message-listener:start'),
    stop: () => ipcRenderer.invoke('message-listener:stop'),
    getStatus: () => ipcRenderer.invoke('message-listener:status'),
    updateConfig: (config) => ipcRenderer.invoke('message-listener:update-config', config)
  },
  // API for email listener
  emailListener: {
    start: () => ipcRenderer.invoke('email-listener:start'),
    stop: () => ipcRenderer.invoke('email-listener:stop'),
    getStatus: () => ipcRenderer.invoke('email-listener:status'),
    updateConfig: (config) => ipcRenderer.invoke('email-listener:update-config', config)
  },
  // API for Gmail OAuth
  startGmailOAuth: (userId) => ipcRenderer.invoke('start-gmail-oauth', userId),
  // API for permissions
  permissions: {
    check: (permission) => ipcRenderer.invoke('permissions:check', permission),
    request: (permission) => ipcRenderer.invoke('permissions:request', permission)
  },
  // API for logs
  logs: {
    get: () => ipcRenderer.invoke('logs:get')
  },
  // API for app info
  app: {
    getVersion: () => ipcRenderer.invoke('app:get-version'),
    getPath: (name) => ipcRenderer.invoke('app:get-path', name),
    quit: () => ipcRenderer.invoke('app:quit')
  },
  // API for settings
  settings: {
    get: (key) => ipcRenderer.invoke('settings:get', key),
    set: (key, value) => ipcRenderer.invoke('settings:set', key, value)
  },
  // API for response overlay
  overlay: {
    getSettings: () => ipcRenderer.invoke('get-overlay-settings'),
    updateSettings: (settings) => ipcRenderer.invoke('update-overlay-settings', settings),
    activate: () => ipcRenderer.invoke('activate-overlay'),
    deactivate: () => ipcRenderer.invoke('deactivate-overlay'),
    onDeactivated: (callback) => ipcRenderer.on('overlay-deactivated', () => callback()),
    getPort: () => ipcRenderer.invoke('get-overlay-port')
  },
  // API for auto-updates
  updates: {
    check: () => ipcRenderer.invoke('check-for-updates'),
    getStatus: () => ipcRenderer.invoke('get-update-status'),
    download: () => ipcRenderer.invoke('download-update'),
    install: () => ipcRenderer.invoke('install-update'),
    onAvailable: (callback) => ipcRenderer.on('update-available', (_, info) => callback(info)),
    onDownloaded: (callback) => ipcRenderer.on('update-downloaded', (_, info) => callback(info)),
    onProgress: (callback) => ipcRenderer.on('download-progress', (_, progress) => callback(progress)),
    onError: (callback) => ipcRenderer.on('update-error', (_, error) => callback(error))
  }
};

// Set essential global variables for React
window.isElectron = true;

// Hybrid approach: local backend for core features, EC2 for OAuth
window.API_BASE_URL = 'http://localhost:5002';  // Local Flask backend server
window.OAUTH_BASE_URL = 'http://localhost:5002';  // For OAuth and user authentication

// Log when preload is complete
console.log('Preload script executed successfully');
