#!/usr/bin/env python3

"""
RAG Integration for AI Clone App

This module provides functions to integrate the RAG system with the existing
AI Clone app. It enhances response generation by providing relevant examples
from the user's message history.
"""

import os
import json
from datetime import datetime, timedelta
from .rag_system import MessageRAG
import uuid

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')

# Initialize RAG system
rag_system = None

def load_repository_data_to_rag(rag_system, user_id="default"):
    """
    Load data from the unified repository into the RAG system.
    
    Args:
        rag_system: The RAG system instance
        user_id: User identifier for the repository
        
    Returns:
        int: Number of messages loaded
    """
    # Path to the repository messages file
    repo_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'repository', user_id)
    messages_file = os.path.join(repo_dir, 'messages.json')
    
    if not os.path.exists(messages_file):
        print(f"Repository messages file not found: {messages_file}")
        return 0
    
    try:
        # Load messages from repository
        with open(messages_file, 'r') as f:
            data = json.load(f)
            messages = data.get("messages", [])
        
        if not messages:
            print("No messages found in repository")
            return 0
            
        # Format messages for RAG system
        rag_messages = []
        for msg in messages:
            rag_message = {
                'text': msg.get('text', ''),
                'previous_message': msg.get('previous_message', ''),
                'sender': msg.get('sender', 'user'),
                'timestamp': msg.get('timestamp', ''),
                'thread_id': msg.get('thread_id', ''),
                'source': msg.get('source', '')
            }
            rag_messages.append(rag_message)
        
        # Add messages to RAG system
        rag_system.add_message_batch(rag_messages)
        print(f"Loaded {len(rag_messages)} messages from repository into RAG system")
        return len(rag_messages)
    except Exception as e:
        print(f"Error loading repository data: {str(e)}")
        return 0

def initialize_rag(user_id="default", min_date=None, model_version=None):
    """
    Initialize the RAG system using Pinecone for vector storage.
    
    Args:
        user_id: User identifier
        min_date: Minimum date for messages to include (ISO format string)
        model_version: Only include messages from this model version or newer
        
    Returns:
        PineconeRAGSystem: Initialized RAG system
    """
    global rag_system
    print("Initializing Pinecone RAG system...")
    
    # Default to recent messages if no date specified (last 7 days)
    if min_date is None:
        # Use 7 days ago as default
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        min_date = seven_days_ago
        print(f"No min_date specified, defaulting to 7 days ago: {min_date}")
    
    # Import PineconeRAGSystem
    from rag.pinecone_rag import PineconeRAGSystem
    
    # Create a fresh Pinecone RAG system instance
    rag_system = PineconeRAGSystem(user_id=user_id)
    
    print(f"Pinecone RAG system initialized for user {user_id}")
    return rag_system

def analyze_message_context(user_message, conversation_history=None):
    """
    Analyze the message for topic, intent, and emotional content.
    
    Args:
        user_message: The user's message to analyze
        conversation_history: Recent conversation history for context
        
    Returns:
        dict: Analysis results with topic, intent, and emotional tone
    """
    # Default analysis
    analysis = {
        'topics': [],
        'intent': 'general',
        'emotional_tone': 'neutral',
        'is_question': False,
        'is_personal': False,
        'context_keywords': []
    }
    
    # Simple topic detection based on keywords
    topic_keywords = {
        'work': ['work', 'job', 'career', 'company', 'startup', 'business', 'project'],
        'technology': ['tech', 'ai', 'code', 'programming', 'software', 'app', 'computer'],
        'personal': ['family', 'friend', 'relationship', 'feel', 'life', 'hobby', 'weekend'],
        'education': ['school', 'college', 'university', 'class', 'course', 'learn', 'study'],
        'communication': ['talk', 'chat', 'message', 'email', 'call', 'text', 'conversation']
    }
    
    # Detect topics
    message_lower = user_message.lower()
    for topic, keywords in topic_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            analysis['topics'].append(topic)
    
    # Simple intent detection
    question_markers = ['?', 'what', 'how', 'when', 'where', 'who', 'why', 'which', 'can you', 'could you']
    if any(marker in message_lower for marker in question_markers):
        analysis['intent'] = 'question'
        analysis['is_question'] = True
    elif any(cmd in message_lower for cmd in ['help', 'explain', 'tell me', 'show', 'find']):
        analysis['intent'] = 'request'
    elif any(greeting in message_lower for greeting in ['hi', 'hello', 'hey', 'morning', 'afternoon', 'evening']):
        analysis['intent'] = 'greeting'
    
    # Simple emotional tone detection
    positive_words = ['good', 'great', 'awesome', 'excellent', 'happy', 'love', 'like', 'thanks']
    negative_words = ['bad', 'terrible', 'awful', 'sad', 'hate', 'dislike', 'angry', 'upset']
    
    positive_count = sum(1 for word in positive_words if word in message_lower)
    negative_count = sum(1 for word in negative_words if word in message_lower)
    
    if positive_count > negative_count:
        analysis['emotional_tone'] = 'positive'
    elif negative_count > positive_count:
        analysis['emotional_tone'] = 'negative'
    
    # Check if message is personal
    personal_pronouns = ['i', 'me', 'my', 'mine', 'myself', 'you', 'your', 'yours', 'yourself']
    if any(pronoun in message_lower.split() for pronoun in personal_pronouns):
        analysis['is_personal'] = True
    
    # Extract context from conversation history
    if conversation_history and len(conversation_history) > 0:
        # Get last 3 messages for context
        recent_context = []
        for msg in conversation_history[-3:]:
            if msg.get('sender') == 'user' and msg.get('text') != user_message:
                recent_context.append(msg.get('text', ''))
        
        # Add context to the query
        if recent_context:
            context_str = " ".join(recent_context)
            # Limit context length
            if len(context_str) > 200:
                context_str = context_str[:200]
            # Extract important words (non-stopwords)
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for'}
            context_words = [word for word in context_str.lower().split() if word not in stopwords and len(word) > 3]
            # Count word frequency
            from collections import Counter
            word_counts = Counter(context_words)
            # Get most common words as context keywords
            analysis['context_keywords'] = [word for word, count in word_counts.most_common(5)]
    
    return analysis

def enhance_prompt_with_rag(system_prompt, user_message, conversation_history=None, user_id="default"):
    """
    Enhance the system prompt with relevant examples from the RAG system.
    
    Args:
        system_prompt: The original system prompt
        user_message: The user's message
        conversation_history: List of previous messages in the conversation
        user_id: User identifier for the RAG system
        
    Returns:
        str: Enhanced system prompt with RAG examples
    """
    # Import here to avoid circular imports
    from rag.pinecone_rag import PineconeRAGSystem
    
    # Get or initialize the RAG system for this user
    rag_system = PineconeRAGSystem(user_id=user_id)
    
    # Combine consecutive messages in conversation history for better context
    combined_history = None
    if conversation_history:
        combined_history = combine_consecutive_messages(conversation_history)
    
    # Analyze the message context with combined history
    context_analysis = analyze_message_context(user_message, combined_history or conversation_history)
    
    # Log the analysis for debugging
    print(f"Message context analysis: {context_analysis}")
    
    # Check if this is an email message
    is_email = False
    email_subject = None
    if conversation_history and len(conversation_history) > 0:
        is_email = conversation_history[-1].get('channel') == 'email'
        email_subject = conversation_history[-1].get('subject')
    
    print(f"Message type: {'Email' if is_email else 'Text'}, Subject: {email_subject if is_email else 'N/A'}")
    
    # Adjust retrieval query based on message type
    retrieval_query = user_message
    
    # Add channel information to the query to leverage our channel-based weighting
    if is_email:
        retrieval_query = f"channel:email {retrieval_query}"
    else:
        retrieval_query = f"channel:text {retrieval_query}"
    
    # Always include context from conversation history
    # Get context from recent conversation
    if conversation_history and len(conversation_history) > 2:
        # Get the last few messages for context
        recent_context = []
        for msg in conversation_history[-3:]:
            if msg.get('sender') == 'user' and msg.get('text') != user_message:
                recent_context.append(msg.get('text', ''))
        
        # Add context to the query
        if recent_context:
            context_str = " ".join(recent_context)
            # Limit context length
            if len(context_str) > 200:
                context_str = context_str[:200]
            retrieval_query = f"{retrieval_query} context:{context_str}"
    
    # Get more examples to allow for filtering
    similar_messages = rag_system.search(
        retrieval_query, 
        top_k=20  # Increased from 15 to provide more examples for pure RAG
    )
    
    # Filter out examples where the response is too similar to the user message
    # or where the example has been marked as bad
    filtered_messages = []
    for msg in similar_messages:
        user_msg = msg.get('previous_message', '')
        ai_resp = msg.get('text', '')
        is_email_example = msg.get('channel') == 'email'
        is_bad_example = msg.get('is_bad_example', False)
        
        # Skip bad examples or where the AI just repeated the user's message
        if is_bad_example:
            print(f"Skipping bad example: {ai_resp[:30]}...")
            continue
            
        # For email examples, apply stricter filtering
        if is_email_example:
            # Check for common repetitive patterns in email responses
            lower_user = user_msg.lower()
            lower_ai = ai_resp.lower()
            
            # Skip if response starts with common repetitive phrases
            common_starts = [
                "thank you for", "thanks for", "thank you so much for",
                "i appreciate", "i received your", "regarding your",
                "in response to", "in regards to", "i hope this email"
            ]
            if any(lower_ai.startswith(phrase) for phrase in common_starts):
                print(f"Skipping email with repetitive start: {ai_resp[:30]}...")
                continue
                
            # Skip if response contains any phrases from the user message
            # Get sentences from user message
            user_sentences = [s.strip().lower() for s in user_msg.split('.') if len(s.strip()) > 10]
            ai_sentences = [s.strip().lower() for s in ai_resp.split('.') if len(s.strip()) > 10]
            
            # Check if any user sentence appears in the AI response (even partially)
            for sentence in user_sentences:
                # Skip very short sentences
                if len(sentence) < 10:
                    continue
                    
                # Check for chunks of the sentence (5+ word sequences)
                words = sentence.split()
                for i in range(len(words) - 4):
                    chunk = ' '.join(words[i:i+5])
                    if len(chunk) > 15 and chunk in lower_ai:
                        print(f"Skipping email with sentence repetition: {chunk}...")
                        continue
            
            # Use the similarity function as a final check
            if is_response_too_similar(user_msg, ai_resp, threshold=0.25, is_email=True):  # Use stricter threshold
                print(f"Skipping too similar email response: {ai_resp[:30]}...")
                continue
        else:
            # For non-email messages, use standard similarity check
            if is_response_too_similar(user_msg, ai_resp):
                continue
                
        filtered_messages.append(msg)
            
    similar_messages = filtered_messages
    print(f"Filtered to {len(filtered_messages)} good examples out of {len(similar_messages)} total")
    
    # IMPROVED: Apply our enhanced filtering to reduce hallucinations
    try:
        # Import the filter function from enhanced_rag_integration
        from .enhanced_rag_integration import filter_and_validate_rag_examples
        
        # Apply additional filtering to ensure contextual relevance and reduce hallucinations
        filtered_messages = filter_and_validate_rag_examples(filtered_messages, user_message, conversation_history)
        print(f"Applied enhanced filtering: {len(filtered_messages)} examples remain after contextual validation")
        similar_messages = filtered_messages
    except Exception as e:
        print(f"Error applying enhanced filtering: {str(e)}")
    
    # If we have too few examples after filtering, add some generic good examples
    if len(similar_messages) < 3 and is_email:
        print("Adding generic good email examples due to lack of good examples")
        similar_messages.append({
            'previous_message': 'Can we schedule a meeting to discuss the project?',
            'text': 'I have availability next Tuesday and Thursday afternoons. Would either of those work for you? I\'m eager to dive into the project details.',
            'channel': 'email'
        })
        similar_messages.append({
            'previous_message': 'What do you think about the proposal I sent?',
            'text': 'The proposal looks solid overall. I particularly like the timeline section. I have a few suggestions for the budget allocation that might strengthen it further.',
            'channel': 'email'
        })
    print(f"After filtering, {len(similar_messages)} quality examples remain")
    
    # Log retrieved messages for debugging
    print(f"Retrieved {len(similar_messages)} similar messages from RAG")
    for i, msg in enumerate(similar_messages[:3]):  # Log only top 3 for brevity
        print(f"  Message {i+1}: {msg.get('previous_message', '')[:30]}... -> {msg.get('text', '')[:30]}...")
    
    # Filter and prioritize messages based on context analysis
    prioritized_messages = []
    
    # First pass: exact topic matches
    if context_analysis['topics']:
        for msg in similar_messages:
            # Check if message text contains any of the detected topics
            if any(topic.lower() in msg.get('text', '').lower() for topic in context_analysis['topics']):
                msg['relevance_score'] = 3  # High relevance
                prioritized_messages.append(msg)
    
    # Second pass: intent matches (questions with questions, etc.)
    for msg in similar_messages:
        if msg not in prioritized_messages:
            # Check for question/answer pairs if user is asking a question
            if context_analysis['is_question'] and '?' in msg.get('context', ''):
                msg['relevance_score'] = 2  # Medium relevance
                prioritized_messages.append(msg)
    
    # Third pass: emotional tone matches
    for msg in similar_messages:
        if msg not in prioritized_messages:
            # Add remaining messages with lower priority
            msg['relevance_score'] = 1  # Low relevance
            prioritized_messages.append(msg)
    
    # Sort by relevance score and limit to top 3
    prioritized_messages.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    top_messages = prioritized_messages[:3]
    
    # Log prioritized messages
    print(f"Selected {len(top_messages)} top messages for prompt enhancement")
    for i, msg in enumerate(top_messages):
        print(f"  Top {i+1} (score: {msg.get('relevance_score', 0)}): {msg.get('context', '')[:30]}... -> {msg.get('text', '')[:30]}...")

    
    # Add RAG examples to the prompt
    if top_messages:
        system_prompt += "\n\nHere are some examples of how you've responded to similar messages in the past:\n"
        
        # Add context about the current conversation
        if context_analysis['topics']:
            system_prompt += f"\nThe current conversation is about: {', '.join(context_analysis['topics'])}\n"
        
        # Add the examples
        for msg in top_messages:
            if msg['sender'] == 'user':
                system_prompt += f"\nSomeone said: {msg['context']}\nYou replied: {msg['text']}\n"
                
        # Add guidance based on intent
        if context_analysis['is_question']:
            system_prompt += "\nThe current message is a question, so provide a helpful and informative response."
        elif context_analysis['intent'] == 'greeting':
            system_prompt += "\nThe current message is a greeting, so respond in a friendly and casual way."
        
        # Add guidance for emotional tone
        if context_analysis['emotional_tone'] == 'positive':
            system_prompt += "\nThe message has a positive tone, so match that in your response."
        elif context_analysis['emotional_tone'] == 'negative':
            system_prompt += "\nThe message has a negative tone, so be empathetic in your response."

    
    return system_prompt

def combine_consecutive_messages(conversation_history):
    """
    Combine consecutive messages from the same sender.
    
    Args:
        conversation_history: List of conversation messages
        
    Returns:
        list: Combined conversation history
    """
    if not conversation_history or len(conversation_history) <= 1:
        return conversation_history
    
    combined_history = []
    current_sender = None
    current_text = []
    current_timestamp = None
    
    for msg in conversation_history:
        sender = msg.get('sender', '')
        text = msg.get('text', '')
        timestamp = msg.get('timestamp', '')
        
        # If this is a new sender or first message
        if sender != current_sender and current_sender is not None:
            # Add the combined message from previous sender
            combined_history.append({
                'sender': current_sender,
                'text': ' '.join(current_text),
                'timestamp': current_timestamp
            })
            # Reset for new sender
            current_text = [text]
            current_sender = sender
            current_timestamp = timestamp
        else:
            # Continue with same sender
            current_text.append(text)
            current_sender = sender
            if not current_timestamp:
                current_timestamp = timestamp
    
    # Add the last combined message
    if current_sender is not None:
        combined_history.append({
            'sender': current_sender,
            'text': ' '.join(current_text),
            'timestamp': current_timestamp
        })
    
    return combined_history

def is_response_too_similar(user_message, ai_response, threshold=0.8, is_email=False):
    """
    Check if the AI response is too similar to the user message.
    
    Args:
        user_message: The user's message
        ai_response: The AI's response
        threshold: Similarity threshold (0-1)
        is_email: Whether this is an email response (stricter checking)
        
    Returns:
        bool: True if the response is too similar to the user message
    """
    if not user_message or not ai_response:
        return False
        
    # Clean the messages for comparison
    clean_user_msg = user_message.lower().strip()
    clean_ai_resp = ai_response.lower().strip()
    
    # Remove email subject line if present
    if clean_ai_resp.startswith('subject:'):
        subject_end = clean_ai_resp.find('\n\n')
        if subject_end > 0:
            clean_ai_resp = clean_ai_resp[subject_end+2:].strip()
    
    # For emails, check for common repetitive patterns
    if is_email:
        # Check for common email starts that often lead to repetition
        common_starts = [
            "thank you for", "thanks for", "thank you so much for",
            "i appreciate your", "i received your", "regarding your",
            "in response to your", "i'm writing in response", "in reply to your"
        ]
        
        if any(clean_ai_resp.startswith(start) for start in common_starts):
            # If it starts with a common phrase, check if the next few words match the user message
            for start in common_starts:
                if clean_ai_resp.startswith(start):
                    rest_of_response = clean_ai_resp[len(start):].strip()
                    # Check if the next few words match the beginning of the user message
                    user_start_words = ' '.join(clean_user_msg.split()[:3])
                    resp_start_words = ' '.join(rest_of_response.split()[:3])
                    
                    if user_start_words and resp_start_words and (user_start_words in resp_start_words or resp_start_words in user_start_words):
                        return True
    
    # Check for direct repetition (chunks of text)
    # For longer messages, check for chunks
    if len(clean_user_msg) > 20:
        chunks = [clean_user_msg[:20], clean_user_msg[-20:]]
        if any(chunk in clean_ai_resp for chunk in chunks if len(chunk) > 10):
            return True
    else:
        # For short messages, check for direct inclusion
        if clean_user_msg in clean_ai_resp:
            return True
    
    # Check for sentence-level repetition
    user_sentences = [s.strip() for s in clean_user_msg.split('.') if len(s.strip()) > 10]
    ai_sentences = [s.strip() for s in clean_ai_resp.split('.') if len(s.strip()) > 10]
    
    for user_sent in user_sentences:
        for ai_sent in ai_sentences:
            # If a significant portion of a user sentence appears in an AI sentence
            if len(user_sent) > 15 and user_sent in ai_sent:
                return True
        
    # Check for high similarity using token overlap
    user_tokens = set(clean_user_msg.split())
    resp_tokens = set(clean_ai_resp.split())
    
    if len(user_tokens) == 0 or len(resp_tokens) == 0:
        return False
        
    # Calculate Jaccard similarity
    intersection = user_tokens.intersection(resp_tokens)
    union = user_tokens.union(resp_tokens)
    similarity = len(intersection) / len(union)
    
    # Use a lower threshold for emails if specified
    actual_threshold = threshold * 0.8 if is_email and threshold > 0.5 else threshold
    
    return similarity > actual_threshold

def add_interaction_to_rag(user_message, ai_response, conversation_history=None, model_version=None, user_id="default"):
    """
    Add a new interaction to the RAG system.
    
    Args:
        user_message: The user's message
        ai_response: The AI's response
        conversation_history: Recent conversation history
        model_version: Version of the model that generated the response
        user_id: User ID for the RAG system (default: "default")
    """
    # Import here to avoid circular imports
    from rag.pinecone_rag import PineconeRAGSystem
    
    # Get or initialize the RAG system for this user
    rag_system = PineconeRAGSystem(user_id=user_id)
    
    # Skip if either message is empty
    if not user_message or not ai_response:
        return
    
    # Get the channel from conversation history
    channel = None
    if conversation_history and len(conversation_history) > 0:
        channel = conversation_history[-1].get('channel', 'text')
    
    # Create message entry
    message_entry = {
        'text': ai_response,
        'previous_message': user_message,
        'sender': 'clone',
        'timestamp': datetime.now().isoformat(),
        'model_version': model_version,
        'user_id': user_id,
        'metadata': {
            'channel': channel
        }
    }
    
    # Add to Pinecone RAG system
    rag_system.add_messages_to_index([message_entry])
    
    print(f"Added interaction to Pinecone RAG: {user_message[:30]}... -> {ai_response[:30]}...")

def add_to_chat_history(user_message, ai_response, user_id="default", model_name=None):
    """
    Add a new message exchange to the chat history.
    
    Args:
        user_message: The user's message
        ai_response: The AI's response
        user_id: User identifier
        model_name: Name/version of the model that generated the response
    """
    try:
        chat_history_path = os.path.join(DATA_DIR, 'chat_history.json')
        
        # Create chat history file if it doesn't exist
        if not os.path.exists(chat_history_path):
            with open(chat_history_path, 'w') as f:
                json.dump({"conversations": []}, f)
        
        # Load existing chat history
        with open(chat_history_path, 'r') as f:
            chat_data = json.load(f)
        
        # Get or create the user's conversation
        user_conversation = None
        for conversation in chat_data.get('conversations', []):
            if conversation.get('user_id') == user_id:
                user_conversation = conversation
                break
        
        if not user_conversation:
            user_conversation = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'messages': [],
                'model_version': model_name  # Add model version to conversation
            }
            chat_data.setdefault('conversations', []).append(user_conversation)
        
        # Add user message
        user_msg_id = str(uuid.uuid4())
        user_conversation['messages'].append({
            'sender': 'user',
            'text': user_message,
            'timestamp': datetime.now().isoformat(),
            'id': user_msg_id,
            'model_version': model_name  # Add model version to message
        })
        
        # Add AI response
        ai_msg_id = str(uuid.uuid4())
        user_conversation['messages'].append({
            'sender': 'assistant',
            'text': ai_response,
            'timestamp': datetime.now().isoformat(),
            'id': ai_msg_id,
            'in_response_to': user_msg_id,
            'model_version': model_name  # Add model version to message
        })
        
        # Save updated chat history
        with open(chat_history_path, 'w') as f:
            json.dump(chat_data, f, indent=2)
            
        return True
        
    except Exception as e:
        print(f"Error adding to chat history: {str(e)}")
        return False
