#!/usr/bin/env python3
"""
Channel-Specific Processing for AI Clone

This module handles channel-specific processing for different communication channels
such as text messages, emails, etc. It adapts the retrieval and response generation
based on the communication channel.
"""

import os
import json
import re
from datetime import datetime

class ChannelProcessor:
    """
    Channel-specific processing for different communication channels.
    
    This class provides methods to adapt the retrieval and response generation
    based on the communication channel (text, email, etc.).
    """
    
    def __init__(self):
        """
        Initialize the channel processor.
        """
        # Channel-specific weights for retrieval
        self.channel_weights = {
            'text': 1.5,     # Weight for text message examples
            'email': 1.5,    # Weight for email examples
            'default': 1.0   # Default weight
        }
        
        # Channel-specific formality scores (0-1)
        self.channel_formality = {
            'text': 0.2,      # Very informal
            'email': 0.7,     # More formal
            'default': 0.5    # Medium formality
        }
    
    def detect_channel(self, message, metadata=None):
        """
        Detect the likely channel for a message.
        
        Args:
            message: User message
            metadata: Optional metadata about the message
            
        Returns:
            Detected channel (text, email, etc.)
        """
        # If metadata specifies the channel, use that
        if metadata and 'channel' in metadata:
            return metadata['channel']
        
        # Otherwise try to detect from the message
        # Email indicators
        email_indicators = [
            r'^(Hi|Hello|Dear)\s+[\w\s]+,',  # Formal greeting
            r'(Best|Regards|Sincerely|Thank you)[,\s]*$',  # Sign-off
            r'^On\s+[\w,\s]+wrote:',  # Reply format
            r'Subject:',  # Email header
        ]
        
        for pattern in email_indicators:
            if re.search(pattern, message, re.IGNORECASE | re.MULTILINE):
                return 'email'
        
        # Default to text for short messages
        if len(message.split()) < 20 and '\n' not in message:
            return 'text'
        
        # Default channel
        return 'default'
    
    def weight_rag_results(self, results, channel):
        """
        Apply channel-specific weighting to RAG results.
        
        Args:
            results: Original RAG results
            channel: Current communication channel
            
        Returns:
            Weighted RAG results
        """
        weighted_results = []
        
        for result in results:
            weight = 1.0
            result_channel = result.get('metadata', {}).get('channel', 'default')
            
            # Apply channel-specific weight
            if result_channel == channel:
                weight *= self.channel_weights.get(channel, 1.0)
            
            # For emails, match formality level
            if channel == 'email' and result_channel == 'email':
                result_formality = result.get('metadata', {}).get('formality_score', 0.5)
                target_formality = self.channel_formality.get('email', 0.7)
                
                # Boost weight based on formality match
                formality_match = 1.0 - abs(target_formality - result_formality)
                weight *= (0.5 + formality_match)
            
            weighted_results.append((result, weight))
        
        # Sort by weighted score
        weighted_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results
        return [item[0] for item in weighted_results]
    
    def prepare_channel_specific_prompt(self, channel, base_prompt):
        """
        Prepare a channel-specific system prompt.
        
        Args:
            channel: Communication channel
            base_prompt: Base system prompt
            
        Returns:
            Channel-specific system prompt
        """
        if channel == 'email':
            # Email-specific instructions that match our fine-tuning format
            return """You are an AI clone that responds to messages as if you were the user. The following is an email conversation. Respond in the user's email style, which is typically more formal and structured than text messages.

""" + base_prompt + """

This is an email response. Follow these guidelines:
1. Always begin with an appropriate greeting based on the formality of the incoming email (e.g., "Hi [Name]," for casual, "Dear [Name]," for formal).
2. Maintain appropriate formality throughout - match the tone of the original email.
3. Address ALL points and questions raised in the original email.
4. Structure your response with clear paragraphs for readability.
5. Use proper punctuation and capitalization.
6. Always include an appropriate sign-off (e.g., "Best regards," "Cheers," "Thanks,") followed by your name.
7. For professional emails, be thorough but concise.
8. For complex inquiries, use bullet points or numbered lists when appropriate.
9. If the email contains time-sensitive matters, acknowledge the timeline in your response.
"""
        
        elif channel == 'text':
            # Text message-specific instructions that match our fine-tuning format
            return """You are an AI clone that responds to messages as if you were the user. The following is a text message conversation. Respond in the user's texting style, which is typically casual with minimal capitalization and punctuation.

""" + base_prompt + """

This is a text message response. Follow these guidelines:
1. Keep it conversational and natural - write exactly as you would in a real text message.
2. Be concise but complete - address the question or topic fully while keeping the response brief.
3. Use casual language, contractions, and occasional abbreviations when appropriate.
4. Limit each message to 1-3 sentences when possible.
5. It's okay to use lowercase and minimal punctuation, but maintain readability.
6. Use emojis sparingly and only when they match your typical texting style.
7. For group chats, consider the context and who else might be in the conversation.
8. If responding to multiple questions, address each one briefly.
"""
        
        else:
            # Default prompt
            return base_prompt + """

Respond naturally in a way that matches the tone and style of the incoming message.
"""
    
    def format_response_for_channel(self, response, channel, metadata=None):
        """
        Format a response for a specific channel.
        
        Args:
            response: Generated response
            channel: Communication channel
            metadata: Additional metadata
            
        Returns:
            Formatted response
        """
        if channel == 'email':
            # Process email response
            response = self._ensure_email_formatting(response, metadata)
        
        elif channel == 'text':
            # Process text message response
            response = self._ensure_text_formatting(response)
        
        return response
    
    def _ensure_email_formatting(self, response, metadata=None):
        """
        Ensure proper email formatting with greeting and sign-off.
        
        Args:
            response: Original response
            metadata: Email metadata including recipient name, subject, etc.
            
        Returns:
            Properly formatted email
        """
        # Extract recipient name if available
        recipient_name = None
        if metadata and 'recipient_name' in metadata:
            recipient_name = metadata['recipient_name']
        
        # Get user_id for signature
        user_id = metadata.get('user_id', 'albertlu43') if metadata else 'albertlu43'
        
        # Get display name from user's memories
        display_name = self._get_user_display_name(user_id)
        
        # Check if response already has greeting
        has_greeting = any(line.strip().startswith(('Hi', 'Hello', 'Dear', 'Hey')) for line in response.split('\n') if line.strip())
        
        # Check if response already has sign-off
        has_sign_off = any(line.strip().lower().startswith(('best', 'regards', 'sincerely', 'thanks', 'thank you', 'cheers')) 
                          for line in response.split('\n') if line.strip())
        
        # Determine formality level from metadata or response content
        formality = 0.5  # Default medium formality
        if metadata and 'formality_score' in metadata:
            formality = metadata['formality_score']
        else:
            # Estimate formality from content
            formal_indicators = ['would', 'could', 'should', 'please', 'thank you', 'sincerely', 'regards']
            casual_indicators = ['hey', 'btw', 'lol', 'haha', 'yeah', 'cool', 'awesome']
            
            formal_count = sum(1 for word in formal_indicators if word in response.lower())
            casual_count = sum(1 for word in casual_indicators if word in response.lower())
            
            if formal_count > casual_count:
                formality = 0.7
            elif casual_count > formal_count:
                formality = 0.3
        
        # Add greeting if missing
        if not has_greeting:
            if recipient_name:
                if formality > 0.6:
                    greeting = f"Dear {recipient_name},\n\n"
                else:
                    greeting = f"Hi {recipient_name},\n\n"
            else:
                if formality > 0.6:
                    greeting = "Dear Sir/Madam,\n\n"
                else:
                    greeting = "Hello,\n\n"
            
            response = greeting + response
        
        # Add sign-off if missing
        if not has_sign_off:
            if formality > 0.6:
                sign_off = f"\n\nBest regards,\n{display_name}"
            else:
                sign_off = f"\n\nCheers,\n{display_name}"
            
            response = response + sign_off
        
        return response
    
    def _get_user_display_name(self, user_id):
        """
        Get the user's display name from their memories.
        
        Args:
            user_id: User ID to retrieve name for
            
        Returns:
            str: User's display name for signatures
        """
        try:
            import os
            import json
            
            # Handle None user_id
            if user_id is None:
                return "User"
            
            # Default name if we can't find anything in memories
            default_name = user_id.split('_')[0] if '_' in user_id else user_id
            
            # Path to user memories
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            memories_dir = os.path.join(base_dir, 'data', 'memories')
            memory_file = os.path.join(memories_dir, f'user_{user_id}_memories.json')
            
            # If user-specific memory file doesn't exist, try a different format
            if not os.path.exists(memory_file):
                # Try the format used in the data/memory directory
                memory_dir = os.path.join(base_dir, 'data', 'memory')
                memory_file = os.path.join(memory_dir, f'{user_id}_memory.json')
                
                if not os.path.exists(memory_file):
                    return default_name
            
            # Read the memory file
            with open(memory_file, 'r') as f:
                memories = json.load(f)
            
            # Look for name in core memories
            if 'core_memory' in memories:
                for memory in memories['core_memory']:
                    content = memory.get('content', '').lower()
                    if 'my name is' in content or 'name:' in content:
                        # Extract name from memory
                        if 'my name is' in content:
                            name_parts = content.split('my name is', 1)[1].strip().rstrip('.').split()
                        else:
                            name_parts = content.split('name:', 1)[1].strip().rstrip('.').split()
                        
                        # Get first name
                        if name_parts:
                            first_name = name_parts[0].strip().capitalize()
                            return first_name
            
            # If no name found in memories, return default
            return default_name
            
        except Exception as e:
            print(f"Error retrieving user display name: {e}")
            # Fall back to default name for None user_id
            if user_id is None:
                return "User"
            # Fall back to default name for non-None user_id
            return user_id.split('_')[0] if '_' in user_id else user_id
    
    def _ensure_text_formatting(self, response):
        """
        Ensure proper text message formatting.
        
        Args:
            response: Original response
            
        Returns:
            Properly formatted text message
        """
        # Remove excessive formality from text messages
        lines = response.split('\n')
        
        # Remove formal greeting if present
        if lines and any(lines[0].strip().startswith(('Dear', 'Hello,', 'Greetings')) for line in lines):
            lines = lines[1:]
        
        # Remove formal sign-off if present
        if lines and any(line.strip().startswith(('Sincerely', 'Best regards', 'Regards')) for line in lines):
            lines = lines[:-2] if len(lines) > 2 else lines
        
        # Join remaining lines
        response = '\n'.join(lines).strip()
        
        # Ensure response isn't too verbose for a text
        if len(response.split()) > 50:
            # Try to condense without losing content
            response = response.replace('\n\n', '\n')
            
            # If still too long, consider truncating or summarizing
            if len(response.split()) > 70:
                sentences = response.split('.')
                if len(sentences) > 3:
                    # Keep first 3 substantial sentences
                    filtered_sentences = [s for s in sentences if len(s.split()) > 3][:3]
                    response = '.'.join(filtered_sentences) + '.'
        
        return response

# Example usage
if __name__ == "__main__":
    processor = ChannelProcessor()
    
    # Test channel detection
    text_message = "hey whats up"
    email_message = "Dear Team,\n\nI wanted to follow up on our discussion from yesterday.\n\nBest regards,\nUser"
    
    print(f"Detected channel for text: {processor.detect_channel(text_message)}")
    print(f"Detected channel for email: {processor.detect_channel(email_message)}")
