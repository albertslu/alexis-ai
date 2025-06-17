"""
AI Service for Discord Clone

Handles interactions with the OpenAI API for generating responses.
"""

from openai import OpenAI
from .config import Config

class AIService:
    """Service for handling AI interactions"""
    
    def __init__(self):
        """Initialize the AI service"""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.conversation_history = {}
    
    async def generate_response(self, channel_id, context_messages):
        """
        Generate a response using the AI model.
        
        Args:
            channel_id: ID of the channel where the conversation is happening
            context_messages: List of context messages with author_id, author_name, and content
            
        Returns:
            Generated response text or None if an error occurs
        """
        try:
            # Format messages for the API
            messages = [
                {"role": "system", "content": "You are an AI assistant that responds exactly like the user would respond in a Discord conversation. The user has a casual, concise communication style and rarely uses exclamation marks. Match their tone and writing patterns precisely. Keep responses conversational and in the style of the user. Respond as if you are the user."}
            ]
            
            # Add conversation history for context
            if channel_id in self.conversation_history:
                messages.extend(self.conversation_history[channel_id])
            
            # Add current context messages
            for msg in context_messages:
                role = "user" if msg['author_id'] != Config.DISCORD_USER_ID else "assistant"
                messages.append({
                    "role": role,
                    "content": msg['content']
                })
            
            # Generate response
            response = self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=messages,
                max_tokens=150,
                temperature=0.7,
            )
            
            response_text = response.choices[0].message.content
            
            # Update conversation history
            if channel_id not in self.conversation_history:
                self.conversation_history[channel_id] = []
            
            # Add the latest user message and response to history
            if context_messages:
                last_user_msg = context_messages[-1]
                self.conversation_history[channel_id].append({
                    "role": "user",
                    "content": last_user_msg['content']
                })
            
            self.conversation_history[channel_id].append({
                "role": "assistant",
                "content": response_text
            })
            
            # Keep history limited to last 10 exchanges
            if len(self.conversation_history[channel_id]) > 20:
                self.conversation_history[channel_id] = self.conversation_history[channel_id][-20:]
            
            return response_text
        except Exception as e:
            print(f"Error generating response: {e}")
            return None
    
    def clear_history(self, channel_id):
        """Clear conversation history for a specific channel"""
        if channel_id in self.conversation_history:
            self.conversation_history[channel_id] = []
            return True
        return False
