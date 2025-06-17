const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const PORT = 3001;

// Enable CORS for all routes
app.use(cors());

// Parse JSON bodies
app.use(express.json());

// Start the Python Flask server
let pythonProcess = null;

function startPythonServer() {
  console.log('Starting Python Flask server...');
  
  // Get the absolute path to the Python script
  const pythonScriptPath = path.join(__dirname, 'backend', 'app.py');
  
  // Start the Python process
  pythonProcess = spawn('python', [pythonScriptPath], {
    stdio: 'inherit',
    env: { ...process.env }
  });
  
  pythonProcess.on('error', (err) => {
    console.error('Failed to start Python process:', err);
  });
  
  // Handle process exit
  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
    pythonProcess = null;
  });
}

// Start Python server when Node.js server starts
startPythonServer();

// Create a test endpoint
app.get('/api/proxy-test', (req, res) => {
  res.json({ message: 'Node.js proxy server is working!' });
});

// Create a direct test endpoint that doesn't go through the proxy
app.get('/api/test', (req, res) => {
  console.log('Direct test endpoint called');
  res.json({ message: 'Direct API test endpoint is working!' });
});

// Create a direct training-chat endpoint that forwards to Python
app.post('/api/training-chat', async (req, res) => {
  console.log('Direct training-chat endpoint called');
  try {
    // Forward the request to the Python server
    const response = await fetch('http://127.0.0.1:5001/api/training-chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(req.body)
    });
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Error forwarding to Python:', error);
    res.status(500).json({ error: 'Failed to communicate with Python server', details: error.message });
  }
});

// Create a proxy for all /api routes
app.use('/api', createProxyMiddleware({
  target: 'http://127.0.0.1:5001',
  changeOrigin: true,
  pathRewrite: {
    '^/api': '/api' // Keep the /api prefix
  },
  logLevel: 'debug',
  onProxyReq: (proxyReq, req, res) => {
    // Log the request
    console.log(`Proxying ${req.method} request to: ${proxyReq.path}`);
  },
  onError: (err, req, res) => {
    console.error('Proxy error:', err);
    res.status(500).json({ error: 'Proxy error', details: err.message });
  }
}));

// Start the server
app.listen(PORT, () => {
  console.log(`Proxy server running on http://localhost:${PORT}`);
});

// Handle process termination
process.on('SIGINT', () => {
  console.log('Shutting down...');
  if (pythonProcess) {
    console.log('Killing Python process...');
    pythonProcess.kill();
  }
  process.exit();
});
