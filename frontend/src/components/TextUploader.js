import React, { useState } from 'react';
import axios from '../api/axios';
import '../styles/TextUploader.css';

const TextUploader = ({ onUploadComplete }) => {
  const [text, setText] = useState('');
  const [sourceType, setSourceType] = useState('conversation');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!text.trim()) {
      setError('Please enter some text');
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await axios.post('/api/upload-text', {
        text,
        source: sourceType
      });

      setSuccess(`Successfully processed ${response.data.message_count} messages!`);
      setText('');
      
      // Call the callback if provided
      if (onUploadComplete) {
        onUploadComplete(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to upload text');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="text-uploader">
      <h2>Upload Your Messages</h2>
      <p>Paste your conversation or messages to train your AI clone</p>
      
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="sourceType">Text Format:</label>
          <select 
            id="sourceType"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
          >
            <option value="conversation">Chat Log (with sender names)</option>
            <option value="messages">Just My Messages (one per line)</option>
          </select>
        </div>
        
        <div className="form-group">
          <label htmlFor="text">Paste your text:</label>
          <textarea
            id="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={10}
            placeholder={sourceType === 'conversation' ? 
              "Albert Lu: Hey how's it going?\n+1 (123) 456-7890: Good, you?\nAlbert Lu: Not bad, just working on this project" :
              "Hey how's it going?\nNot bad, just working on this project\nI'll be there in 10 minutes"}
          />
        </div>
        
        <button 
          type="submit" 
          disabled={isLoading}
          className="submit-button"
        >
          {isLoading ? 'Processing...' : 'Upload'}
        </button>
      </form>

      <div className="instructions">
        <h3>Instructions:</h3>
        <p><strong>Chat Log format:</strong> Paste conversations that include your name or identifier before each message. For example:</p>
        <pre>
          Albert Lu: Hey what's up?
          Friend: Not much, you?
          Albert Lu: Just working on this AI project
        </pre>
        <p>The system will automatically identify which messages are yours based on the name pattern.</p>
        <p><strong>Just My Messages format:</strong> Paste only your messages, with each message on a new line.</p>
        <p>For best results, include at least 10 of your messages that represent your typical writing style.</p>
      </div>
    </div>
  );
};

export default TextUploader;
