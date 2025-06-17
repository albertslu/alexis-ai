#!/usr/bin/env python3
"""
Migration script to associate existing data with a specific user account.
This script copies the default RAG database, Letta memories, and model configuration
to user-specific files and updates the user record in MongoDB Atlas.
"""

import os
import json
import shutil
import sys
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Get MongoDB connection details from environment
MONGO_URI = os.environ.get('MONGO_URI')
DB_NAME = os.environ.get('DB_NAME', 'ai_clone')

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RAG_DIR = os.path.join(DATA_DIR, 'rag')
MEMORIES_DIR = os.path.join(DATA_DIR, 'memories')
MEMORY_DIR = os.path.join(DATA_DIR, 'memory')  # Note: 'memory' not 'memories'
MODEL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model_config.json')
TRAINING_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'training_data.json')

# Default paths
DEFAULT_RAG_PATH = os.path.join(RAG_DIR, 'default_message_db.json')
DEFAULT_MEMORIES_PATH = os.path.join(MEMORIES_DIR, 'default_memories.json')
ALBERT_MEMORY_PATH = os.path.join(MEMORY_DIR, 'albert_memory.json')

def get_user_by_email(email):
    """Get user by email from MongoDB Atlas"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        users_collection = db['users']
        user = users_collection.find_one({'email': email})
        return user
    except Exception as e:
        print(f"Error connecting to MongoDB Atlas: {e}")
        return None

def migrate_user_data(email):
    """
    Create empty user-specific data for a new user.
    
    Args:
        email: Email of the user to create data for
    
    Returns:
        bool: True if creation was successful, False otherwise
    """
    # Get user from MongoDB Atlas
    user = get_user_by_email(email)
    if not user:
        print(f"Error: User with email {email} not found")
        return False
    
    user_id = user['_id']
    print(f"Creating data for new user: {user_id} ({user.get('name', 'Unknown')})")
    
    # Ensure directories exist
    os.makedirs(RAG_DIR, exist_ok=True)
    os.makedirs(MEMORIES_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, 'chat_histories'), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, 'user_configs'), exist_ok=True)
    
    # 1. Create empty RAG database
    success = create_empty_rag_database(user_id)
    if not success:
        return False
    
    # 2. Create empty Letta memories
    success = create_empty_letta_memories(user_id)
    if not success:
        return False
    
    # 3. Create empty chat history
    success = create_empty_chat_history(user_id)
    if not success:
        return False
    
    # 4. Create default model configuration
    success = create_default_model_config(user_id)
    if not success:
        return False
    
    # Update user record in MongoDB to indicate data is initialized
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        users_collection = db['users']
        
        # Update user record
        result = users_collection.update_one(
            {'_id': user_id},
            {'$set': {
                'data_initialized': True,
                'model_trained': False,  # New users don't have trained models
                'initialization_date': datetime.datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            print(f"Updated user record in MongoDB")
        else:
            print(f"Warning: User record not updated in MongoDB")
            
    except Exception as e:
        print(f"Error updating MongoDB: {e}")
        return False
    
    print(f"Successfully created data for new user: {user_id}")
    return True

def create_empty_rag_database(user_id):
    """Create empty RAG database for a new user"""
    user_rag_path = os.path.join(RAG_DIR, f'{user_id}_message_db.json')
    
    # Check if user database already exists
    if os.path.exists(user_rag_path):
        print(f"Warning: User RAG database already exists at {user_rag_path}")
        return True
    
    # Create empty RAG database
    print(f"Creating empty RAG database for user at {user_rag_path}")
    empty_rag = {
        "messages": []
    }
    
    try:
        with open(user_rag_path, 'w') as f:
            json.dump(empty_rag, f, indent=2)
        return True
    except Exception as e:
        print(f"Error creating empty RAG database: {e}")
        return False

def create_empty_letta_memories(user_id):
    """Create empty Letta memories for a new user"""
    user_memories_path = os.path.join(MEMORIES_DIR, f'{user_id}_memories.json')
    
    # Check if user memories already exist
    if os.path.exists(user_memories_path):
        print(f"Warning: User memories already exist at {user_memories_path}")
        return True
    
    # Create empty memories file
    print(f"Creating empty memories file for user at {user_memories_path}")
    empty_memories = {
        "memories": []
    }
    
    try:
        with open(user_memories_path, 'w') as f:
            json.dump(empty_memories, f, indent=2)
        return True
    except Exception as e:
        print(f"Error creating empty memories file: {e}")
        return False

def create_default_model_config(user_id):
    """Create default model configuration for a new user"""
    user_config_dir = os.path.join(DATA_DIR, 'user_configs')
    user_model_config_path = os.path.join(user_config_dir, f'{user_id}_model_config.json')
    
    # Ensure user configs directory exists
    os.makedirs(user_config_dir, exist_ok=True)
    
    # Check if user model config already exists
    if os.path.exists(user_model_config_path):
        print(f"Warning: User model config already exists at {user_model_config_path}")
        return True
    
    # Create default model config for new users
    print(f"Creating default model config for user at {user_model_config_path}")
    
    # Default configuration for new users - no fine-tuned model
    default_config = {
        "fine_tuned_model": None,
        "base_model": "gpt-4o-mini",  # Use base model for new users
        "rag_weight": 0.7,
        "temperature": 0.7,
        "max_tokens": 300,
        "trained": False
    }
    
    try:
        with open(user_model_config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"Created default model config for new user at {user_model_config_path}")
        return True
    except Exception as e:
        print(f"Error creating default model config: {e}")
        return False

def create_empty_chat_history(user_id):
    """Create empty chat history for a new user"""
    chat_histories_dir = os.path.join(DATA_DIR, 'chat_histories')
    user_chat_history_path = os.path.join(chat_histories_dir, f'{user_id}_chat_history.json')
    
    # Check if user chat history already exists
    if os.path.exists(user_chat_history_path):
        print(f"Warning: User chat history already exists at {user_chat_history_path}")
        return True
    
    # Create empty chat history
    print(f"Creating empty chat history for user at {user_chat_history_path}")
    empty_chat_history = {
        "conversations": []
    }
    
    try:
        with open(user_chat_history_path, 'w') as f:
            json.dump(empty_chat_history, f, indent=2)
        return True
    except Exception as e:
        print(f"Error creating empty chat history: {e}")
        return False

def count_messages(file_path):
    """Count the number of messages in a RAG database"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return len(data.get('messages', []))
    except Exception as e:
        print(f"Error counting messages: {e}")
        return 0

def count_memories(file_path):
    """Count the number of memories in a Letta memories file"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return len(data.get('memories', []))
    except Exception as e:
        print(f"Error counting memories: {e}")
        return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python migrate_user_data.py <user_email>")
        sys.exit(1)
    
    user_email = sys.argv[1]
    success = migrate_user_data(user_email)
    
    if success:
        print(f"Successfully migrated data to user {user_email}")
        sys.exit(0)
    else:
        print(f"Failed to migrate data to user {user_email}")
        sys.exit(1)
