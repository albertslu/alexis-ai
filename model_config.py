# Configuration file for AI models used in the application

# Default model to use if no fine-tuned model is available
DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"

# This will be dynamically set by the training system
# Don't hardcode specific user-model IDs here
FINE_TUNED_MODEL = DEFAULT_MODEL

# History of fine-tuned models (newest first)
# This is kept for documentation purposes
MODEL_HISTORY = [
    {
        "id": "ft:gpt-4o-mini-2024-07-18:al43595::BCX8dk0Q",
        "created": "2025-03-18",
        "description": "Latest model trained on 30 days of messages and emails with enhanced RAG integration"
    },
    {
        "id": "ft:gpt-4o-mini-2024-07-18:al43595::B8W6OPMm",
        "created": "2025-03-07",
        "description": "Improved model with consistent system prompts, simple greeting examples, and work history examples"
    },
    {
        "id": "ft:gpt-4o-mini-2024-07-18:al43595::B8VEyhUd",
        "created": "2025-03-07",
        "description": "Improved model with simplified system prompt and better training examples"
    },
    {
        "id": "ft:gpt-4o-2024-08-06:al43595:clone:B7VxPMl6",
        "created": "2025-03-04",
        "description": "Initial fine-tuned clone model"
    }
]

def get_current_model():
    """
    Returns the current model ID to use.
    This should be the user's trained fine-tuned model.
    If no trained model is available, returns None with appropriate error logging.
    """
    import os
    import json
    import logging
    from pathlib import Path
    from pymongo import MongoClient
    
    # Try to get user ID from Flask context first if this is being called from Flask
    try:
        from flask import g
        if hasattr(g, 'user_id') and g.user_id:
            user_id = g.user_id
        else:
            # If we're in Flask but no user_id in g, this is an error
            error_msg = "No user_id available in Flask context. Cannot determine which model to use."
            print(error_msg)
            logging.error(error_msg)
            return None
    except ImportError:
        # If we're not in Flask, check environment
        user_id = os.environ.get('USER_ID')
        if not user_id:
            error_msg = "No USER_ID available in environment. Cannot determine which model to use."
            print(error_msg)
            logging.error(error_msg)
            return None
    
    # Connect to MongoDB to get user model information
    # Import the MongoDB connection setup from auth module
    try:
        # Import MongoDB connection from auth module
        from utils.auth import db
        
        # Get user from MongoDB
        user = db.users.find_one({"user_id": user_id})
        if user and user.get('model_trained', False) and user.get('fine_tuned_model_id'):
            # User has a trained model according to MongoDB
            print(f"Using model ID from MongoDB for user {user_id}: {user.get('fine_tuned_model_id')}")
            return user.get('fine_tuned_model_id')
        else:
            # No trained model found in MongoDB
            error_msg = f"ERROR: User {user_id} does not have a trained model according to MongoDB. Cannot proceed."
            print(error_msg)
            logging.error(error_msg)
            return None
    except Exception as e:
        # If MongoDB connection fails, this is a critical error - no fallbacks
        error_msg = f"ERROR: Failed to check MongoDB for model info: {e}. Cannot proceed without database connection."
        print(error_msg)
        logging.error(error_msg)
        return None
