#!/usr/bin/env python3

"""
Script to clean the chat history by removing bad email examples where the AI response is too similar to the user message.
This will help improve email response quality by preventing the RAG system from learning bad patterns.
"""

import json
import os
import re
from datetime import datetime

# Path to chat history file
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')

def is_response_too_similar(user_message, ai_response, threshold=0.7, is_email=False):
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

def clean_chat_history():
    """Clean the chat history by removing bad email examples"""
    if not os.path.exists(CHAT_HISTORY_PATH):
        print(f"Chat history file not found: {CHAT_HISTORY_PATH}")
        return
        
    # Load chat history
    with open(CHAT_HISTORY_PATH, 'r') as f:
        chat_data = json.load(f)
    
    # Find email conversations with problematic responses
    bad_email_pairs = []
    total_email_pairs = 0
    
    # Process each conversation
    for conv_idx, conversation in enumerate(chat_data.get('conversations', [])):
        messages = conversation.get('messages', [])
        
        # Scan for user-clone message pairs
        for i in range(len(messages) - 1):
            if (messages[i].get('channel') == 'email' and 
                messages[i].get('sender') == 'user' and 
                messages[i+1].get('sender') == 'clone'):
                
                total_email_pairs += 1
                user_msg = messages[i].get('text', '')
                ai_resp = messages[i+1].get('text', '')
                
                if is_response_too_similar(user_msg, ai_resp):
                    # Store conversation index, message indices
                    bad_email_pairs.append((conv_idx, i, i+1))
    
    print(f"Found {len(bad_email_pairs)} problematic email pairs out of {total_email_pairs} total email pairs")
    
    # Show examples of bad responses
    if bad_email_pairs:
        print("\nExamples of bad email responses:")
        for i, (conv_idx, user_idx, clone_idx) in enumerate(bad_email_pairs[:3]):
            messages = chat_data['conversations'][conv_idx]['messages']
            print(f"\nExample {i+1}:")
            print(f"Subject: {messages[user_idx].get('subject', 'No subject')}")
            print(f"User: {messages[user_idx].get('text', '')}")
            print(f"AI: {messages[clone_idx].get('text', '')}")
    
    # Create a backup of the chat history
    backup_path = os.path.join(DATA_DIR, f'chat_history_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(backup_path, 'w') as f:
        json.dump(chat_data, f, indent=2)
    print(f"Created backup at {backup_path}")
    
    # Mark bad examples in the chat history
    for conv_idx, user_idx, clone_idx in bad_email_pairs:
        messages = chat_data['conversations'][conv_idx]['messages']
        # Add a flag to indicate this is a bad example
        messages[clone_idx]['is_bad_example'] = True
        # Get the subject
        subject = messages[user_idx].get('subject', 'your inquiry')
        # Replace with an improved response
        messages[clone_idx]['text'] = f"Thank you for your email regarding {subject}. I appreciate you reaching out and will respond thoughtfully to your inquiry."
    
    # Save the updated chat history
    with open(CHAT_HISTORY_PATH, 'w') as f:
        json.dump(chat_data, f, indent=2)
    
    print(f"Updated {len(bad_email_pairs)} problematic email responses in chat history")
    print("These examples will now be properly filtered by the RAG system")

if __name__ == "__main__":
    clean_chat_history()
