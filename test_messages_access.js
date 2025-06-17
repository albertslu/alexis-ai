const { exec } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

// Helper function to log to console
function log(message) {
  console.log(`[Test] ${message}`);
}

function logError(message, error) {
  console.error(`[Test] ${message}`, error);
}

// Get the active conversation ID
async function getActiveConversation() {
  log('Attempting to get active conversation');
  
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
        log('Messages app is not running');
        resolve(null);
        return;
      }
      
      // Get the active conversation ID using defaults command
      exec(`defaults read com.apple.MobileSMS.plist CKLastSelectedItemIdentifier | sed 's/^[^-]*-//'`, (error2, stdout2, stderr2) => {
        if (error2) {
          logError('Error getting active conversation ID', error2);
          resolve(null);
          return;
        }
        
        const conversationId = stdout2.trim();
        if (!conversationId) {
          log('No active conversation found');
          resolve(null);
          return;
        }
        
        log(`Found active conversation with ID: ${conversationId}`);
        resolve(conversationId);
      });
    });
  });
}

// Get the latest messages from a conversation
async function getLatestMessage(conversationId) {
  log(`Getting latest messages from conversation: ${conversationId}`);
  
  return new Promise((resolve) => {
    if (!conversationId) {
      log('No conversation ID provided');
      resolve(null);
      return;
    }
    
    // First, check if we have access to the Messages database
    const messagesDbPath = path.join(os.homedir(), 'Library/Messages/chat.db');
    fs.access(messagesDbPath, fs.constants.R_OK, (err) => {
      if (err) {
        logError(`Cannot access Messages database: ${err.message}`);
        log('This likely means Full Disk Access permission is not granted');
        resolve(null);
        return;
      }
      
      // First, let's try a simple query to check if we can access the database at all
      log('Testing basic database access first...');
      const testCommand = `sqlite3 -readonly "${messagesDbPath}" "SELECT count(*) FROM sqlite_master;"`;  
      exec(testCommand, (testError, testStdout, testStderr) => {
        if (testError) {
          logError(`Error accessing Messages database: ${testError.message}`);
          logError(`stderr: ${testStderr}`);
          resolve(null);
          return;
        }
        
        log(`Basic database access successful. Tables count: ${testStdout.trim()}`);
        
        // Extract the phone number from the conversation ID
        // The format is typically 'iMessage;-;+1234567890'
        let phoneNumber = conversationId;
        if (conversationId.includes(';')) {
          const parts = conversationId.split(';');
          phoneNumber = parts[parts.length - 1]; // Get the last part
          log(`Extracted phone number: ${phoneNumber}`);
        }
        
        // Now let's check if the chat exists
        const chatCheckQuery = `SELECT ROWID FROM chat WHERE chat_identifier LIKE '%${phoneNumber.replace(/'/g, "''")}%'`;
        const chatCheckCommand = `sqlite3 -readonly "${messagesDbPath}" "${chatCheckQuery}"`;  
        
        exec(chatCheckCommand, (chatError, chatStdout, chatStderr) => {
          if (chatError) {
            logError(`Error checking chat: ${chatError.message}`);
            resolve(null);
            return;
          }
          
          const chatId = chatStdout.trim();
          if (!chatId) {
            log(`No chat found with identifier: ${conversationId}`);
            resolve(null);
            return;
          }
          
          log(`Found chat with ROWID: ${chatId}`);
          
          // Now use the chat ID to query messages
          const query = `
            SELECT 
              m.text, 
              m.is_from_me, 
              datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') as date_str
            FROM 
              message m
              JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            WHERE 
              cmj.chat_id = ${chatId}
              AND m.text IS NOT NULL
            ORDER BY 
              m.date DESC
            LIMIT 10;
          `;
      
          const command = `sqlite3 -readonly "${messagesDbPath}" "${query.replace(/\n/g, ' ').replace(/"/g, '\"')}"`;
          exec(command, (error, stdout, stderr) => {
            if (error) {
              logError(`Error querying Messages database: ${error.message}`);
              logError(`stderr: ${stderr}`);
              resolve(null);
              return;
            }
            
            const messages = stdout.trim();
            if (!messages) {
              log('No messages found in conversation');
              resolve(null);
              return;
            }
            
            log(`Retrieved ${messages.split('\n').length} messages from conversation`);
            resolve(messages);
          });
        });
      });
    });
  });
}

// Format messages for LLM input
function formatMessagesForLLM(messagesText) {
  if (!messagesText) return null;
  
  const messageLines = messagesText.split('\n');
  const formattedMessages = messageLines.map(line => {
    const parts = line.split('|');
    if (parts.length >= 3) {
      const text = parts[0];
      const isFromMe = parts[1] === '1';
      const date = parts[2];
      return {
        role: isFromMe ? 'user' : 'other',
        content: text,
        timestamp: date
      };
    }
    return null;
  }).filter(msg => msg !== null);
  
  // Reverse to get chronological order
  return formattedMessages.reverse();
}

// Simulate what we would send to the LLM
function prepareLLMInput(messages, conversationId) {
  if (!messages || messages.length === 0) return null;
  
  // Create a prompt that includes conversation context
  const contextMessages = messages.map(msg => 
    `${msg.role === 'user' ? 'You' : 'Them'} (${msg.timestamp}): ${msg.content}`
  ).join('\n');
  
  // Example of what we might send to the LLM
  return {
    messages: messages,
    formattedContext: contextMessages,
    conversationId: conversationId,
    systemPrompt: "You are Alexis, an AI assistant. Generate helpful responses to the conversation above. Provide 3 possible responses of varying tones (friendly, professional, and concise)."
  };
}

// Main test function
async function testMessagesAccess() {
  try {
    // Get the active conversation
    const conversationId = await getActiveConversation();
    if (!conversationId) {
      log('No active conversation found. Please open Messages app and select a conversation.');
      return;
    }
    
    // Get the latest messages
    const messagesText = await getLatestMessage(conversationId);
    if (!messagesText) {
      log('No messages found in the conversation.');
      return;
    }
    
    // Format the messages for LLM input
    const formattedMessages = formatMessagesForLLM(messagesText);
    if (!formattedMessages || formattedMessages.length === 0) {
      log('Could not format messages properly.');
      return;
    }
    
    // Prepare what we would send to the LLM
    const llmInput = prepareLLMInput(formattedMessages, conversationId);
    
    // Log what we would send to the LLM
    log('Data that would be sent to the LLM:');
    console.log(JSON.stringify(llmInput, null, 2));
    
    // Example of how we might generate suggestions
    log('Example suggestions that might be generated:');
    console.log([
      "Sure, I'd be happy to help with that!",
      "Let me look into that for you.",
      "I'll get back to you on this soon."
    ]);
  } catch (error) {
    logError('Error testing Messages access:', error);
  }
}

// Run the test
testMessagesAccess();
