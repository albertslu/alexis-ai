#!/usr/bin/env python

import sys
import json
import os
import traceback
from datetime import datetime
from openai import OpenAI
import httpx

# Get message from command line arguments
message = sys.argv[1]
message_count = int(sys.argv[2])

try:
    # Set up OpenAI client with custom HTTP client (no proxies)
    http_client = httpx.Client()
    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        http_client=http_client
    )
    
    # Define paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    TRAINING_DATA_PATH = os.path.join(DATA_DIR, 'training_data.json')
    USER_PROFILE_PATH = os.path.join(DATA_DIR, 'user_profile.json')
    
    # Create directories if they don't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Initialize or load training data
    if os.path.exists(TRAINING_DATA_PATH):
        with open(TRAINING_DATA_PATH, 'r') as f:
            training_data = json.load(f)
    else:
        training_data = {
            "conversations": [],
            "answers": {},
            "trained": False,
            "last_updated": None
        }
    
    # Initialize or load user profile
    if os.path.exists(USER_PROFILE_PATH):
        with open(USER_PROFILE_PATH, 'r') as f:
            user_profile = json.load(f)
    else:
        user_profile = {
            "style_characteristics": {},
            "emoji_usage": {},
            "common_phrases": []
        }
        with open(USER_PROFILE_PATH, 'w') as f:
            json.dump(user_profile, f, indent=2)
    
    # Save the user message to training data
    conversations = training_data.get("conversations", [])
    if not conversations:
        conversations.append({"messages": []})
    
    # Add user message
    conversations[-1]["messages"].append({
        "sender": "user",
        "text": message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Generate response based on message count
    if message_count < 3:
        response_text = "Hi there! I'm your AI training assistant. Let's have a conversation so I can learn your communication style. Just chat with me naturally about anything you'd like!"
    elif message_count < 6:
        response_text = "Thanks for chatting with me! I'm starting to get a sense of your communication style. Keep going - the more we chat, the better I'll understand how you communicate."
    elif message_count < 9:
        response_text = "Great conversation! I'm learning more about your style with each message. We're getting close to having enough data for a basic analysis."
    else:
        response_text = "I think I have a good understanding of your communication style now. Would you like me to analyze it and show you what I've learned?"
    
    # Add bot response to training data
    conversations[-1]["messages"].append({
        "sender": "bot",
        "text": response_text,
        "timestamp": datetime.now().isoformat()
    })
    
    # Save updated training data
    training_data["conversations"] = conversations
    with open(TRAINING_DATA_PATH, 'w') as f:
        json.dump(training_data, f, indent=2)
    
    # Return the response as JSON
    result = {"response": response_text}
    print(json.dumps(result))
    
except Exception as e:
    error_message = f"Error: {str(e)}\n{traceback.format_exc()}"
    print(json.dumps({"error": error_message}))
    sys.exit(1)
