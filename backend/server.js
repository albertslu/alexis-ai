const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const bodyParser = require('body-parser');
const path = require('path');
const axios = require('axios');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = 3001;
const FLASK_PORT = 5001;
const FLASK_URL = `http://localhost:${FLASK_PORT}`;

// Enable CORS
app.use(cors());

// Parse JSON bodies
app.use(bodyParser.json());

// Start Flask service if not already running
let flaskProcess = null;

function startFlaskService() {
  console.log('Starting Flask service...');
  
  // Path to Flask app
  const flaskAppPath = path.join(__dirname, 'app.py');
  
  // Spawn Flask process
  flaskProcess = spawn('python', [flaskAppPath]);
  
  flaskProcess.stdout.on('data', (data) => {
    console.log(`Flask stdout: ${data}`);
  });
  
  flaskProcess.stderr.on('data', (data) => {
    console.error(`Flask stderr: ${data}`);
  });
  
  flaskProcess.on('close', (code) => {
    console.log(`Flask process exited with code ${code}`);
    flaskProcess = null;
  });
  
  // Wait for Flask to start up
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve();
    }, 2000); // Wait 2 seconds for Flask to start
  });
}

// Check if Flask service is running
async function checkFlaskService() {
  try {
    const response = await axios.get(`${FLASK_URL}/api/test`);
    return response.status === 200;
  } catch (error) {
    console.error('Flask service not running:', error.message);
    return false;
  }
}

// Middleware to ensure Flask is running
async function ensureFlaskRunning(req, res, next) {
  const isRunning = await checkFlaskService();
  
  if (!isRunning && !flaskProcess) {
    await startFlaskService();
  }
  
  next();
}

// Use middleware for all routes
app.use(ensureFlaskRunning);

// Simple test endpoint
app.get('/api/test', async (req, res) => {
  try {
    console.log('Test endpoint called, forwarding to Flask');
    const response = await axios.get(`${FLASK_URL}/api/test`);
    res.json(response.data);
  } catch (error) {
    console.error('Error forwarding to Flask:', error.message);
    res.status(500).json({ error: 'Error connecting to Flask service' });
  }
});

// Training chat endpoint that forwards to Flask
app.post('/api/training-chat', async (req, res) => {
  try {
    console.log('Training chat endpoint called, forwarding to Flask');
    const response = await axios.post(`${FLASK_URL}/api/training-chat`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('Error forwarding to Flask:', error.message);
    res.status(500).json({ error: 'Error connecting to Flask service' });
  }
});

// Analyze endpoint
app.get('/api/analyze', async (req, res) => {
  try {
    console.log('Analyze endpoint called, forwarding to Flask');
    const response = await axios.get(`${FLASK_URL}/api/analyze`);
    res.json(response.data);
  } catch (error) {
    console.error('Error forwarding to Flask:', error.message);
    res.status(error.response?.status || 500).json(error.response?.data || { error: 'Error connecting to Flask service' });
  }
});

// Start the server
app.listen(PORT, async () => {
  console.log(`Node.js server running on http://localhost:${PORT}`);
  
  // Start Flask service on startup
  const isRunning = await checkFlaskService();
  if (!isRunning) {
    await startFlaskService();
    console.log('Flask service started');
  } else {
    console.log('Flask service already running');
  }
});

// Handle process termination
process.on('SIGINT', () => {
  console.log('Shutting down...');
  if (flaskProcess) {
    console.log('Stopping Flask service...');
    flaskProcess.kill();
  }
  process.exit();
});
