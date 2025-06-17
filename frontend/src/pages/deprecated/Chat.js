import React, { useState, useEffect, useRef } from 'react';
import { 
  Container, 
  Typography, 
  Paper, 
  Box, 
  TextField, 
  Button, 
  CircularProgress, 
  Tabs, 
  Tab, 
  Divider,
  IconButton,
  Tooltip,
  Link,
  FormControlLabel,
  Checkbox
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import EmailIcon from '@mui/icons-material/Email';
import ChatIcon from '@mui/icons-material/Chat';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import EditIcon from '@mui/icons-material/Edit';
import FeedbackIcon from '@mui/icons-material/Feedback';
import { Link as RouterLink } from 'react-router-dom';
import axios from '../api/axios';

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isCloneTrained, setIsCloneTrained] = useState(false);
  const [activeChannel, setActiveChannel] = useState('text'); // 'text' or 'email'
  const [emailSubject, setEmailSubject] = useState('');
  const [emailContext, setEmailContext] = useState('');
  const [addToRag, setAddToRag] = useState(false); // New state for RAG opt-in
  const messagesEndRef = useRef(null);

  // Check if clone is trained
  useEffect(() => {
    const checkTrainingStatus = async () => {
      try {
        // Only check status when necessary, don't trigger OpenAI API calls on every page load
        const response = await axios.get('/api/fine-tuning-status', { params: { check_status: false } });
        setIsCloneTrained(response.data.trained);
        
        // If trained, add welcome message with personalized information
        if (response.data.trained) {
          setMessages([
            { id: 1, text: "Hi there! I'm your Alexis AI. I've learned your communication style and will respond just like you would. What would you like to talk about?", sender: 'clone' }
          ]);
        } else if (response.data.in_progress) {
          // If training is in progress, show a message
          setMessages([
            { id: 1, text: "Your Alexis AI is still being trained. Please check back later or continue training to improve it further.", sender: 'system' }
          ]);
        } else {
          // If not trained yet
          setMessages([
            { id: 1, text: "Your Alexis AI hasn't been trained yet. Please complete the training process first.", sender: 'system' }
          ]);
        }
      } catch (error) {
        console.error('Error checking training status:', error);
        // Fallback message
        setMessages([
          { id: 1, text: "Unable to check training status. Please try again later or go to the Training page.", sender: 'system' }
        ]);
      }
    };
    
    checkTrainingStatus();
  }, []);

  // Scroll to bottom of messages
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Function to save conversation to chat history
  const saveConversation = async (userMsg, cloneMsg) => {
    try {
      console.log('Skipping conversation history saving - using session-only conversations');
      
      // Only add to RAG system if explicitly opted-in
      if (addToRag) {
        const timestamp = new Date().toISOString();
        const threadId = `thread-${Date.now()}`;
        
        const historyEntry = {
          user_message: {
            text: userMsg.text,
            sender: 'user',
            timestamp: timestamp,
            thread_id: threadId,
            channel: userMsg.channel,
            subject: userMsg.subject || null
          },
          clone_message: {
            text: cloneMsg.text,
            sender: 'clone',
            timestamp: timestamp,
            thread_id: threadId,
            channel: cloneMsg.channel,
            subject: cloneMsg.subject || null,
            id: cloneMsg.id // Include message ID for feedback reference
          }
        };
        
        await axios.post('/api/add-to-rag', {
          user_message: historyEntry.user_message,
          ai_response: historyEntry.clone_message
        });
        console.log('Conversation added to RAG system');
      } else {
        console.log('Conversation NOT added to RAG system (opt-in not selected)');
      }
    } catch (error) {
      console.error('Error adding to RAG system:', error);
    }
  };

  const handleSendMessage = async () => {
    if (input.trim() === '') return;
    
    // Create message with channel info
    const userMessage = { 
      id: messages.length + 1, 
      text: input, 
      sender: 'user',
      channel: activeChannel,
      subject: activeChannel === 'email' ? emailSubject : null
    };
    
    // Update messages state with new user message
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput('');
    setIsLoading(true);
    
    try {
      let response;
      
      // Use the appropriate API endpoint based on the active channel
      if (activeChannel === 'email') {
        response = await axios.post('/api/chat', {
          message: input,
          conversation_id: `thread-${Date.now()}`,
          subject: emailSubject,
          previous_context: emailContext,
          channel: 'email',
          addToRag: addToRag,
          conversation_history: emailContext ? 
            updatedMessages.filter(msg => msg.channel === 'email' && msg.subject === emailSubject)
              .slice(-20).map(msg => ({
                role: msg.sender === 'user' ? 'user' : 'assistant',
                content: msg.text
              })) : 
            []
        }, {
          timeout: 90000 // Increase timeout to 90 seconds to accommodate Pinecone verification delays
        });
        
        // Add AI response with slight delay to feel more natural
        setTimeout(() => {
          const cloneMessage = { 
            id: response.data.message_id || `msg-${Date.now()}`, // Use server-generated ID or fallback
            text: response.data.response || response.data.draft || "", 
            sender: 'clone',
            channel: 'email',
            subject: emailSubject
          };
          
          setMessages(prevMessages => {
            const updatedMessages = [...prevMessages, cloneMessage];
            return updatedMessages;
          });
          
          // Save to RAG system if opted in
          if (addToRag) {
            saveConversation(userMessage, cloneMessage);
          }
          
          setIsLoading(false);
        }, 500);
      } else {
        response = await axios.post('/api/chat', {
          message: input,
          conversation_id: `thread-${Date.now()}`,
          channel: 'text',
          addToRag: addToRag,
          conversation_history: updatedMessages.slice(-20).map(msg => ({
            role: msg.sender === 'user' ? 'user' : 'assistant',
            content: msg.text
          }))
        }, {
          timeout: 90000 // Increase timeout to 90 seconds to accommodate Pinecone verification delays
        });
        
        // Add AI response with slight delay to feel more natural
        setTimeout(() => {
          const cloneMessage = { 
            id: response.data.message_id || `msg-${Date.now()}`, // Use server-generated ID or fallback
            text: response.data.response, 
            sender: 'clone',
            channel: 'text'
          };
          
          setMessages(prevMessages => {
            const updatedMessages = [...prevMessages, cloneMessage];
            return updatedMessages;
          });
          
          // Save to RAG system if opted in
          if (addToRag) {
            saveConversation(userMessage, cloneMessage);
          }
          
          setIsLoading(false);
        }, 500);
      }
    } catch (error) {
      console.error(`Error getting ${activeChannel} response:`, error);
      
      // Fallback response for demo
      setTimeout(() => {
        const errorMessage = { 
          id: `error-${Date.now()}`,
          text: `I'm having trouble generating a ${activeChannel} response right now. Can you try again?`, 
          sender: 'clone',
          channel: activeChannel
        };
        
        setMessages(prevMessages => [...prevMessages, errorMessage]);
        setIsLoading(false);
      }, 500);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isCloneTrained) {
    return (
      <Container maxWidth="md">
        <Paper elevation={3} sx={{ p: 4, mt: 4, textAlign: 'center' }}>
          <Typography variant="h4" gutterBottom>
            Your Alexis AI isn't trained yet
          </Typography>
          <Typography paragraph>
            Please complete the training process before chatting with your clone.
          </Typography>
          <Button 
            variant="contained" 
            href="/training"
            sx={{ mt: 2 }}
          >
            Start Training
          </Button>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={3} sx={{ height: '80vh', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, borderBottom: '1px solid #e0e0e0' }}>
          <Typography variant="h5">
            Chat with Your Alexis AI
          </Typography>
        </Box>
        
        {/* Channel Tabs */}
        <Tabs
          value={activeChannel}
          onChange={(e, newValue) => setActiveChannel(newValue)}
          aria-label="communication channel tabs"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab 
            icon={<ChatIcon />} 
            label="Text" 
            value="text" 
            iconPosition="start"
            sx={{ minHeight: '48px' }}
          />
          <Tab 
            icon={<EmailIcon />} 
            label="Email" 
            value="email" 
            iconPosition="start"
            sx={{ minHeight: '48px' }}
          />
        </Tabs>
        
        {/* Email-specific fields */}
        {activeChannel === 'email' && (
          <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0' }}>
            <TextField
              fullWidth
              label="Email Subject"
              variant="outlined"
              size="small"
              value={emailSubject}
              onChange={(e) => setEmailSubject(e.target.value)}
              sx={{ mb: 2 }}
              placeholder="Enter email subject..."
            />
            <TextField
              fullWidth
              label="Previous Email Context (Optional)"
              variant="outlined"
              size="small"
              multiline
              rows={2}
              value={emailContext}
              onChange={(e) => setEmailContext(e.target.value)}
              placeholder="Paste previous email content here for context..."
            />
          </Box>
        )}
        
        <Box sx={{ flex: 1, overflowY: 'auto', p: 2, mb: 0, height: activeChannel === 'email' ? 'calc(100% - 250px)' : 'calc(100% - 150px)' }}>
          {messages.map((message) => (
            <Box 
              key={message.id}
              sx={{
                display: 'flex',
                justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
                mb: 2
              }}
            >
              <Paper 
                elevation={1}
                sx={{
                  p: 2,
                  maxWidth: '70%',
                  backgroundColor: message.sender === 'user' ? '#e3f2fd' : 
                                   message.channel === 'email' ? '#f3e5f5' : '#e8f5e9',
                  borderRadius: 2
                }}
              >
                {/* Show email subject if available */}
                {message.channel === 'email' && message.subject && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                      Subject: {message.subject}
                    </Typography>
                    <Divider sx={{ my: 1 }} />
                  </Box>
                )}
                
                {/* Show channel indicator */}
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  {message.channel === 'email' ? (
                    <EmailIcon fontSize="small" sx={{ mr: 0.5, color: '#9c27b0' }} />
                  ) : (
                    <ChatIcon fontSize="small" sx={{ mr: 0.5, color: '#4caf50' }} />
                  )}
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    {message.channel === 'email' ? 'Email' : 'Text Message'}
                  </Typography>
                </Box>
                
                {/* Message content */}
                <Typography variant="body1">{message.text}</Typography>
                
                {/* Quick feedback buttons for clone messages */}
                {message.sender === 'clone' && (
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
                    <Tooltip title="Approve Response">
                      <IconButton 
                        size="small" 
                        color="success"
                        onClick={() => {
                          axios.post('/api/feedback/submit', {
                            message_id: message.id,
                            feedback_type: 'approved'
                          });
                        }}
                      >
                        <ThumbUpIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit Response">
                      <IconButton 
                        size="small" 
                        color="primary"
                        component={RouterLink}
                        to={`/feedback?message_id=${message.id}`}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                )}
              </Paper>
            </Box>
          ))}
          {isLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
              <Paper elevation={1} sx={{ p: 2, backgroundColor: '#f5f5f5', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  <Typography variant="body2">
                    {activeChannel === 'email' ? 'Drafting email...' : 'Typing message...'}
                  </Typography>
                </Box>
              </Paper>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Box>
        
        {/* Message input area */}
        <Box sx={{ display: 'flex', mt: 2, flexDirection: 'column' }}>
          <Box sx={{ display: 'flex', p: 2, borderTop: '1px solid #e0e0e0', flexDirection: 'column' }}>
            <FormControlLabel
              control={
                <Checkbox 
                  checked={addToRag} 
                  onChange={(e) => setAddToRag(e.target.checked)} 
                  color="primary"
                />
              }
              label="Add this conversation to RAG database (only check if responses are accurate)"
              sx={{ mb: 1 }}
            />
            <Box sx={{ display: 'flex' }}>
              <TextField
                fullWidth
                variant="outlined"
                placeholder={activeChannel === 'email' ? 'Type your email content...' : 'Type your message...'}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                multiline={activeChannel === 'email'}
                rows={activeChannel === 'email' ? 3 : 1}
                sx={{ mr: 1 }}
                size="small"
              />
              <Button 
                variant="contained" 
                color="primary" 
                endIcon={<SendIcon />}
                onClick={handleSendMessage}
                disabled={isLoading || input.trim() === ''}
              >
                Send
              </Button>
            </Box>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
};

export default Chat;
