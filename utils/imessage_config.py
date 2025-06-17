"""
iMessage Configuration Manager for AI Clone
Handles user-specific iMessage autoresponse configurations stored in MongoDB
"""
import os
import json
import datetime
from pymongo import MongoClient
from flask import g, current_app

# MongoDB connection - reuse the connection from auth.py
from utils.auth import db, users_collection

# Default configuration
DEFAULT_CONFIG = {
    "auto_respond": False,
    "check_interval": 5,
    "allowed_numbers": [],
    "visual_mode": False  # Whether to use visual mode for sending messages
}

def get_imessage_config_collection():
    """Get the MongoDB collection for iMessage configurations"""
    # Get or create the imessage_configs collection
    return db.get_collection('imessage_configs')

def get_user_imessage_config(user_id):
    """
    Get the iMessage configuration for a specific user
    
    Args:
        user_id: The user ID to get the configuration for
        
    Returns:
        dict: The user's iMessage configuration, or the default if not found
    """
    if not user_id:
        current_app.logger.error("No user_id provided to get_user_imessage_config")
        return DEFAULT_CONFIG.copy()
    
    collection = get_imessage_config_collection()
    
    # Try to find the user's configuration
    config = collection.find_one({"user_id": user_id})
    
    if config:
        # Remove MongoDB _id field before returning
        if "_id" in config:
            del config["_id"]
        return config
    else:
        # Create a new configuration for the user with defaults
        new_config = DEFAULT_CONFIG.copy()
        new_config["user_id"] = user_id
        new_config["created_at"] = datetime.datetime.utcnow()
        new_config["updated_at"] = datetime.datetime.utcnow()
        
        # Insert the new configuration
        collection.insert_one(new_config)
        
        # Remove MongoDB _id field before returning
        if "_id" in new_config:
            del new_config["_id"]
            
        return new_config

def update_user_imessage_config(user_id, config_updates):
    """
    Update the iMessage configuration for a specific user
    
    Args:
        user_id: The user ID to update the configuration for
        config_updates: Dictionary of configuration updates to apply
        
    Returns:
        dict: The updated configuration
    """
    if not user_id:
        current_app.logger.error("No user_id provided to update_user_imessage_config")
        return DEFAULT_CONFIG.copy()
    
    collection = get_imessage_config_collection()
    
    # Get the current configuration
    current_config = get_user_imessage_config(user_id)
    
    # Update with new values
    current_config.update(config_updates)
    current_config["updated_at"] = datetime.datetime.utcnow()
    
    # Save to MongoDB
    collection.update_one(
        {"user_id": user_id},
        {"$set": current_config},
        upsert=True
    )
    
    return current_config

def get_current_user_imessage_config():
    """
    Get the iMessage configuration for the current user (from Flask g object)
    
    Returns:
        dict: The current user's iMessage configuration
    """
    user_id = getattr(g, 'user_id', None)
    if not user_id:
        current_app.logger.warning("No user_id in Flask g object, using default iMessage config")
        return DEFAULT_CONFIG.copy()
    
    return get_user_imessage_config(user_id)

def update_current_user_imessage_config(config_updates):
    """
    Update the iMessage configuration for the current user (from Flask g object)
    
    Args:
        config_updates: Dictionary of configuration updates to apply
        
    Returns:
        dict: The updated configuration
    """
    user_id = getattr(g, 'user_id', None)
    if not user_id:
        current_app.logger.warning("No user_id in Flask g object, cannot update iMessage config")
        return config_updates
    
    return update_user_imessage_config(user_id, config_updates)
