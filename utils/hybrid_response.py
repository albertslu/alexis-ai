#!/usr/bin/env python3

"""
Hybrid Response Generation System for AI Clone

This module combines fine-tuned model responses with RAG-retrieved context
to generate more accurate and personalized responses.
"""

import os
import json
import random
import uuid
from datetime import datetime
from openai import OpenAI
import httpx
from dotenv import load_dotenv
from pathlib import Path
import logging
import concurrent.futures

# Import our RAG system
# Deprecated: MessageRAG is no longer used as we use Pinecone exclusively
# from rag.rag_system import MessageRAG
from rag.state_management import AgentState

# Import Pinecone RAG system
from rag.pinecone_rag import PineconeRAGSystem

# Import channel processor
from utils.channel_processor import ChannelProcessor

# Import feedback system for prompt enhancement
from utils.feedback_system import FeedbackSystem

# Default model configuration (simplified)
FINE_TUNED_MODEL = "gpt-4o-mini-2024-07-18"

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MODEL_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model_config.json')

# Initialize OpenAI client with custom HTTP client (no proxies)
try:
    print("Initializing OpenAI client with custom HTTP client (no proxies)")
    http_client = httpx.Client()
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        http_client=http_client
    )
    print("Successfully initialized OpenAI client")
except Exception as e:
    print(f"Error initializing OpenAI client: {str(e)}")
    import traceback
    traceback.print_exc()

class HybridResponseGenerator:
    """
    Hybrid response generation system that combines fine-tuned model with RAG.
    
    This class provides methods to generate responses using a combination of
    fine-tuned models and RAG-retrieved context.
    """
    
    def __init__(self, user_id="default", skip_rag=False):
        """
        Initialize the hybrid response generator.
        
        Args:
            user_id: Identifier for the user/agent
            skip_rag: If True, skip RAG system initialization to avoid verification delays
        """
        # Load environment variables
        load_dotenv()
        
        self.user_id = user_id
        self.conversation_history = []
        
        # Only initialize RAG system if not skipped
        if not skip_rag:
            self.rag_system = PineconeRAGSystem(user_id=user_id)
        else:
            self.rag_system = None
        
        self.channel_processor = ChannelProcessor()
        self.agent_state = AgentState()
        
        # Initialize feedback system for prompt enhancement
        self.feedback_system = FeedbackSystem(user_id=user_id)
        
        # Load model configuration
        self.model_config = self._load_model_config()
        
        # Conversation tracking
        self.current_conversation_id = None
    
    def _load_model_config(self):
        """
        Load model configuration from file.
        
        Returns:
            dict: Model configuration
        """
        if os.path.exists(MODEL_CONFIG_FILE):
            try:
                with open(MODEL_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    print(f"Loaded model config: {config}")
                    return config
            except Exception as e:
                print(f"Error loading model config: {str(e)}")
        else:
            print(f"Model config file not found at: {MODEL_CONFIG_FILE}")
        
        # Get model ID from environment variable
        model_id = os.getenv('AI_MODEL', FINE_TUNED_MODEL)
        print(f"Using model ID from environment: {model_id}")
        
        # Default configuration if file doesn't exist
        default_config = {
            "fine_tuned_model": model_id,  # Use model from environment variable
            "base_model": model_id,  # Use same model as fallback
            "rag_weight": 0.7,  # Weight given to RAG context (0.0 to 1.0)
            "temperature": 0.7,
            "max_tokens": 300
        }
        print(f"Using default model config: {default_config}")
        return default_config
    
    def start_conversation(self):
        """
        Start a new conversation.
        
        Returns:
            str: Conversation ID
        """
        self.current_conversation_id = str(uuid.uuid4())
        self.conversation_history = []
        return self.current_conversation_id
    
    def add_to_conversation_history(self, role, content):
        """
        Add a message to the conversation history.
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        self.conversation_history.append({
            "role": role,
            "text": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep conversation history to a reasonable size
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def generate_response(self, user_message, conversation_history=None, channel=None, metadata=None, model=None, rag_weight=None, temperature=None, max_tokens=None, system_prompt=None):
        """
        Generate a response using the simplified approach for message suggestions.
        
        Args:
            user_message: The user's message
            conversation_history: Recent conversation messages in the format [{'role': 'user'|'assistant', 'content': 'message'}]
            channel: Not used in simplified version (always uses 'text')
            metadata: Not used in simplified version
            model: Optional model ID to use for generation
            rag_weight: Not used in simplified version
            temperature: Optional temperature for response generation
            max_tokens: Optional maximum tokens for response generation
            system_prompt: Optional system prompt
            
        Returns:
            str: Generated response
        """
        # Always use 'text' channel for message suggestions
        channel = 'text'
        
        # Use provided system prompt or default to the optimized prompt
        if system_prompt:
            system_message = system_prompt
        else:
            system_message = "You draft message suggestions that match the user's writing style, fit the conversation context, and are ready to send without editing."
        
        # Analyze conversation state if we have history
        if conversation_history and len(conversation_history) >= 2:
            conversation_state = self._analyze_conversation_state(conversation_history)
            
            # Add conversation flow information to the system prompt
            flow_type = conversation_state.get('flow_type', 'new_topic')
            contains_question = conversation_state.get('contains_question', False)
            question_type = conversation_state.get('question_type')
            is_correction = conversation_state.get('is_correction', False)
            
            # Enhance system prompt with conversation flow information
            flow_guidance = f"\nConversation flow: {flow_type}"
            
            if contains_question:
                flow_guidance += f", contains a {question_type} question"
            
            if is_correction:
                flow_guidance += ", user is correcting previous information"
                
            system_message += flow_guidance
        
        # Generate response using fine-tuned model
        response = self._generate_with_fine_tuned_model(
            user_message,
            system_message,
            conversation_history=conversation_history,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response
    
    def _analyze_conversation_state(self, conversation_history=None):
        """
        Analyze the current conversation state to determine the conversation flow pattern.
        
        Args:
            conversation_history: Optional conversation history to analyze
            
        Returns:
            dict: Conversation state information including flow type, topic continuity, etc.
        """
        # Use provided conversation history or instance history
        if conversation_history is None:
            conversation_history = self.conversation_history
            
        # Default state
        state = {
            "flow_type": "new_topic",  # new_topic, continuation, follow_up, greeting
            "topic_continuity": 0.0,   # 0.0-1.0 measure of topic continuity
            "contains_question": False, # Whether the message contains a question
            "question_type": None,     # yes_no, factual, opinion, etc.
            "is_correction": False    # Whether this is correcting previous response
        }
        
        # Not enough history to determine state
        if len(conversation_history) < 2:
            return state
        
        # Get the last few messages (more context for better analysis)
        recent_messages = conversation_history[-6:] if len(conversation_history) >= 6 else conversation_history
        
        # Check for follow-up questions (very short questions after a response)
        if len(recent_messages) >= 2:
            last_user_msg = None
            last_assistant_msg = None
            prev_user_msg = None
            
            # Find the last user message, last assistant message, and previous user message
            for msg in reversed(conversation_history):
                if msg['role'] == 'user' and last_user_msg is None:
                    last_user_msg = msg['content']
                elif msg['role'] == 'assistant' and last_assistant_msg is None:
                    last_assistant_msg = msg['content']
                elif msg['role'] == 'user' and prev_user_msg is None and last_user_msg is not None:
                    prev_user_msg = msg['content']
                    break
            
            # If we have all three messages, analyze the flow
            if last_user_msg and last_assistant_msg and prev_user_msg:
                # Check for follow-up questions (short user message after assistant response)
                if len(last_user_msg.split()) <= 10 and '?' in last_user_msg:
                    state['flow_type'] = 'follow_up'
                    state['topic_continuity'] = 0.8  # High continuity for follow-ups
                
                # Check for topic continuity between user messages
                user_msg_words = set(last_user_msg.lower().split())
                prev_msg_words = set(prev_user_msg.lower().split())
                
                # Calculate word overlap as a simple measure of topic continuity
                if user_msg_words and prev_msg_words:
                    overlap = len(user_msg_words.intersection(prev_msg_words))
                    total = len(user_msg_words.union(prev_msg_words))
                    if total > 0:
                        continuity = overlap / total
                        state['topic_continuity'] = min(continuity * 2, 1.0)  # Scale up but cap at 1.0
                        
                        # If significant continuity, mark as continuation
                        if continuity > 0.3:
                            state['flow_type'] = 'continuation'
                
                # Check for corrections (user correcting the assistant)
                correction_phrases = ['no, ', 'actually, ', 'i meant ', 'not what i', 'incorrect', 'that\'s not']
                if any(phrase in last_user_msg.lower() for phrase in correction_phrases):
                    state['is_correction'] = True
                    state['flow_type'] = 'correction'
            
            # Check for greeting patterns
            greeting_words = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'sup', 'yo']
            if last_user_msg and any(greeting in last_user_msg.lower() for greeting in greeting_words):
                if len(last_user_msg.split()) <= 3:  # Short greeting
                    state['flow_type'] = 'greeting'
        
        # Detect questions in the last user message
        last_user_msg = None
        for msg in reversed(conversation_history):
            if msg['role'] == 'user':
                last_user_msg = msg['content']
                break
                
        if last_user_msg:
            # Simple question detection
            if '?' in last_user_msg:
                state['contains_question'] = True
                
                # Determine question type
                if any(word in last_user_msg.lower() for word in ['is', 'are', 'was', 'were', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should']):
                    if last_user_msg.lower().startswith(('is', 'are', 'was', 'were', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should')):
                        state['question_type'] = 'yes_no'
                elif any(word in last_user_msg.lower() for word in ['what', 'who', 'where', 'when', 'why', 'how']):
                    state['question_type'] = 'factual'
                else:
                    state['question_type'] = 'open_ended'
        
        return state
    
    def _prepare_system_message(self, channel=None):
        """
        Prepare base system message with channel awareness.
        
        Note: This method is deprecated and will be removed in a future version.
        System prompts should now be provided from app.py instead.
        
        Args:
            channel: Communication channel
            
        Returns:
            str: System message
        """
        # Return a simple default message - this should rarely be used now
        # that we're passing system_prompt from app.py
        return "You draft message suggestions that match the user's writing style, fit the conversation context, and are ready to send without editing."
    
    def _generate_with_fine_tuned_model(self, user_message, system_message, conversation_history=None, model=None, temperature=None, max_tokens=None):
        """
        Generate a message suggestion using the fine-tuned model.
        
        Args:
            user_message: User message
            system_message: System message (including any RAG enhancements)
            conversation_history: Recent conversation messages
            model: Optional model ID to use for generation
            temperature: Optional temperature for response generation
            max_tokens: Optional maximum tokens for response generation
            
        Returns:
            str: Generated message suggestion
        """
        try:
            # Get model ID from MongoDB if not provided
            if not model:
                # Import get_current_model from model_config
                try:
                    from model_config import get_current_model
                    model = get_current_model()
                except Exception as e:
                    # Use default model if MongoDB retrieval fails
                    model = FINE_TUNED_MODEL
            
            # Set default values for message suggestions
            temperature_value = 0.7 if temperature is None else temperature
            max_tokens_value = 150 if max_tokens is None else max_tokens
            
            # Create messages for the API call with the system message
            messages = [
                {"role": "system", "content": system_message}
            ]
            
            # Add conversation history if available
            if conversation_history:
                for msg in conversation_history:
                    messages.append({
                        "role": msg['role'], 
                        "content": msg['content']
                    })
            
            # Always add the current user message
            messages.append({"role": "user", "content": user_message})
            
            # Generate response with OpenAI API
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature_value,
                max_tokens=max_tokens_value
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # Log error and re-raise
            print(f"Error generating message suggestion: {str(e)}")
            raise e
    
    def generate_response_suggestions(self, user_message, conversation_history=None, channel=None, metadata=None, model=None, count=3, temperature_range=(0.5, 0.9), max_tokens=None, system_prompt=None):
        """
        Generate multiple message suggestions with varying temperatures for diversity using parallel API calls.
        
        Args:
            user_message: The user's message
            conversation_history: Recent conversation messages in the format [{"role": "user"|"assistant", "content": "message"}]
            channel: Not used in simplified version (always uses 'text')
            metadata: Not used in simplified version
            model: Optional model ID to use for generation
            count: Number of message suggestions to generate (default: 3)
            temperature_range: Tuple of (min_temp, max_temp) to use for generating diverse suggestions
            max_tokens: Optional maximum tokens for suggestion generation
            system_prompt: Optional system prompt
            
        Returns:
            list: List of generated message suggestions
        """
        # Get the model ID once here in the main thread where Flask context is available
        if not model:
            try:
                from model_config import get_current_model
                model = get_current_model()
                print(f"Using model ID from MongoDB for user {self.user_id}: {model}")
            except Exception as e:
                print(f"Error getting model from MongoDB: {e}")
                # Use default model if MongoDB retrieval fails
                model = FINE_TUNED_MODEL
                print(f"Falling back to default model: {model}")
        
        # Calculate temperatures for diversity
        temp_min, temp_max = temperature_range
        if count == 1:
            temperatures = [temp_min]
        elif count == 2:
            temperatures = [temp_min, temp_max]
        else:
            # For 3+ suggestions, distribute temperatures evenly
            temp_step = (temp_max - temp_min) / (count - 1)
            temperatures = [temp_min + i * temp_step for i in range(count)]
        
        # Create a function to generate a single suggestion
        def generate_single_suggestion(temp):
            try:
                return self.generate_response(
                    user_message,
                    conversation_history,
                    model=model,  # Pass the model explicitly to avoid Flask context issues
                    temperature=temp,
                    max_tokens=max_tokens,
                    system_prompt=system_prompt
                )
            except Exception as e:
                print(f"Error generating suggestion with temperature {temp}: {str(e)}")
                return None
        
        # Execute API calls in parallel
        suggestions = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            # Submit all tasks
            future_to_temp = {executor.submit(generate_single_suggestion, temp): temp for temp in temperatures}
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_temp):
                temp = future_to_temp[future]
                try:
                    result = future.result()
                    if result:
                        suggestions.append(result)
                except Exception as e:
                    print(f"Error in future for temperature {temp}: {str(e)}")
        
        # Return suggestions without Jaccard filtering - rely on temperature diversity and fine-tuned model
        # The fine-tuned model already avoids repetitive responses, and temperature diversity ensures variety
        return suggestions[:count]
        
# Example usage
if __name__ == "__main__":
    # Initialize hybrid response generator
    generator = HybridResponseGenerator()
    
    # Start a conversation
    conversation_id = generator.start_conversation()
    
    # Generate a response
    user_message = "Hey, how's your startup going?"
    response = generator.generate_response(user_message, conversation_history=None, channel="text")
    
    print(f"User: {user_message}")
    print(f"AI: {response}")
    
    # Continue the conversation
    user_message = "What technologies are you using?"
    response = generator.generate_response(user_message, conversation_history=None, channel="text")
    
    print(f"User: {user_message}")
    print(f"AI: {response}")
