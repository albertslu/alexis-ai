const { app, BrowserWindow, ipcMain, dialog, shell, Menu, Tray } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const os = require('os');
const Store = require('electron-store');
const { autoUpdater } = require('electron-updater');
const log = require('electron-log');
const axios = require('axios');

// Configure logging for auto-updater
autoUpdater.logger = log;
autoUpdater.logger.transports.file.level = 'info';
log.info('App starting...');

// Set the update feed URL
autoUpdater.setFeedURL({
  provider: 'generic',
  url: 'https://aiclone-downloads.s3.amazonaws.com/'
});

// Initialize store for app settings
const store = new Store({
  name: 'ai-clone-settings',
  defaults: {
    autoRespondMessages: false,
    autoRespondEmails: false,
    messageCheckInterval: 5,
    emailCheckInterval: 60,
    allowedNumbers: [],
    firstRun: true,
    dependenciesInstalled: false,
    // Response overlay settings
    overlayEnabled: false,
    overlaySuggestionCount: 3,
    overlayCheckInterval: 5
  }
});

// Reset dependenciesInstalled flag to ensure dependencies are checked on next startup
// Only reset on app update, not on every startup
if (process.argv.includes('--updated')) {
  console.log('App was updated, resetting dependenciesInstalled flag');
  store.set('dependenciesInstalled', false);
}

// Import the OverlayAgentManager class
const OverlayAgentManager = require('./overlay-agent-manager');

// Keep references to prevent garbage collection
let mainWindow;
let tray;
let overlayAgentManager;
let backendProcess;
let messageListenerProcess;
let emailListenerProcess;
let responseOverlay;

// Update state
let updateAvailable = false;
let updateDownloaded = false;
let updateInfo = null;

// Path to project root and Python executable
const PROJECT_ROOT = path.join(__dirname, '..');

// Find the Python executable dynamically
function findPythonPath() {
  // Check for environment variable first
  if (process.env.PYTHON_PATH) {
    return process.env.PYTHON_PATH;
  }
  
  // In development, try to find Python in the virtual environment
  const venvPythonPath = path.join(PROJECT_ROOT, 'venv', 'bin', 'python');
  if (fs.existsSync(venvPythonPath)) {
    return venvPythonPath;
  }
  
  // Fall back to system Python
  return 'python3';
}

const PYTHON_PATH = findPythonPath();

// Get the correct path for resources based on whether we're in development or production
const getAppPath = () => {
  if (process.env.NODE_ENV === 'development') {
    return PROJECT_ROOT;
  } else {
    // In production, use the app.getAppPath() to get the path to the app.asar file
    return app.isPackaged 
      ? path.dirname(app.getAppPath()) 
      : PROJECT_ROOT;
  }
};

// Get resource path based on whether we're in development or production
const getResourcePath = (resourcePath = '') => {
  if (app.isPackaged) {
    // In production, resources are in extraResources (Resources directory)
    return path.join(app.getAppPath(), '..', '..', 'Resources', resourcePath);
  } else {
    // In development, resources are in the project root
    return path.join(PROJECT_ROOT, resourcePath);
  }
};

// Backend API URL
const API_URL = 'http://localhost:5002';

// Create the main application window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: false, // Change to false to allow direct access to Node APIs
      nodeIntegration: true,   // Enable Node integration for React to work properly
      webSecurity: false,      // Disable web security to allow loading local resources
      allowRunningInsecureContent: true,
      javascript: true,
      webviewTag: true,
      devTools: true,
      nodeIntegrationInWorker: false,
      sandbox: false
    },
    title: 'Alexis AI',
    backgroundColor: '#ffffff',
    icon: path.join(getAppPath(), 'assets/icon.icns'),
    show: false,
    paintWhenInitiallyHidden: true
  });
  
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
  
  // Set Content Security Policy to allow script execution and Google Fonts
  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self'; " +
          "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.google.com https://*.googleapis.com https://*.gstatic.com; " +
          "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://*.google.com https://*.googleapis.com https://*.gstatic.com; " +
          "font-src 'self' https://fonts.gstatic.com; " +
          "img-src 'self' data: https://*.google.com https://*.googleapis.com https://*.gstatic.com https://lh3.googleusercontent.com; " +
          "connect-src 'self' http://localhost:5002 https://api.aiclone.space https://api.openai.com https://*.google.com https://*.googleapis.com"
        ]
      }
    });
  });
  
  // Allow navigation to Google domains for OAuth
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    // Allow opening Google OAuth URLs in the default browser
    if (url.startsWith('https://accounts.google.com/') || 
        url.startsWith('https://www.google.com/') ||
        url.startsWith('http://localhost:5002/')) {
      return { action: 'allow' };
    }
    
    // Handle custom protocol URLs
    if (url.startsWith('ai-clone://')) {
      console.log(`Intercepted custom protocol URL in window.open: ${url}`);
      handleDeepLink(url);
      // Return deny to prevent opening a new window, as we're handling it ourselves
      return { action: 'deny' };
    }
    
    return { action: 'deny' };
  });
  
  // Load the React app
  // In production, this will load from a built version
  // In development, this will connect to the React dev server
  if (process.env.NODE_ENV === 'development') {
    // Try to load from React dev server first
    console.log('Development mode: Attempting to load from React dev server');
    
    // Try to connect to React dev server
    fetch('http://localhost:3000')
      .then(() => {
        console.log('React dev server running, loading from dev server');
        mainWindow.loadURL('http://localhost:3000');
      })
      .catch(err => {
        console.log(`React dev server not running, falling back to local build: ${err.message}`);
        loadLocalBuild();
      });
  } else {
    // In production, load from the built version
    loadLocalBuild();
  }

  // Handle window close (minimize to tray instead of quitting)
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      return false;
    }
  });

  // Emitted when the window is closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
  
  // Initialize the overlay agent manager
  overlayAgentManager = new OverlayAgentManager();
  
  // Check if Messages permissions are granted
  checkMessagesPermissions();
  
  // Don't activate overlay automatically on startup
  // The overlay will only be activated when explicitly toggled on by the user
}

// Function to load from local build
const loadLocalBuild = () => {
  let frontendPath;
  
  // Determine the correct path based on whether we're in development or production
  if (app.isPackaged) {
    frontendPath = getResourcePath('frontend/build');
  } else {
    frontendPath = path.join(PROJECT_ROOT, 'frontend', 'build');
  }
  
  console.log(`Loading frontend from: ${frontendPath}`);
  
  if (fs.existsSync(frontendPath)) {
    // Create a local HTTP server to serve the React app
    const http = require('http');
    const serveStatic = require('serve-static');
    const finalhandler = require('finalhandler');
    
    // Configure the main window for better debugging
    mainWindow.webContents.openDevTools();
    
    // Create a static file server for the build directory
    const serve = serveStatic(frontendPath);
    
    // Create the server
    const server = http.createServer((req, res) => {
      // Log incoming requests to help debug
      console.log(`Request: ${req.method} ${req.url}`);
      
      // Add CORS headers
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, PATCH, DELETE');
      res.setHeader('Access-Control-Allow-Headers', 'X-Requested-With,content-type');
      
      // Set CSP headers directly in the response
      res.setHeader('Content-Security-Policy', 
        "default-src 'self'; " +
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.google.com https://*.googleapis.com https://*.gstatic.com; " +
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://*.google.com https://*.googleapis.com https://*.gstatic.com; " +
        "font-src 'self' https://fonts.gstatic.com; " +
        "img-src 'self' data: https://*.google.com https://*.googleapis.com https://*.gstatic.com https://lh3.googleusercontent.com; " +
        "connect-src 'self' http://localhost:5002 https://api.aiclone.space https://api.openai.com https://*.google.com https://*.googleapis.com"
      );
      
      serve(req, res, finalhandler(req, res));
    });
    
    // Find an available port
    const getPort = () => {
      return new Promise((resolve, reject) => {
        const server = http.createServer();
        server.listen(0, () => {
          const port = server.address().port;
          server.close(() => {
            resolve(port);
          });
        });
      });
    };
    
    // Start the server and load the app
    getPort().then(port => {
      server.listen(port, '127.0.0.1', () => {
        const url = `http://localhost:${port}/`;
        console.log(`Local server running at ${url}`);
        
        // Set up event listeners before loading the URL
        mainWindow.webContents.on('did-start-loading', () => {
          console.log('Started loading page');
        });
        
        mainWindow.webContents.on('did-finish-load', () => {
          console.log('React app loaded successfully');
        });
        
        mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
          console.error(`Failed to load: ${errorDescription} (${errorCode})`);
        });
        
        // Load the root URL - HashRouter will handle the routing
        mainWindow.loadURL(`http://localhost:${port}/#/login`);
      });
    }).catch(err => {
      console.error('Failed to start local server:', err);
      // Fallback to direct file loading
      mainWindow.loadFile(path.join(frontendPath, 'index.html'));
    });
  } else {
    console.error(`Frontend build not found at: ${frontendPath}`);
    dialog.showErrorBox(
      'Frontend Not Found',
      `Could not find the frontend build at ${frontendPath}. Please run 'npm run build' in the frontend directory.`
    );
  }
};

// Create the system tray icon and menu
function createTray() {
  try {
    // Use the tray icon we created
    const trayIconPath = path.join(getAppPath(), 'assets/tray-icon.png');
    
    // Check if the icon exists
    if (fs.existsSync(trayIconPath)) {
      console.log(`Using tray icon: ${trayIconPath}`);
      tray = new Tray(trayIconPath);
    } else {
      console.log(`Tray icon not found at: ${trayIconPath}`);
      // Use a default icon as fallback
      tray = new Tray(nativeImage.createEmpty());
    }
    
    // Configure the tray
    tray.setToolTip('Alexis AI');
    
    // Create the tray menu
    const contextMenu = Menu.buildFromTemplate([
      { 
        label: 'Open Alexis AI', 
        click: () => {
          mainWindow.show();
        }
      },
      { type: 'separator' },
      { 
        label: 'Auto-Respond to Messages', 
        type: 'checkbox', 
        checked: store.get('autoRespondMessages'),
        click: (menuItem) => {
          store.set('autoRespondMessages', menuItem.checked);
          toggleMessageListener(menuItem.checked);
          if (mainWindow) {
            mainWindow.webContents.send('message-listener-status-changed', menuItem.checked);
          }
        }
      },
      { 
        label: 'Auto-Respond to Emails', 
        type: 'checkbox', 
        checked: store.get('autoRespondEmails'),
        click: (menuItem) => {
          store.set('autoRespondEmails', menuItem.checked);
          toggleEmailListener(menuItem.checked);
          if (mainWindow) {
            mainWindow.webContents.send('email-listener-status-changed', menuItem.checked);
          }
        }
      },
      { type: 'separator' },
      { label: 'Settings', click: () => {
        mainWindow.show();
        if (mainWindow) {
          mainWindow.webContents.send('navigate-to-settings');
        }
      }},
      { type: 'separator' },
      { 
        label: 'Check for Updates', 
        click: () => {
          log.info('Manual update check from tray');
          autoUpdater.checkForUpdates();
        }
      },
      { label: 'Quit', click: () => {
        app.isQuitting = true;
        app.quit();
      }}
    ]);
    
    tray.setContextMenu(contextMenu);
    
    // Show window on click (macOS behavior)
    tray.on('click', () => {
      if (mainWindow) {
        mainWindow.show();
      }
    });
  } catch (error) {
    console.error('Error creating tray:', error);
    // If we can't create a tray, we'll just continue without it
  }
}

// Start the backend Flask server
function startBackend() {
  console.log('Starting backend server...');
  
  // Get paths based on whether we're in development or production
  let backendPath;
  let resourcesPath;
  
  if (app.isPackaged) {
    // In production, use the resource paths
    resourcesPath = getResourcePath('');
    backendPath = getResourcePath('backend/app.py');
  } else {
    // In development, use the project root
    resourcesPath = PROJECT_ROOT;
    backendPath = path.join(resourcesPath, 'backend', 'app.py');
  }
  
  console.log(`Backend path: ${backendPath}`);
  console.log(`Resources path: ${resourcesPath}`);
  
  // Check if the backend file exists
  if (!fs.existsSync(backendPath)) {
    console.error(`Backend file not found at: ${backendPath}`);
    dialog.showErrorBox(
      'Backend Not Found', 
      `Could not find backend at ${backendPath}. Please make sure the application is installed correctly.`
    );
    app.quit();
    return;
  } else {
    console.log(`Backend file exists at: ${backendPath}`);
  }
  
  // Load environment variables from .env file
  let envPath;
  if (app.isPackaged) {
    // In production, try to find .env file in app directory
    envPath = getResourcePath('.env.production');
    if (!fs.existsSync(envPath)) {
      envPath = getResourcePath('.env');
    }
  } else {
    // In development, use .env file in project root
    envPath = path.join(PROJECT_ROOT, '.env');
  }
  
  // Check if the env file exists
  if (!fs.existsSync(envPath)) {
    console.error(`Env file not found at: ${envPath}`);
  } else {
    console.log(`Env file exists at: ${envPath}`);
  }
  
  // Load environment variables
  let envVars = {};
  if (fs.existsSync(envPath)) {
    console.log(`Loading environment variables from: ${envPath}`);
    const envContent = fs.readFileSync(envPath, 'utf8');
    envContent.split('\n').forEach(line => {
      const match = line.match(/^([^=]+)=(.*)$/);
      if (match) {
        const key = match[1].trim();
        const value = match[2].trim().replace(/^['"]|['"]$/g, ''); // Remove quotes
        envVars[key] = value;
      }
    });
    console.log('Environment variables loaded successfully');
  } else {
    console.log(`No .env file found at: ${envPath}`);
  }
  
  // Set up environment variables for the backend process
  const env = { 
    ...process.env, 
    ...envVars,
    FLASK_APP: backendPath,
    FLASK_ENV: app.isPackaged ? 'production' : 'development',
    PYTHONUNBUFFERED: '1',   // Ensure Python output is not buffered
    PYTHONIOENCODING: 'utf-8'
  };
  
  // Create logs directory if it doesn't exist
  const logsDir = path.join(app.getPath('userData'), 'logs');
  if (!fs.existsSync(logsDir)) {
    try {
      fs.mkdirSync(logsDir, { recursive: true });
      console.log(`Created logs directory at ${logsDir}`);
    } catch (error) {
      console.error(`Failed to create logs directory: ${error.message}`);
    }
  }
  
  // Create a log file for the backend
  const logFilePath = path.join(logsDir, 'backend.log');
  const logStream = fs.createWriteStream(logFilePath, { flags: 'a' });
  
  // Log startup information
  const startupLog = `\n\n--- Backend started at ${new Date().toISOString()} ---\n\n`;
  logStream.write(startupLog);
  console.log(`Backend logs will be saved to ${logFilePath}`);
  
  // Copy credentials.json to the working directory if it exists in resources
  const credentialsSourcePath = getResourcePath('credentials.json');
  const credentialsTargetPath = path.join(process.cwd(), 'credentials.json');
  
  // Ensure data directory exists and has proper permissions
  const dataDir = path.join(process.cwd(), 'data');
  if (!fs.existsSync(dataDir)) {
    try {
      fs.mkdirSync(dataDir, { recursive: true });
      console.log(`Created data directory at ${dataDir}`);
    } catch (error) {
      console.error(`Failed to create data directory: ${error.message}`);
    }
  }

  // Create subdirectories for data
  const dataDirs = [
    path.join(dataDir, 'chat_histories'),
    path.join(dataDir, 'user_configs'),
    path.join(dataDir, 'memory'),
    path.join(dataDir, 'unified_repository')
  ];

  dataDirs.forEach(dir => {
    if (!fs.existsSync(dir)) {
      try {
        fs.mkdirSync(dir, { recursive: true });
        console.log(`Created directory: ${dir}`);
      } catch (error) {
        console.error(`Failed to create directory ${dir}: ${error.message}`);
      }
    }
  });
  
  if (fs.existsSync(credentialsSourcePath)) {
    try {
      fs.copyFileSync(credentialsSourcePath, credentialsTargetPath);
      console.log(`Copied credentials.json from ${credentialsSourcePath} to ${credentialsTargetPath}`);
      
      // Add more detailed logging to verify the contents of credentials.json
      try {
        const credentialsContent = fs.readFileSync(credentialsTargetPath, 'utf8');
        const credentialsJson = JSON.parse(credentialsContent);
        console.log('credentials.json loaded successfully');
        console.log(`OAuth client ID: ${credentialsJson.web?.client_id || credentialsJson.installed?.client_id || 'Not found'}`);
        console.log(`OAuth redirect URIs: ${JSON.stringify(credentialsJson.web?.redirect_uris || credentialsJson.installed?.redirect_uris || [])}`);
      } catch (readError) {
        console.error(`Failed to read or parse credentials.json: ${readError.message}`);
      }
    } catch (error) {
      console.error(`Failed to copy credentials.json: ${error.message}`);
    }
  } else {
    console.warn(`credentials.json not found at ${credentialsSourcePath}`);
    // Try to find credentials.json in other locations
    const possiblePaths = [
      path.join(process.cwd(), 'credentials.json'),
      path.join(PROJECT_ROOT, 'credentials.json'),
      path.join(app.getPath('userData'), 'credentials.json')
    ];
    
    for (const possiblePath of possiblePaths) {
      if (fs.existsSync(possiblePath)) {
        console.log(`Found credentials.json at alternative location: ${possiblePath}`);
        try {
          fs.copyFileSync(possiblePath, credentialsTargetPath);
          console.log(`Copied credentials.json from ${possiblePath} to ${credentialsTargetPath}`);
          break;
        } catch (copyError) {
          console.error(`Failed to copy from alternative location: ${copyError.message}`);
        }
      }
    }
  }
  
  // Ensure MongoDB URI is set correctly for production
  if (app.isPackaged) {
    // In production, always use the production MongoDB URI
    const productionMongoURI = envVars.MONGODB_URI_PRODUCTION || process.env.MONGODB_URI_PRODUCTION;
    if (productionMongoURI) {
      env.MONGODB_URI = productionMongoURI;
      console.log('Using production MongoDB URI for packaged app');
    } else {
      console.warn('No production MongoDB URI found in environment variables');
      // Try to load from .env.production if it exists
      try {
        const envPath = getResourcePath('.env.production');
        if (fs.existsSync(envPath)) {
          const envContent = fs.readFileSync(envPath, 'utf8');
          // Simple parsing without using dotenv
          const productionMongoURI = envContent.split('\n')
            .find(line => line.startsWith('MONGODB_URI='))
            ?.split('=')[1]
            ?.trim()
            ?.replace(/^['"]|['"]$/g, ''); // Remove quotes
            
          if (productionMongoURI) {
            env.MONGODB_URI = productionMongoURI;
            console.log('Loaded production MongoDB URI from .env.production file');
          }
        }
      } catch (err) {
        console.error('Error loading production MongoDB URI:', err);
      }
    }
  }
  
  // Set the PYTHONPATH to include the project root directory for utils module
  if (app.isPackaged) {
    // In production, set PYTHONPATH to include all necessary directories
    // Make sure the project root is in the path so Python can find utils, routes, etc.
    env.PYTHONPATH = `${getResourcePath()}:${getResourcePath('backend')}:${getResourcePath('rag')}:${env.PYTHONPATH || ''}`;
    console.log(`PYTHONPATH in production: ${env.PYTHONPATH}`);
  } else {
    // In development, set PYTHONPATH to include the project root
    env.PYTHONPATH = `${PROJECT_ROOT}:${env.PYTHONPATH || ''}`;
    console.log(`PYTHONPATH in development: ${env.PYTHONPATH}`);
  }
  
  // Set the working directory for the backend process
  const cwd = app.isPackaged ? getResourcePath('') : PROJECT_ROOT;
  console.log(`Working directory: ${cwd}`);
  
  // Find Python executable
  let pythonPath = PYTHON_PATH;
  
  if (app.isPackaged) {
    // In production, try to find Python in common locations
    const possiblePythonPaths = [
      '/usr/bin/python3',
      '/usr/local/bin/python3',
      '/opt/homebrew/bin/python3',
      '/usr/bin/python',
      process.env.PYTHON_PATH
    ].filter(Boolean); // Remove undefined entries
    
    for (const path of possiblePythonPaths) {
      try {
        if (fs.existsSync(path)) {
          pythonPath = path;
          console.log(`Found Python at: ${pythonPath}`);
          break;
        }
      } catch (error) {
        console.log(`Error checking Python path ${path}: ${error.message}`);
      }
    }
  }
  
  console.log(`Using Python path: ${pythonPath}`);
  
  // Check if Python has the required dependencies
  const checkDependencies = () => {
    // Check if we've already installed dependencies
    if (app.isPackaged && store.get('dependenciesInstalled')) {
      console.log('Dependencies were previously installed, skipping check');
      return Promise.resolve([]);
    }
    
    return new Promise((resolve, reject) => {
      const requiredPackages = [
        'flask',
        'flask-cors',
        'openai',
        'pymongo',
        'scikit-learn',
        'numpy',
        'pandas',
        'PyJWT',
        'websocket-client'
      ];
      
      console.log('Checking Python dependencies...');
      
      const checkProcess = spawn(pythonPath, [
        '-c', 
        `import importlib.util; missing = [pkg for pkg in ${JSON.stringify(requiredPackages)} if importlib.util.find_spec(pkg.replace('-', '_')) is None]; print(','.join(missing))`
      ]);
      
      let output = '';
      
      checkProcess.stdout.on('data', (data) => {
        output += data.toString();
      });
      
      checkProcess.on('close', (code) => {
        if (code !== 0) {
          console.error(`Failed to check dependencies, exit code: ${code}`);
          resolve([]); // Continue anyway
        } else {
          const missingPackages = output.trim().split(',').filter(Boolean);
          console.log(`Missing packages: ${missingPackages.length ? missingPackages.join(', ') : 'None'}`);
          resolve(missingPackages);
        }
      });
      
      checkProcess.on('error', (error) => {
        console.error(`Error checking dependencies: ${error.message}`);
        resolve([]); // Continue anyway
      });
    });
  };
  
  // Install missing dependencies if needed
  const installDependencies = (packages) => {
    if (!packages.length) {
      // Mark dependencies as installed even if none were missing
      if (app.isPackaged) {
        store.set('dependenciesInstalled', true);
      }
      return Promise.resolve();
    }
    
    return new Promise((resolve, reject) => {
      // Create a detailed log file for debugging
      const debugLogPath = path.join(app.getPath('userData'), 'dependency-debug.log');
      
      // Function to write to the debug log
      const writeDebugLog = (message) => {
        try {
          fs.appendFileSync(debugLogPath, `[${new Date().toISOString()}] ${message}\n`);
          console.log(message); // Also log to console
        } catch (error) {
          console.error(`Failed to write to debug log: ${error.message}`);
        }
      };
      
      writeDebugLog('Starting dependency installation...');
      writeDebugLog(`Packages to install: ${packages.join(', ')}`);
      
      console.log(`Installing missing packages: ${packages.join(', ')}`);
      
      // Show a dialog to inform the user
      dialog.showMessageBox({
        type: 'info',
        title: 'Installing Dependencies',
        message: 'Installing required Python packages',
        detail: 'This may take a few minutes. The app will start automatically when finished.',
        buttons: ['OK']
      });
      
      const reqPath = app.isPackaged 
        ? getResourcePath('requirements.txt')
        : path.join(PROJECT_ROOT, 'requirements.txt');
      
      writeDebugLog(`Requirements path: ${reqPath}`);
      writeDebugLog(`Python path: ${pythonPath}`);
      
      // Install all dependencies from requirements.txt
      writeDebugLog('Installing dependencies...');
      const installProcess = spawn(pythonPath, [
        '-m', 'pip', 'install', '-r', reqPath
      ]);
      
      installProcess.stdout.on('data', (data) => {
        writeDebugLog(`Pip install output: ${data.toString().trim()}`);
      });
      
      installProcess.stderr.on('data', (data) => {
        writeDebugLog(`Pip install error: ${data.toString().trim()}`);
      });
      
      installProcess.on('close', (code) => {
        if (code !== 0) {
          console.error(`Failed to install dependencies, exit code: ${code}`);
          dialog.showErrorBox(
            'Dependency Installation Failed',
            `Failed to install required Python packages. The app may not work correctly.`
          );
        } else {
          console.log('Dependencies installed successfully');
          // Mark dependencies as installed
          if (app.isPackaged) {
            store.set('dependenciesInstalled', true);
          }
        }
        resolve();
      });
      
      installProcess.on('error', (error) => {
        console.error(`Error installing dependencies: ${error.message}`);
        dialog.showErrorBox(
          'Dependency Installation Error',
          `Error starting installation process: ${error.message}`
        );
        resolve();
      });
    });
  };
  
  // Start the backend after checking and installing dependencies
  const startBackendProcess = () => {
    // Start the backend process
    console.log(`Starting backend process with Python: ${pythonPath}`);
    console.log(`Command: ${pythonPath} ${backendPath}`);
    
    try {
      backendProcess = spawn(pythonPath, [backendPath], {
        cwd,
        env,
        stdio: 'pipe'
      });
      
      console.log(`Backend process started with PID: ${backendProcess.pid}`);
      
      // Handle backend process output
      backendProcess.stdout.on('data', (data) => {
        const output = data.toString().trim();
        console.log(`Backend stdout: ${output}`);
        logStream.write(`[STDOUT ${new Date().toISOString()}] ${output}\n`);
      });
      
      backendProcess.stderr.on('data', (data) => {
        const output = data.toString().trim();
        console.error(`Backend stderr: ${output}`);
        logStream.write(`[STDERR ${new Date().toISOString()}] ${output}\n`);
      });
      
      // Handle backend process exit
      backendProcess.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
        logStream.write(`[EXIT ${new Date().toISOString()}] Backend process exited with code ${code}\n`);
        
        if (code !== 0 && code !== null) {
          dialog.showErrorBox(
            'Backend Error', 
            `The backend server has stopped unexpectedly (exit code: ${code}).`
          );
        }
        
        backendProcess = null;
      });
      
      // Wait for the backend to start
      setTimeout(() => {
        // Check if the backend is running
        fetch(API_URL)
          .then(response => {
            console.log(`Backend is running at ${API_URL}`);
          })
          .catch(error => {
            console.error(`Failed to connect to backend: ${error.message}`);
          });
      }, 2000);
    } catch (error) {
      console.error(`Failed to start backend process: ${error.message}`);
      
      dialog.showErrorBox(
        'Backend Error',
        `Failed to start backend server: ${error.message}. Please restart the application.`
      );
    }
  };
  
  // Check dependencies and start backend
  if (app.isPackaged) {
    checkDependencies()
      .then(missingPackages => installDependencies(missingPackages))
      .then(() => startBackendProcess())
      .catch(error => {
        console.error(`Error in dependency management: ${error.message}`);
        startBackendProcess(); // Try to start anyway
      });
  } else {
    // In development, just start the backend
    startBackendProcess();
  }
}

// Start/stop the iMessage listener
function toggleMessageListener(enabled) {
  if (enabled) {
    const messageListenerPath = getResourcePath('scripts/mac_message_listener.py');
    
    // Check if the script exists
    if (!fs.existsSync(messageListenerPath)) {
      dialog.showErrorBox(
        'Message Listener Not Found', 
        `Could not find message listener at ${messageListenerPath}.`
      );
      return;
    }
    
    // Build command arguments
    const args = [
      messageListenerPath,
      '--interval', store.get('messageCheckInterval', 5).toString()
    ];
    
    if (store.get('allowedNumbers', []).length > 0) {
      args.push('--allowed-numbers', ...store.get('allowedNumbers'));
    }
    
    // Start the message listener process
    messageListenerProcess = spawn(PYTHON_PATH, args, {
      cwd: PROJECT_ROOT
    });
    
    // Log message listener output
    messageListenerProcess.stdout.on('data', (data) => {
      console.log(`Message listener: ${data}`);
      if (mainWindow) {
        mainWindow.webContents.send('message-listener-log', data.toString());
      }
    });
    
    messageListenerProcess.stderr.on('data', (data) => {
      console.error(`Message listener error: ${data}`);
      if (mainWindow) {
        mainWindow.webContents.send('message-listener-error', data.toString());
      }
    });
    
    messageListenerProcess.on('close', (code) => {
      console.log(`Message listener process exited with code ${code}`);
      if (code !== 0 && store.get('autoRespondMessages') && !app.isQuitting) {
        dialog.showErrorBox(
          'Message Listener Error', 
          `The message listener stopped unexpectedly (code ${code}).`
        );
        store.set('autoRespondMessages', false);
        updateTrayMenu();
      }
    });
    
    console.log('Message listener started');
  } else if (messageListenerProcess) {
    // Stop the message listener
    messageListenerProcess.kill();
    messageListenerProcess = null;
    console.log('Message listener stopped');
  }
}

// Start/stop the email listener
function toggleEmailListener(enabled) {
  if (enabled) {
    const emailListenerPath = getResourcePath('scripts/email_auto_response.py');
    
    // Check if the script exists
    if (!fs.existsSync(emailListenerPath)) {
      dialog.showErrorBox(
        'Email Listener Not Found', 
        `Could not find email listener at ${emailListenerPath}.`
      );
      return;
    }
    
    // Build command arguments
    const args = [
      emailListenerPath,
      '--mode=monitor',
      '--interval', store.get('emailCheckInterval', 60).toString(),
      '--max_emails', '10'
    ];
    
    if (store.get('autoRespondEmails', false)) {
      args.push('--auto_respond');
    }
    
    // Start the email listener process
    emailListenerProcess = spawn(PYTHON_PATH, args, {
      cwd: PROJECT_ROOT
    });
    
    // Log email listener output
    emailListenerProcess.stdout.on('data', (data) => {
      console.log(`Email listener: ${data}`);
      if (mainWindow) {
        mainWindow.webContents.send('email-listener-log', data.toString());
      }
    });
    
    emailListenerProcess.stderr.on('data', (data) => {
      console.error(`Email listener error: ${data}`);
      if (mainWindow) {
        mainWindow.webContents.send('email-listener-error', data.toString());
      }
    });
    
    emailListenerProcess.on('close', (code) => {
      console.log(`Email listener process exited with code ${code}`);
      if (code !== 0 && store.get('autoRespondEmails') && !app.isQuitting) {
        dialog.showErrorBox(
          'Email Listener Error', 
          `The email listener stopped unexpectedly (code ${code}).`
        );
        store.set('autoRespondEmails', false);
        updateTrayMenu();
      }
    });
    
    console.log('Email listener started');
  } else if (emailListenerProcess) {
    // Stop the email listener
    emailListenerProcess.kill();
    emailListenerProcess = null;
    console.log('Email listener stopped');
  }
}

// Update the tray menu to reflect current settings
function updateTrayMenu() {
  if (!tray) return;
  
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Open Alexis AI', click: () => mainWindow.show() },
    { type: 'separator' },
    { 
      label: 'Auto-Respond to Messages', 
      type: 'checkbox', 
      checked: store.get('autoRespondMessages', false),
      click: (menuItem) => {
        store.set('autoRespondMessages', menuItem.checked);
        toggleMessageListener(menuItem.checked);
        updateTrayMenu();
      }
    },
    { 
      label: 'Auto-Respond to Emails', 
      type: 'checkbox', 
      checked: store.get('autoRespondEmails', false),
      click: (menuItem) => {
        store.set('autoRespondEmails', menuItem.checked);
        toggleEmailListener(menuItem.checked);
        updateTrayMenu();
      }
    },
    { type: 'separator' },
    { label: 'Settings', click: () => {
      mainWindow.show();
      if (mainWindow) {
        mainWindow.webContents.send('navigate-to-settings');
      }
    }},
    { type: 'separator' },
    { label: 'Quit', click: () => {
      app.isQuitting = true;
      app.quit();
    }}
  ]);
  
  tray.setContextMenu(contextMenu);
}



// Check if Messages permissions are granted and prompt if needed
function checkMessagesPermissions() {
  log.info('Checking Messages permissions');
  
  // Use AppleScript to check if we can access Messages
  const script = `
    tell application "System Events"
      try
        tell application "Messages"
          get name of first chat
          return "true"
        end tell
      on error
        return "false"
      end try
    end tell
  `;
  
  exec(`osascript -e '${script}'`, (error, stdout) => {
    const hasPermission = stdout.trim() === 'true';
    log.info(`Messages permission check result: ${hasPermission}`);
    
    if (!hasPermission) {
      // Show dialog prompting user to grant permissions
      dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'Messages Permission Required',
        message: 'Alexis AI needs permission to access Messages',
        detail: 'To provide response suggestions in Messages, Alexis AI needs permission to access your Messages app. You will be prompted by macOS to grant this permission.',
        buttons: ['Grant Permission', 'Later'],
        defaultId: 0
      }).then(({ response }) => {
        if (response === 0) {
          // Try to trigger the permission dialog by accessing Messages
          exec(`osascript -e 'tell application "Messages" to get name of first chat'`, (err) => {
            if (err) {
              log.error('Error triggering Messages permission dialog', err);
            }
          });
        }
      });
    }
  });
}

// Check system permissions required for the app
async function checkPermissions() {
  // Check Full Disk Access (needed for Messages database)
  const hasFullDiskAccess = await new Promise((resolve) => {
    exec('ls ~/Library/Messages/chat.db', (error) => {
      resolve(!error);
    });
  });
  
  // Check Automation permission (needed for AppleScript)
  const hasAutomationPermission = await new Promise((resolve) => {
    exec('osascript -e "tell application \\"Messages\\" to get name"', (error) => {
      resolve(!error);
    });
  });
  
  return {
    fullDiskAccess: hasFullDiskAccess,
    automationPermission: hasAutomationPermission
  };
}

// Show permission instructions
function showPermissionInstructions(permission) {
  const permissionTexts = {
    fullDiskAccess: {
      title: 'Full Disk Access Required',
      message: 'Alexis AI needs Full Disk Access to read your Messages database. Please follow these steps:\n\n1. Open System Preferences\n2. Go to Security & Privacy > Privacy\n3. Select "Full Disk Access" from the left sidebar\n4. Click the lock icon to make changes\n5. Add Alexis AI to the list of allowed apps\n\nWould you like to open System Preferences now?'
    },
    automationPermission: {
      title: 'Automation Permission Required',
      message: 'Alexis AI needs permission to control the Messages app. Please follow these steps:\n\n1. Open System Preferences\n2. Go to Security & Privacy > Privacy\n3. Select "Automation" from the left sidebar\n4. Click the lock icon to make changes\n5. Enable Alexis AI to control "Messages"\n\nWould you like to open System Preferences now?'
    }
  };
  
  const { title, message } = permissionTexts[permission];
  
  const response = dialog.showMessageBoxSync(mainWindow, {
    type: 'info',
    title: title,
    message: title,
    detail: message,
    buttons: ['Open System Preferences', 'Later'],
    defaultId: 0
  });
  
  if (response === 0) {
    if (permission === 'fullDiskAccess') {
      shell.openExternal('x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles');
    } else if (permission === 'automationPermission') {
      shell.openExternal('x-apple.systempreferences:com.apple.preference.security?Privacy_Automation');
    }
  }
}

// Show first run dialog
function showFirstRunDialog() {
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Welcome to Alexis AI',
    message: 'Welcome to Alexis AI',
    detail: 'This app helps you draft iMessage responses in your personal style. To get started, you\'ll need to grant some permissions and connect your iMessage account.\n\nWould you like to set up Alexis AI now?',
    buttons: ['Set Up Now', 'Later'],
    defaultId: 0
  }).then(({ response }) => {
    if (response === 0) {
      // Navigate to setup page
      if (mainWindow) {
        mainWindow.webContents.send('navigate-to-setup');
      }
      
      // Check permissions
      checkPermissions().then((permissions) => {
        if (!permissions.fullDiskAccess) {
          showPermissionInstructions('fullDiskAccess');
        } else if (!permissions.automationPermission) {
          showPermissionInstructions('automationPermission');
        }
      });
    }
    
    // Mark first run as complete
    store.set('firstRun', false);
  });
}

// When Electron has finished initialization and is ready to create browser windows
// Auto-updater event handlers
autoUpdater.on('checking-for-update', () => {
  log.info('Checking for update...');
});

autoUpdater.on('update-available', (info) => {
  log.info('Update available:', info);
  updateAvailable = true;
  updateInfo = info;
  
  // Notify the user via the renderer process
  if (mainWindow) {
    mainWindow.webContents.send('update-available', info);
  }
});

autoUpdater.on('update-not-available', (info) => {
  log.info('Update not available:', info);
  updateAvailable = false;
});

autoUpdater.on('error', (err) => {
  log.error('Error in auto-updater:', err);
  if (mainWindow) {
    mainWindow.webContents.send('update-error', err.message);
  }
});

autoUpdater.on('download-progress', (progressObj) => {
  let message = `Download speed: ${progressObj.bytesPerSecond} - Downloaded ${progressObj.percent}%`;
  log.info(message);
  
  // Update progress in the renderer
  if (mainWindow) {
    mainWindow.webContents.send('download-progress', progressObj);
  }
});

autoUpdater.on('update-downloaded', (info) => {
  log.info('Update downloaded:', info);
  updateDownloaded = true;
  updateInfo = info;
  
  // Notify the renderer that update is ready to install
  if (mainWindow) {
    mainWindow.webContents.send('update-downloaded', info);
  }
});

app.whenReady().then(async () => {
  try {
    // Register custom protocol for OAuth callback
    if (process.platform === 'darwin') {
      app.setAsDefaultProtocolClient('ai-clone');
    } else if (process.platform === 'win32') {
      // On Windows, we need to handle protocol registration differently
      // The setAsDefaultProtocolClient method should work, but we'll add a check
      const success = app.setAsDefaultProtocolClient('ai-clone');
      if (!success) {
        console.error('Failed to register protocol handler for ai-clone://');
      } else {
        console.log('Successfully registered protocol handler for ai-clone://');
      }
    } else if (process.platform === 'linux') {
      // Linux requires additional setup which is handled by electron-builder
      app.setAsDefaultProtocolClient('ai-clone');
    }
    
    console.log('Registered custom protocol handler for ai-clone://');
    
    // Create the browser window
    createWindow();
    
    // Create the tray icon
    createTray();
    
    // Start the backend server
    await startBackend();
    
    // Register IPC handlers
    registerIpcHandlers();
    
    // Restore previous state
    if (store.get('autoRespondMessages', false)) {
      toggleMessageListener(true);
    }
    
    if (store.get('autoRespondEmails', false)) {
      toggleEmailListener(true);
    }
    
    // Show first run dialog if needed
    if (store.get('firstRun', true)) {
      showFirstRunDialog();
    }
    
    // Check for updates after a delay
    setTimeout(() => {
      log.info('Checking for updates...');
      autoUpdater.checkForUpdates();
    }, 5000);
    
    // Periodically check for updates
    setInterval(() => {
      log.info('Periodic update check...');
      autoUpdater.checkForUpdates();
    }, 60 * 60 * 1000); // Check every hour
    
    // Check permissions and notify user if needed
    const permissions = await checkPermissions();
    if (mainWindow) {
      mainWindow.webContents.send('permissions-status', permissions);
    }
    
    app.on('activate', () => {
      // On macOS it's common to re-create a window in the app when the
      // dock icon is clicked and there are no other windows open
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      } else {
        mainWindow.show();
      }
    });
  } catch (error) {
    console.error('Error during app initialization:', error);
    dialog.showErrorBox(
      'Initialization Error',
      `Failed to initialize the application: ${error.message}`
    );
  }
});

// Register IPC handlers for communication with renderer process
function registerIpcHandlers() {
  // Auto-update related handlers
  ipcMain.handle('check-for-updates', () => {
    log.info('Manual update check requested');
    autoUpdater.checkForUpdates();
    return { checking: true };
  });
  
  ipcMain.handle('get-update-status', () => {
    return {
      updateAvailable,
      updateDownloaded,
      updateInfo
    };
  });
  
  ipcMain.handle('install-update', () => {
    if (updateDownloaded) {
      log.info('Installing update and restarting...');
      autoUpdater.quitAndInstall(false, true);
      return { installing: true };
    }
    return { installing: false, error: 'No update downloaded' };
  });
  
  ipcMain.handle('download-update', () => {
    if (updateAvailable && !updateDownloaded) {
      log.info('Downloading update...');
      autoUpdater.downloadUpdate();
      return { downloading: true };
    }
    return { downloading: false };
  });
  // Handle renderer process requests
  ipcMain.handle('get-app-info', () => {
    return {
      version: app.getVersion(),
      dataPath: app.getPath('userData'),
      platform: process.platform
    };
  });

  // Handle Gmail OAuth request from renderer
  ipcMain.handle('start-gmail-oauth', async (event, userId) => {
    console.log(`Starting Gmail OAuth for user: ${userId}`);
    
    try {
      // Validate userId to ensure it's not null or undefined
      if (!userId || userId === 'null' || userId === 'undefined') {
        console.error('Invalid user ID provided for OAuth flow:', userId);
        throw new Error('Invalid user ID. Please ensure you are logged in before connecting Gmail.');
      }
      
      // Use api.aiclone.space which points to the EC2 instance for OAuth
      const redirectUri = encodeURIComponent(`https://api.aiclone.space/api/oauth/callback/gmail`);
      const authUrl = `https://api.aiclone.space/api/oauth/authorize/gmail?user_id=${userId}&redirect_uri=${redirectUri}&desktop_app=true&use_system_browser=true`;
      
      // Open the system browser for authentication
      console.log(`Opening system browser for OAuth: ${authUrl}`);
      await shell.openExternal(authUrl);
      
      // Set up a polling mechanism to check OAuth status
      console.log('Setting up OAuth status polling');
      let checkCount = 0;
      const maxChecks = 60; // Check for up to 5 minutes (5s intervals)
      
      const checkOAuthStatus = async () => {
        try {
          // Check the OAuth status via API on the EC2 server
          const response = await axios.get(`https://api.aiclone.space/api/oauth/status/gmail?user_id=${userId}`);
          console.log(`OAuth status check #${checkCount + 1}:`, response.data);
          
          if (response.data.authenticated) {
            console.log('OAuth completed successfully!');
            // Notify the renderer process
            if (mainWindow) {
              mainWindow.webContents.send('oauth-completed', {
                service: 'gmail',
                status: 'success'
              });
            }
            return true;
          }
        } catch (error) {
          console.error(`Error checking OAuth status: ${error.message}`);
        }
        
        checkCount++;
        if (checkCount >= maxChecks) {
          console.log('OAuth status polling timed out');
          // Notify the renderer process
          if (mainWindow) {
            mainWindow.webContents.send('oauth-completed', {
              service: 'gmail',
              status: 'error',
              message: 'OAuth process timed out'
            });
          }
          return true;
        }
        
        // Continue polling
        return false;
      };
      
      // Start polling every 5 seconds
      const pollInterval = setInterval(async () => {
        const done = await checkOAuthStatus();
        if (done) {
          clearInterval(pollInterval);
        }
      }, 5000);
      
      return { success: true, message: 'OAuth process started in system browser' };
    } catch (error) {
      console.error('Error starting OAuth process:', error);
      return { success: false, error: error.message };
    }
  });

  // Handle messages from renderer process
  ipcMain.handle('toggle-message-listener', (event, enabled) => {
    store.set('autoRespondMessages', enabled);
    toggleMessageListener(enabled);
    updateTrayMenu();
    return true;
  });
  
  ipcMain.handle('toggle-email-listener', (event, enabled) => {
    store.set('autoRespondEmails', enabled);
    toggleEmailListener(enabled);
    updateTrayMenu();
    return true;
  });
  
  ipcMain.handle('update-message-settings', (event, settings) => {
    store.set('messageCheckInterval', settings.interval || 5);
    store.set('allowedNumbers', settings.allowedNumbers || []);
    
    if (messageListenerProcess) {
      // Update the message listener with new settings
      toggleMessageListener(false);
      toggleMessageListener(true);
    }
    
    return true;
  });
  
  ipcMain.handle('update-email-settings', (event, settings) => {
    store.set('emailCheckInterval', settings.interval || 60);
    
    if (emailListenerProcess) {
      // Update the email listener with new settings
      toggleEmailListener(false);
      toggleEmailListener(true);
    }
    
    return true;
  });
  
  ipcMain.handle('check-permissions', async () => {
    return await checkPermissions();
  });
  
  ipcMain.handle('show-permission-instructions', (event, permission) => {
    showPermissionInstructions(permission);
    return true;
  });
  
  ipcMain.handle('approve-email', (event, emailId) => {
    const emailScriptPath = getResourcePath('scripts/email_auto_response.py');
    
    try {
      const result = spawn.sync(PYTHON_PATH, [
        emailScriptPath,
        '--approve',
        emailId
      ]);
      
      console.log(`Email approval result: ${result.stdout.toString()}`);
      
      if (result.stderr.length > 0) {
        console.error(`Email approval error: ${result.stderr.toString()}`);
      }
    } catch (error) {
      console.error('Error approving email:', error);
    }
    
    return true;
  });
  
  ipcMain.handle('reject-email', (event, emailId) => {
    const emailScriptPath = getResourcePath('scripts/email_auto_response.py');
    
    try {
      const result = spawn.sync(PYTHON_PATH, [
        emailScriptPath,
        '--reject',
        emailId
      ]);
      
      console.log(`Email rejection result: ${result.stdout.toString()}`);
      
      if (result.stderr.length > 0) {
        console.error(`Email rejection error: ${result.stderr.toString()}`);
      }
    } catch (error) {
      console.error('Error rejecting email:', error);
    }
    
    return true;
  });
  
  // Response overlay handlers
  ipcMain.handle('get-overlay-settings', () => {
    return {
      // Don't return enabled state from persistent storage
      // The overlay toggle is session-only and not persisted
      enabled: false, // Always default to disabled on app start
      suggestionCount: store.get('overlaySuggestionCount', 3),
      checkInterval: store.get('overlayCheckInterval', 5)
    };
  });

  // Get the WebSocket port used by the overlay agent
  ipcMain.handle('get-overlay-port', () => {
    if (overlayAgentManager) {
      return overlayAgentManager.port;
    }
    return null;
  });

  ipcMain.handle('update-overlay-settings', (event, settings) => {
    try {
      // Only update the non-toggle settings in the store
      store.set('overlaySuggestionCount', settings.suggestionCount);
      store.set('overlayCheckInterval', settings.checkInterval);
      
      // Don't persist the enabled state to storage
      // The toggle state is session-only and managed through activate/deactivate handlers
      
      return { success: true };
    } catch (error) {
      console.error('Error updating overlay settings:', error);
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('activate-overlay', () => {
    try {
      if (overlayAgentManager) {
        overlayAgentManager.startAgent();
        return { success: true };
      }
      return { success: false, error: 'Overlay agent manager not initialized' };
    } catch (error) {
      console.error('Error activating overlay agent:', error);
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('deactivate-overlay', () => {
    try {
      if (overlayAgentManager) {
        overlayAgentManager.stopAgent();
        return { success: true };
      }
      return { success: false, error: 'Overlay agent manager not initialized' };
    } catch (error) {
      console.error('Error deactivating overlay agent:', error);
      return { success: false, error: error.message };
    }
  });

  // Handle overlay agent events
  ipcMain.on('send-suggestions', (event, suggestions) => {
    if (overlayAgentManager && overlayAgentManager.isAgentRunning()) {
      // Send suggestions to the overlay agent
      overlayAgentManager.sendSuggestions(suggestions);
    }
  });

  // Handle overlay close button click (completely turn off the overlay)
  ipcMain.on('close-overlay', () => {
    console.log('Main process received close-overlay request');
    if (overlayAgentManager) {
      // Stop the overlay agent
      overlayAgentManager.stopAgent();
      
      // Update the overlay enabled setting in the store
      store.set('overlayEnabled', false);
      console.log('Updated store setting: overlayEnabled = false');
      
      // Notify the renderer process that the overlay has been deactivated
      if (mainWindow && !mainWindow.isDestroyed()) {
        console.log('Sending overlay-deactivated event to main window');
        mainWindow.webContents.send('overlay-deactivated');
      }
    }
  });

  ipcMain.on('overlay-deactivated', () => {
    console.log('Received overlay-deactivated event');
    // Update the store setting
    store.set('overlayEnabled', false);
    
    // Notify the frontend
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('overlay-deactivated');
    }
  });
  
  // NOTE: The code below is commented out because we've switched to the native overlay agent
  // and responseOverlay is no longer defined
  /*
  // Listen for overlay-closed event from the ResponseOverlay class
  responseOverlay.on('overlay-closed', () => {
    console.log('Received overlay-closed event from ResponseOverlay');
    
    // Update the store setting
    store.set('overlayEnabled', false);
    
    // Notify the frontend
    if (mainWindow && !mainWindow.isDestroyed()) {
      console.log('Sending overlay-deactivated event to main window');
      mainWindow.webContents.send('overlay-deactivated');
    }
  });
  */
  
  // We've removed the duplicate overlay-close-requested handler
  // The handler in overlay.js will be used instead

  // NOTE: This handler is commented out because we've switched to the native overlay agent
  // and responseOverlay is no longer defined
  /*
  ipcMain.on('insert-response', (event, response) => {
    if (responseOverlay) {
      responseOverlay.insertResponse(response);
    }
  });
  */
}

// Handle deep linking for OAuth callback
function handleDeepLink(url) {
  if (!url) return;
  
  console.log(`Received deep link URL: ${url}`);
  
  // Check if this is an OAuth callback
  if (url.startsWith('ai-clone://oauth-callback')) {
    try {
      // Parse the URL to get the service and status
      const urlObj = new URL(url);
      const service = urlObj.searchParams.get('service');
      const status = urlObj.searchParams.get('status');
      
      console.log(`OAuth callback received for ${service} with status ${status}`);
      
      // First, make sure the backend is running
      const ensureBackendRunning = () => {
        return new Promise((resolve) => {
          // Check if backend is responding
          fetch(API_URL)
            .then(response => {
              console.log('Backend is running, proceeding with OAuth callback');
              resolve(true);
            })
            .catch(error => {
              console.error(`Backend appears to be down: ${error.message}, attempting to restart`);
              
              // If there's an existing process, attempt to kill it first
              if (backendProcess) {
                try {
                  // Check if process is still running
                  if (backendProcess.exitCode === null) {
                    console.log(`Killing existing backend process with PID ${backendProcess.pid}`);
                    backendProcess.kill();
                  }
                } catch (error) {
                  console.error(`Error killing backend process: ${error.message}`);
                }
              }
              
              // Start a new backend process
              console.log('Starting a new backend process');
              startBackendProcess();
              
              // Wait for backend to start
              console.log('Waiting for backend to start...');
              let attempts = 0;
              const maxAttempts = 10;
              
              const checkBackend = () => {
                attempts++;
                fetch(API_URL)
                  .then(response => {
                    console.log(`Backend is running after restart (attempt ${attempts})`);
                    resolve(true);
                  })
                  .catch(error => {
                    if (attempts < maxAttempts) {
                      console.log(`Backend not responding yet (attempt ${attempts}/${maxAttempts}), retrying...`);
                      setTimeout(checkBackend, 1000);
                    } else {
                      console.error('Maximum attempts reached, proceeding anyway');
                      resolve(false);
                    }
                  });
              };
              
              // Start checking after a delay
              setTimeout(checkBackend, 2000);
            });
        });
      };
      
      // Ensure backend is running, then navigate
      ensureBackendRunning().then(() => {
        // Navigate to the training page with the OAuth result
        if (mainWindow) {
          // First send the event to the renderer process
          mainWindow.webContents.send('oauth-callback', { service, status });
          
          // Make sure the window is visible
          if (!mainWindow.isVisible()) {
            mainWindow.show();
          }
          
          // Focus the window
          if (!mainWindow.isFocused()) {
            mainWindow.focus();
          }
          
          // Navigate to the training page
          // Use the file protocol in production to ensure we load from the local build
          if (process.env.NODE_ENV === 'development') {
            mainWindow.loadURL(`http://localhost:3000/training?service=${service}&status=${status}`);
          } else {
            // For production, we need to load the local file with the query parameters
            const frontendPath = getResourcePath('frontend/build');
            
            console.log(`Loading training page from: ${frontendPath}`);
            
            // In production, use loadFile with hash navigation
            mainWindow.loadFile(path.join(frontendPath, 'index.html'), {
              hash: `training?service=${service}&status=${status}`
            }).then(() => {
              console.log('Successfully loaded training page');
            }).catch(err => {
              console.error('Error loading training page:', err);
            });
          }
        }
      });
    } catch (error) {
      console.error('Error handling OAuth callback:', error);
    }
  }
}

// Register protocol handler for macOS
app.on('open-url', (event, url) => {
  event.preventDefault();
  handleDeepLink(url);
});

// Register protocol handler for Windows
app.on('second-instance', (event, commandLine, workingDirectory) => {
  // Someone tried to run a second instance, we should focus our window
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
    
    // Check if there's a URL in the command line arguments
    const url = commandLine.find(arg => arg.startsWith('ai-clone://'));
    if (url) {
      handleDeepLink(url);
    }
  }
});

// Quit when all windows are closed, except on macOS
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Clean up before quitting
app.on('before-quit', () => {
  app.isQuitting = true;
  
  // NOTE: This code is commented out because we've switched to the native overlay agent
  // and responseOverlay is no longer defined
  /*
  // Deactivate the response overlay
  if (responseOverlay) {
    responseOverlay.deactivate();
  }
  */
  
  // Stop the overlay agent if it's running
  if (overlayAgentManager) {
    overlayAgentManager.stopAgent();
  }
  
  // Stop all processes
  if (backendProcess) backendProcess.kill();
  if (messageListenerProcess) messageListenerProcess.kill();
  if (emailListenerProcess) emailListenerProcess.kill();
});
