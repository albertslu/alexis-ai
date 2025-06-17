const { spawn } = require('child_process');
const path = require('path');
const WebSocket = require('ws');
const { app } = require('electron');
const EventEmitter = require('events');
const axios = require('axios');
const fs = require('fs');

// Import utility functions
const { PROJECT_ROOT, getResourcePath, findPythonPath } = require('./utils.js');

// Custom debug logging function that writes to a specific file
function debugLog(message) {
  const logPath = path.join(app.getPath('userData'), 'debug.log');
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}\n`;
  
  try {
    fs.appendFileSync(logPath, logMessage);
  } catch (error) {
    console.error(`Failed to write to debug log: ${error.message}`);
  }
  
  // Also log to console
  console.log(message);
}

/**
 * Manages the native overlay agent process and communication
 */
class OverlayAgentManager {
  constructor() {
    this.agentProcess = null;
    this.wsServer = null;
    this.wsConnections = [];
    this.isRunning = false;
    this.port = null; // Will be dynamically assigned
    this.eventEmitter = new EventEmitter();
  }

  /**
   * Start the overlay agent process and WebSocket server
   */
  startAgent() {
    // VERIFICATION LOG: This will show if startAgent is called
    debugLog('========== OVERLAY AGENT MANAGER: startAgent called ==========');
    
    if (this.isRunning) {
      debugLog('Overlay agent is already running');
      return;
    }

    try {
      // Start WebSocket server to communicate with the agent
      this.startWebSocketServer();
      
      // Start the overlay agent process
      // Handle path resolution differently for production (asar) vs development
      let agentPath;
      const appPath = app.getAppPath();
      const isAsar = appPath.includes('app.asar');
      
      if (isAsar) {
        // In production, resources are outside the asar archive
        agentPath = path.join(path.dirname(appPath), 'resources', 'overlay-agent.app', 'Contents', 'MacOS', 'overlay-agent');
      } else {
        // In development
        agentPath = path.join(appPath, 'resources', 'overlay-agent.app', 'Contents', 'MacOS', 'overlay-agent');
      }
      
      console.log(`Starting overlay agent from: ${agentPath} with port ${this.port}`);
      console.log(`App path: ${appPath}, isAsar: ${isAsar}`);
      
      // Pass the dynamically assigned port to the overlay agent
      this.agentProcess = spawn(agentPath, [`--port=${this.port}`], { detached: false });
      
      this.agentProcess.stdout.on('data', (data) => {
        console.log(`Overlay agent stdout: ${data}`);
      });
      
      this.agentProcess.stderr.on('data', (data) => {
        console.error(`Overlay agent stderr: ${data}`);
      });
      
      this.agentProcess.on('close', (code) => {
        console.log(`Overlay agent process exited with code ${code}`);
        this.isRunning = false;
        this.agentProcess = null;
      });
      
      this.agentProcess.on('error', (err) => {
        console.error(`Failed to start overlay agent: ${err}`);
        this.isRunning = false;
        this.agentProcess = null;
      });
      
      this.isRunning = true;
      console.log('Overlay agent started');
    } catch (error) {
      console.error(`Error starting overlay agent: ${error}`);
    }
  }

  /**
   * Stop the overlay agent process and WebSocket server
   */
  stopAgent() {
    if (!this.isRunning) {
      console.log('Overlay agent is not running');
      return;
    }

    try {
      // Stop WebSocket server
      this.stopWebSocketServer();
      
      // Kill the overlay agent process
      if (this.agentProcess) {
        console.log('Stopping overlay agent process');
        this.agentProcess.kill();
        this.agentProcess = null;
      }
      
      // Stop the active chat detector
      // Don't await the stopChatDetector call to maintain the original synchronous behavior
      this.stopChatDetector().catch(error => {
        debugLog(`Error stopping chat detector: ${error.message}, but continuing with overlay agent shutdown`);
        // Continue even if chat detector fails to stop
      });
      
      this.isRunning = false;
      console.log('Overlay agent stopped');
    } catch (error) {
      console.error(`Error stopping overlay agent: ${error}`);
    }
  }

  /**
   * Start WebSocket server to communicate with the overlay agent
   */
  startWebSocketServer() {
    if (this.wsServer) {
      console.log('WebSocket server is already running');
      return;
    }

    try {
      // Create server without specifying port (will use any available port)
      this.wsServer = new WebSocket.Server({ port: 0 });
      
      // Get the dynamically assigned port
      this.port = this.wsServer.address().port;
      console.log(`WebSocket server started on dynamically assigned port ${this.port}`);
      
      this.wsServer.on('connection', (ws) => {
        console.log('Overlay agent connected to WebSocket');
        this.wsConnections.push(ws);
        
        ws.on('message', (message) => {
          try {
            const data = JSON.parse(message);
            console.log('Received message from overlay agent:', data);
            this.handleAgentMessage(data, ws);
          } catch (error) {
            console.error(`Error parsing message from overlay agent: ${error}`);
          }
        });
        
        ws.on('close', () => {
          console.log('Overlay agent disconnected from WebSocket');
          this.wsConnections = this.wsConnections.filter(conn => conn !== ws);
        });
        
        // Send initial data to the agent
        this.sendMessage(ws, { type: 'connected', message: 'Connected to Alexis AI' });
      });
      
      this.wsServer.on('error', (error) => {
        console.error(`WebSocket server error: ${error}`);
      });
      
      console.log(`WebSocket server started on port ${this.port}`);
    } catch (error) {
      console.error(`Error starting WebSocket server: ${error}`);
    }
  }

  /**
   * Stop WebSocket server
   */
  stopWebSocketServer() {
    if (!this.wsServer) {
      return;
    }

    try {
      // Close all connections
      this.wsConnections.forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      });
      this.wsConnections = [];
      
      // Close the server
      this.wsServer.close();
      this.wsServer = null;
      console.log('WebSocket server stopped');
    } catch (error) {
      console.error(`Error stopping WebSocket server: ${error}`);
    }
  }

  /**
   * Send a message to the overlay agent
   * @param {WebSocket|null} ws - WebSocket connection or null to broadcast to all
   * @param {Object} data - Data to send
   */
  sendMessage(ws, data) {
    try {
      const message = JSON.stringify(data);
      
      if (ws) {
        // Send to specific connection
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(message);
        }
      } else {
        // Broadcast to all connections
        this.wsConnections.forEach(conn => {
          if (conn.readyState === WebSocket.OPEN) {
            conn.send(message);
          }
        });
      }
    } catch (error) {
      console.error(`Error sending message to overlay agent: ${error}`);
    }
  }

  /**
   * Handle messages from the overlay agent
   * @param {Object} data - Message data
   * @param {WebSocket} ws - WebSocket connection
   */
  handleAgentMessage(data, ws) {
    switch (data.type) {
      case 'suggestion_selected':
        console.log(`User selected suggestion ${data.index}: "${data.text}" (inserted: ${data.inserted})`);
        
        // Emit an event that the renderer process can listen for
        if (this.eventEmitter) {
          this.eventEmitter.emit('suggestion-selected', {
            index: data.index,
            text: data.text,
            inserted: data.inserted
          });
        }
        break;
        
      case 'conversation_context':
        console.log(`Received conversation context from overlay agent (${data.context.length} chars)`);
        
        // Emit an event that the renderer process can listen for
        if (this.eventEmitter) {
          this.eventEmitter.emit('conversation-context', {
            context: data.context
          });
        }
        
        // Generate suggestions based on the context
        this.generateSuggestions(data.context);
        break;
        
      case 'status':
        console.log(`Overlay agent status: ${data.status}`);
        break;
        
      default:
        console.log(`Unknown message type: ${data.type}`);
    }
  }

  /**
   * Send suggestions to the overlay agent
   * @param {Array<string>} suggestions - Array of suggestion strings
   */
  sendSuggestions(suggestions) {
    if (!this.isRunning || this.wsConnections.length === 0) {
      console.log('Cannot send suggestions: overlay agent not connected');
      return;
    }

    this.sendMessage(null, {
      type: 'suggestions',
      suggestions: suggestions
    });
  }
  
  /**
   * Generate message suggestions based on conversation context
   * @param {string} context - The conversation context
   */
  async generateSuggestions(context) {
    try {
      console.log('Generating suggestions based on conversation context');
      
      // API URL for message suggestions
      const apiUrl = 'http://localhost:5002/api/message-suggestions';
      
      // Call the backend API to generate suggestions
      const response = await axios.get(apiUrl, {
        params: { context }
      });
      
      if (response.data && response.data.success && response.data.suggestions) {
        console.log('Received suggestions from API:', response.data.suggestions);
        this.sendSuggestions(response.data.suggestions);
      } else {
        console.error('Invalid response from suggestions API:', response.data);
        // Use fallback suggestions
        this.sendSuggestions([
          'I\'ll get back to you soon',
          'Let me think about that',
          'Thanks for letting me know'
        ]);
      }
    } catch (error) {
      console.error(`Error generating suggestions: ${error}`);
      // Send fallback suggestions
      this.sendSuggestions([
        'I\'ll get back to you soon',
        'Let me think about that',
        'Thanks for letting me know'
      ]);
    }
  }
  
  // Active chat detector methods have been moved to the React frontend (IMessagePage.js)
  
  /**
   * Send suggestions to the overlay agent
   * @param {Array<string>} suggestions - Array of suggestion strings
   */
  sendSuggestions(suggestions) {
    if (!this.isRunning || this.wsConnections.length === 0) {
      console.log('Cannot send suggestions: overlay agent not connected');
      return;
    }

    this.sendMessage(null, {
      type: 'suggestions',
      suggestions: suggestions
    });
    
    console.log('Sent suggestions to overlay agent:', suggestions);
  }

  /**
   * Check if the overlay agent is running
   * @returns {boolean} - True if running, false otherwise
   */
  isAgentRunning() {
    return this.isRunning;
  }
}

module.exports = OverlayAgentManager;
