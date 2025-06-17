const { BrowserWindow, ipcMain, screen, app } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const axios = require('axios');
const fs = require('fs');
const log = require('electron-log');
const Store = require('electron-store');
const { EventEmitter } = require('events');

// Initialize store for app settings
const store = new Store({
  name: 'ai-clone-settings'
});

// Configure logging
log.transports.file.level = 'debug';
log.transports.console.level = 'debug';

// Helper function to log to both console and file
function logInfo(message) {
  log.info(`[ResponseOverlay] ${message}`);
  console.log(`[ResponseOverlay] ${message}`);
}

function logError(message, error) {
  log.error(`[ResponseOverlay] ${message}`, error);
  console.error(`[ResponseOverlay] ${message}`, error);
}

class ResponseOverlay extends EventEmitter {
  constructor(mainWindow) {
    super(); // Call EventEmitter constructor
    
    this.mainWindow = mainWindow;
    this.overlayWindow = null;
    this.isActive = false;
    this.messageCheckInterval = null;
    this.lastMessagesActiveState = false; // Track previous state to reduce logging
    this.updateCounter = 0; // Counter for throttling updates
    this.settings = {
      suggestionCount: 3,
      checkInterval: 5
    };
    this.currentContact = null;
    this.currentSuggestions = [];
    
    logInfo('ResponseOverlay initialized');
    
    // Initialize IPC listeners
    this.initializeIpcListeners();
  }
  
  initializeIpcListeners() {
    logInfo('Setting up IPC listeners');
    
    // Remove any existing handler for overlay-close-requested to prevent duplicates
    try {
      ipcMain.removeHandler('overlay-close-requested');
      logInfo('Removed existing overlay-close-requested handler');
    } catch (error) {
      // If there's no handler to remove, this will throw an error which we can ignore
      logInfo('No existing overlay-close-requested handler to remove');
    }
    
    // Register the overlay-close-requested handler at initialization time
    // This ensures it's only registered once, not every time the window is created
    ipcMain.handle('overlay-close-requested', () => {
      logInfo('Overlay close requested');
      if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
        this.overlayWindow.hide();
        // Notify the main process that the overlay was closed
        this.emit('overlay-closed');
      }
      return true; // Acknowledge the request
    });
    
    ipcMain.on('toggle-overlay', (event, isEnabled) => {
      logInfo(`Toggle overlay received: ${isEnabled}`);
      if (isEnabled && !this.isActive) {
        this.activate();
      } else if (!isEnabled && this.isActive) {
        this.deactivate();
      }
    });
    
    ipcMain.on('update-overlay-settings', (event, settings) => {
      logInfo(`Update overlay settings received: ${JSON.stringify(settings)}`);
      this.updateSettings(settings);
    });
    
    ipcMain.on('hide-overlay', () => {
      logInfo('Hide overlay request received');
      this.hideOverlay();
    });
    
    ipcMain.on('close-overlay', () => {
      logInfo('Close overlay request received');
      
      // First hide the overlay to provide immediate visual feedback
      this.hideOverlay();
      
      // Then deactivate it completely
      this.deactivate();
      
      // Update the overlay enabled setting in the store
      store.set('overlayEnabled', false);
      logInfo('Updated store setting: overlayEnabled = false');
      
      // Notify the frontend to update the toggle state
      // Send to both the main window and the overlay window's parent (which is the main window)
      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        logInfo('Sending overlay-deactivated event to main window');
        this.mainWindow.webContents.send('overlay-deactivated');
      }
      
      // Also notify the main process to update its state
      logInfo('Notifying main process of overlay deactivation');
      ipcMain.emit('overlay-deactivated');
    });
    
    ipcMain.on('insert-response', (event, response) => {
      logInfo(`Insert response request received: ${response.substring(0, 30)}...`);
      this.insertResponse(response);
    });
    
    ipcMain.on('set-ignore-mouse-events', (event, ignore) => {
      logInfo(`Set ignore mouse events: ${ignore}`);
      if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
        // When dragging, we need to temporarily disable ignore mouse events
        // but we don't want to activate the window
        this.overlayWindow.setIgnoreMouseEvents(ignore, { forward: true });
      }
    });
    
    ipcMain.on('move-overlay', (event, { deltaX, deltaY }) => {
      if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
        // Get current position
        const [x, y] = this.overlayWindow.getPosition();
        
        // Move the window by the delta amounts
        this.overlayWindow.setPosition(x + deltaX, y + deltaY);
      }
    });
  }
  
  activate() {
    if (this.isActive) {
      logInfo('Overlay already active, ignoring activation request');
      return;
    }
    
    logInfo('Activating response overlay');
    this.isActive = true;
    this.createOverlayWindow();
    this.startMessageMonitoring();
    
    logInfo('Response overlay activated successfully');
  }
  
  deactivate() {
    if (!this.isActive) {
      logInfo('Overlay not active, ignoring deactivation request');
      return;
    }
    
    logInfo('Deactivating response overlay');
    
    this.isActive = false;
    
    // Hide and destroy the overlay window
    if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
      logInfo('Hiding overlay window');
      this.overlayWindow.hide();
    }
    
    // Clear the message check interval
    if (this.messageCheckInterval) {
      logInfo('Clearing message check interval');
      clearInterval(this.messageCheckInterval);
      this.messageCheckInterval = null;
    }
    
    // We don't need to clean up the overlay-close-requested handler here
    // since it's now registered only once in the initializeIpcListeners method
    // and we want to keep it available for future overlay activations
    
    // Clean up any window-specific event listeners if needed
    if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
      // Clean up any window-specific event listeners
      this.overlayWindow.webContents.removeAllListeners('close-overlay-local');
      logInfo('Removed window-specific event listeners');
    }
    
    logInfo('Response overlay deactivated successfully');
  }
  
  createOverlayWindow() {
    logInfo('Creating overlay window');
    
    // Get the path to the overlay HTML file
    const overlayHtmlPath = path.join(__dirname, 'overlay.html');
    const preloadJsPath = path.join(__dirname, 'preload.js');
    
    // Check if files exist
    const htmlExists = fs.existsSync(overlayHtmlPath);
    const preloadExists = fs.existsSync(preloadJsPath);
    
    logInfo(`Overlay HTML path: ${overlayHtmlPath} (exists: ${htmlExists})`);
    logInfo(`Preload JS path: ${preloadJsPath} (exists: ${preloadExists})`);
    
    // Create a transparent, frameless window for the overlay
    try {
      this.overlayWindow = new BrowserWindow({
        width: 300,
        height: 150,
        transparent: true,
        frame: false,
        alwaysOnTop: true,
        skipTaskbar: true,
        show: false,
        movable: true, // Allow the window to be moved
        resizable: false,
        focusable: true, // Make it focusable so clicks work
        hasShadow: false, // Remove shadow for better aesthetics
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
          preload: preloadJsPath
        }
      });
      
      // Prevent the window from activating the app when clicked
      this.overlayWindow.setAlwaysOnTop(true, 'floating', 1);
      this.overlayWindow.setVisibleOnAllWorkspaces(true, {visibleOnFullScreen: true});
      this.overlayWindow.setFullScreenable(false);
      
      logInfo('Overlay window created successfully');
      
      // Load the overlay HTML
      this.overlayWindow.loadFile(overlayHtmlPath);
      
      // Set up non-activating clicks
      this.overlayWindow.webContents.on('did-finish-load', () => {
        // Don't set click-through by default, let the window be interactive
        // This allows buttons to be clicked while still not activating the main app
        this.overlayWindow.setIgnoreMouseEvents(false);
        
        // Set up event listeners for interactive elements
        this.overlayWindow.webContents.send('setup-non-activating-clicks');
        
        // We've moved the overlay-close-requested handler to initializeIpcListeners
        // to prevent duplicate handler registration
        
        // Handle the regular close event locally
        this.overlayWindow.webContents.on('close-overlay-local', () => {
          logInfo('Close overlay message received (local)');
          if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
            this.overlayWindow.hide();
            // Notify the main process that the overlay was closed
            this.emit('overlay-closed');
          }
        });
        
        logInfo('Interactive overlay setup complete');
      });
      
      // Hide the overlay initially
      this.overlayWindow.hide();
      
      // Handle window close
      this.overlayWindow.on('closed', () => {
        logInfo('Overlay window closed');
        this.overlayWindow = null;
      });
      
      // Log errors when loading the HTML
      this.overlayWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        logError(`Failed to load overlay HTML: ${errorDescription} (${errorCode})`);
      });
      
      // Log when HTML is loaded successfully
      this.overlayWindow.webContents.on('did-finish-load', () => {
        logInfo('Overlay HTML loaded successfully');
      });
    } catch (error) {
      logError('Error creating overlay window', error);
    }
  }
  
  async startMessageMonitoring() {
    logInfo('Starting message monitoring');
    
    // Initial check to show the overlay when activated
    try {
      if (this.isActive) {
        const isMessagesActive = await this.isMessagesAppActive();
        if (isMessagesActive) {
          await this.showTestOverlay();
        }
      }
    } catch (error) {
      logError('Error during initial overlay display', error);
    }
    
    // Check every 1 second to show/hide overlay based on whether Messages is active
    // This provides more responsive UI without being too resource-intensive
    this.messageCheckInterval = setInterval(async () => {
      try {
        // Only proceed if overlay is active (user has toggled it on)
        if (!this.isActive) {
          return;
        }
        
        const isMessagesActive = await this.isMessagesAppActive();
        
        // Only log when state changes to reduce noise
        if (this.lastMessagesActiveState !== isMessagesActive) {
          logInfo(`Messages app active state changed: ${isMessagesActive}`);
          this.lastMessagesActiveState = isMessagesActive;
        }
        
        // Show overlay if Messages is active, hide if not
        if (isMessagesActive) {
          // If overlay is not visible, show it
          if (this.overlayWindow && !this.overlayWindow.isDestroyed() && !this.overlayWindow.isVisible()) {
            await this.showTestOverlay();
          } 
          // If overlay is already visible, update suggestions less frequently (every 3 cycles)
          else if (this.overlayWindow && !this.overlayWindow.isDestroyed() && this.overlayWindow.isVisible()) {
            // Only update suggestions every 3 seconds to reduce processing load
            if (this.updateCounter % 3 === 0) {
              // Get the active conversation
              const activeConversation = await this.getActiveConversation();
              
              if (activeConversation) {
                // Get the latest messages and update suggestions
                const conversationMessages = await this.getLatestMessage(activeConversation);
                
                // Update the overlay with new suggestions if we have messages
                if (conversationMessages) {
                  await this.generateSuggestions(conversationMessages, activeConversation);
                }
              }
            }
            
            // Increment counter for throttling updates
            this.updateCounter = (this.updateCounter + 1) % 30; // Reset after 30 to avoid potential overflow
          }
        } else {
          // Hide the overlay if Messages is not active
          if (this.overlayWindow && !this.overlayWindow.isDestroyed() && this.overlayWindow.isVisible()) {
            this.hideOverlay();
          }
        }
      } catch (error) {
        logError('Error monitoring messages', error);
      }
    }, 1000); // Check every 1 second instead of 5 seconds
    
    logInfo('Message monitoring started');
  }
  
  async isMessagesAppActive() {
    logInfo('Messages app running check');
    
    return new Promise((resolve) => {
      // First check if Messages is running
      const runningScript = `
        tell application "System Events"
          if exists (processes where name is "Messages") then
            return true
          else
            return false
          end if
        end tell
      `;
      
      exec(`osascript -e '${runningScript}'`, (error, stdout, stderr) => {
        if (error) {
          logError('Error checking if Messages app is running', error);
          resolve(false);
          return;
        }
        
        const isRunning = stdout.trim().toLowerCase() === 'true';
        logInfo(`Messages app running: ${isRunning}`);
        
        if (!isRunning) {
          resolve(false);
          return;
        }
        
        // Then check if it's frontmost (active)
        const frontmostScript = `
          tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            if frontApp is "Messages" then
              return true
            else
              return false
            end if
          end tell
        `;
        
        exec(`osascript -e '${frontmostScript}'`, (error2, stdout2, stderr2) => {
          if (error2) {
            logError('Error checking if Messages is frontmost', error2);
            // If we can't determine if it's frontmost, just use the running state
            resolve(isRunning);
          } else {
            const isFrontmost = stdout2.trim().toLowerCase() === 'true';
            logInfo(`Messages app is frontmost: ${isFrontmost}`);
            resolve(isFrontmost);
          }
        });
      });
    });
  }
  
  async getActiveConversation() {
    logInfo('Attempting to get active conversation');
    
    return new Promise((resolve) => {
      // First check if Messages is running
      const isRunningScript = `
        tell application "System Events"
          if exists (processes where name is "Messages") then
            return true
          else
            return false
          end if
        end tell
      `;
      
      exec(`osascript -e '${isRunningScript}'`, (error, stdout, stderr) => {
        if (error) {
          logError('Error checking if Messages is running', error);
          resolve(null);
          return;
        }
        
        const isRunning = stdout.trim().toLowerCase() === 'true';
        if (!isRunning) {
          logInfo('Messages app is not running');
          resolve(null);
          return;
        }
        
        // Get the active conversation ID using defaults command
        // This is more reliable than AppleScript for getting the conversation ID
        exec(`defaults read com.apple.MobileSMS.plist CKLastSelectedItemIdentifier | sed 's/^[^-]*-//'`, (error2, stdout2, stderr2) => {
          if (error2) {
            logError('Error getting active conversation ID', error2);
            resolve(null);
            return;
          }
          
          const conversationId = stdout2.trim();
          if (!conversationId) {
            logInfo('No active conversation found');
            resolve(null);
            return;
          }
          
          logInfo(`Found active conversation with ID: ${conversationId}`);
          resolve(conversationId);
        });
      });
    });
  }
  
  async getLatestMessage(conversationId) {
    logInfo(`Getting latest messages from conversation: ${conversationId}`);
    
    // Use direct SQLite access to get messages from the database
    // This is more reliable than AppleScript for getting message content
    return new Promise((resolve) => {
      if (!conversationId) {
        logInfo('No conversation ID provided');
        resolve(null);
        return;
      }
      
      // First, check if we have access to the Messages database
      const os = require('os');
      const path = require('path');
      const messagesDbPath = path.join(os.homedir(), 'Library/Messages/chat.db');
      fs.access(messagesDbPath, fs.constants.R_OK, (err) => {
        if (err) {
          logError(`Cannot access Messages database: ${err.message}`);
          logInfo('This likely means Full Disk Access permission is not granted');
          resolve(null);
          return;
        }
        
        // Use the sqlite3 command line tool to query the database
        // This avoids having to bundle a SQLite library with the app
        const query = `
          SELECT 
            m.text, 
            m.is_from_me, 
            datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') as date_str
          FROM 
            message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            JOIN chat c ON cmj.chat_id = c.ROWID
          WHERE 
            c.chat_identifier = '${conversationId.replace(/'/g, "''")}'
            AND m.text IS NOT NULL
          ORDER BY 
            m.date DESC
          LIMIT 10;
        `;
        
        const command = `sqlite3 -readonly "${messagesDbPath}" "${query.replace(/\n/g, ' ').replace(/"/g, '\"')}"`;        
        exec(command, (error, stdout, stderr) => {
          if (error) {
            logError(`Error querying Messages database: ${error.message}`);
            resolve(null);
            return;
          }
          
          const messages = stdout.trim();
          if (!messages) {
            logInfo('No messages found in conversation');
            resolve(null);
            return;
          }
          
          logInfo(`Retrieved ${messages.split('\n').length} messages from conversation`);
          resolve(messages);
        });
      });
    });
  }
  
  async showTestOverlay() {
    logInfo('Generating AI suggestions for overlay');
    
    try {
      // Get the active conversation ID
      const conversationId = await this.getActiveConversation();
      
      // Show blank overlay if no conversation is selected
      if (!conversationId) {
        logInfo('No active conversation found, showing blank overlay');
        
        if (this.overlayWindow) {
          // Show blank overlay with empty suggestions
          this.overlayWindow.webContents.send('update-suggestions', {
            contact: 'Conversation',
            message: '',
            suggestions: []
          });
          
          // Position and show the overlay
          this.positionOverlayNearMessagesInput();
          this.overlayWindow.showInactive();
          logInfo('Blank overlay is now visible');
        }
        return;
      }
      
      // Get the latest messages from the conversation
      const messagesText = await this.getLatestMessage(conversationId);
      
      if (!messagesText) {
        logInfo('No recent messages found, showing blank overlay');
        
        // Show blank overlay with empty suggestions
        if (this.overlayWindow) {
          this.overlayWindow.webContents.send('update-suggestions', {
            contact: conversationId,
            message: '',
            suggestions: []
          });
          
          // Position and show the overlay
          this.positionOverlayNearMessagesInput();
          this.overlayWindow.showInactive();
          logInfo('Blank overlay is now visible');
        }
        return;
      }
      
      // Format the messages for display
      const messageLines = messagesText.split('\n');
      const formattedMessages = messageLines.map(line => {
        const parts = line.split('|');
        if (parts.length >= 3) {
          const text = parts[0];
          const isFromMe = parts[1] === '1';
          const date = parts[2];
          return `${isFromMe ? 'You' : 'Them'} (${date}): ${text}`;
        }
        return line;
      }).join('\n');
      
      // Generate AI suggestions based on the latest messages
      await this.generateSuggestions(formattedMessages, conversationId);
      
      // Position and show the overlay
      this.positionOverlayNearMessagesInput();
      this.overlayWindow.showInactive();
      logInfo('AI suggestions overlay is now visible');
    } catch (error) {
      // Show blank overlay on error
      if (this.overlayWindow) {
        this.overlayWindow.webContents.send('update-suggestions', {
          contact: 'Messages',
          message: '',
          suggestions: []
        });
        
        this.positionOverlayNearMessagesInput();
        this.overlayWindow.showInactive();
        logInfo('Blank overlay shown due to error');
      }
      
      logError('Error showing AI suggestions overlay:', error);
    }
  }
  
  async generateSuggestions(message, contact) {
    try {
      // Get conversation context for this contact
      const context = await this.getConversationContext(contact);
      
      // Call the AI backend to generate suggestions
      const response = await axios.post('http://localhost:5002/api/chat', {
        message: message,
        channel: 'imessage',
        contactName: contact,
        conversationHistory: context.conversationHistory || [],
        generateSuggestions: true
      });
      
      // Extract suggestions from response
      const suggestions = response.data.suggestions || [response.data.response];
      
      if (suggestions.length > 0) {
        this.currentSuggestions = suggestions;
        
        // Update the overlay with new suggestions
        if (this.overlayWindow) {
          this.overlayWindow.webContents.send('update-suggestions', {
            contact,
            message,
            suggestions
          });
          
          // Position and show the overlay
          this.positionOverlayNearMessagesInput();
          this.overlayWindow.showInactive();
        }
      }
    } catch (error) {
      console.error('Error generating suggestions:', error);
    }
  }
  
  async getConversationContext(contact) {
    // This would typically query your database for conversation history
    // For now, we'll return an empty context
    
    // In a real implementation, you would:
    // 1. Query your database for previous conversations with this contact
    // 2. Get any contact-specific information
    // 3. Return the context for AI processing
    
    return {
      conversationHistory: []
    };
  }
  
  async positionOverlayNearMessagesInput() {
    try {
      // Get the position of the Messages input field
      const position = await this.getMessagesInputPosition();
      
      if (position) {
        const { x, y, width } = position;
        
        // Position the overlay above the input field
        this.overlayWindow.setPosition(
          Math.round(x + width/2 - 150), // Center horizontally
          Math.round(y - 160)            // Position above input
        );
      } else {
        // Fallback: position in the bottom right of the screen
        const { width, height } = screen.getPrimaryDisplay().workAreaSize;
        this.overlayWindow.setPosition(width - 350, height - 200);
      }
    } catch (error) {
      console.error('Error positioning overlay:', error);
    }
  }
  
  async getMessagesInputPosition() {
    return new Promise((resolve) => {
      const script = `
        tell application "System Events"
          tell process "Messages"
            try
              set textArea to text area 1 of scroll area 1 of window 1
              set position to position of textArea
              set size to size of textArea
              return (item 1 of position) & "," & (item 2 of position) & "," & (item 1 of size) & "," & (item 2 of size)
            on error
              return ""
            end try
          end tell
        end tell
      `;
      
      exec(`osascript -e '${script}'`, (error, stdout) => {
        if (error || !stdout.trim()) {
          resolve(null);
        } else {
          const [x, y, width, height] = stdout.trim().split(',').map(Number);
          resolve({ x, y, width, height });
        }
      });
    });
  }
  
  hideOverlay() {
    logInfo('Hiding overlay window');
    if (this.overlayWindow) {
      try {
        this.overlayWindow.hide();
        logInfo('Overlay window hidden successfully');
      } catch (error) {
        logError('Error hiding overlay window', error);
      }
    } else {
      logInfo('No overlay window to hide');
    }
  }
  
  async insertResponse(response) {
    if (!this.currentContact) return;
    
    try {
      // Use AppleScript to insert the response into Messages
      const script = `
        tell application "Messages"
          set targetBuddy to "${this.currentContact}"
          set targetService to id of 1st service whose service type = iMessage
          set targetBuddy to buddy targetBuddy of service id targetService
          
          tell application "System Events"
            tell process "Messages"
              keystroke "${response.replace(/"/g, '\\"')}"
            end tell
          end tell
        end tell
      `;
      
      exec(`osascript -e '${script}'`, (error) => {
        if (error) {
          console.error('Error inserting response:', error);
        } else {
          console.log('Response inserted successfully');
          
          // Hide the overlay after inserting the response
          this.hideOverlay();
        }
      });
    } catch (error) {
      console.error('Error inserting response:', error);
    }
  }
  
  updateSettings(settings) {
    // Update overlay settings
    console.log('Updating overlay settings:', settings);
    
    // Restart message monitoring with new settings if active
    if (this.isActive) {
      this.deactivate();
      this.activate();
    }
  }
}

module.exports = ResponseOverlay;
