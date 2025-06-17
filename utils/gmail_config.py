"""
Gmail Configuration Manager for AI Clone
Handles user-specific Gmail autoresponse configurations stored in MongoDB
"""
import os
import json
import datetime
import sys
import traceback
import logging
from pymongo import MongoClient
from flask import g, current_app

# Set up a logger for this module
logger = logging.getLogger('gmail_config')
logger.setLevel(logging.INFO)

# Add a handler that writes to stderr (which will be captured in the backend.log)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

logger.info("========== GMAIL_CONFIG.PY MODULE STARTED LOADING ==========")
logger.info(f"Python path: {sys.path}")
logger.info(f"Current directory: {os.getcwd()}")

# MongoDB connection - reuse the connection from auth.py
logger.info("========== IMPORTING AUTH MODULE ==========")
try:
    from utils.auth import db, users_collection
    logger.info("========== SUCCESSFULLY IMPORTED AUTH MODULE ==========")
except Exception as e:
    logger.error(f"========== ERROR IMPORTING AUTH MODULE: {str(e)} ==========")
    logger.error(traceback.format_exc())
    # Fail loudly - we need the auth module
    raise

# Default configuration
DEFAULT_CONFIG = {
    "auto_respond": False,
    "check_interval": 60,
    "max_emails_per_check": 5,
    "respond_to_all": False,
    "filter_labels": [],
    "filter_from": "",
    "filter_to": "",
    "filter_subject": ""
}

# Initialize the collection on module load
logger.info("========== INITIALIZING GMAIL_CONFIGS COLLECTION ==========")
try:
    # Get or create the gmail_configs collection
    gmail_configs = db.get_collection('gmail_configs')
    logger.info(f"Successfully initialized gmail_configs collection: {gmail_configs.name}")
    
    # Create an index on user_id for faster lookups
    gmail_configs.create_index('user_id', unique=True)
    logger.info("Created index on user_id field")
    
    # Check if the collection is accessible
    count = gmail_configs.count_documents({})
    logger.info(f"Found {count} documents in gmail_configs collection")
    
    # Create a dummy document to ensure the collection exists
    # This is important because MongoDB doesn't actually create a collection until a document is inserted
    if count == 0:
        dummy_config = DEFAULT_CONFIG.copy()
        dummy_config['user_id'] = 'dummy_user_id'
        dummy_config['is_dummy'] = True
        
        # Use update_one with upsert=True to avoid duplicate dummy documents
        result = gmail_configs.update_one(
            {'user_id': 'dummy_user_id'},
            {'$set': dummy_config},
            upsert=True
        )
        logger.info(f"Created dummy document in gmail_configs collection: {result.upserted_id or 'updated existing'}")
except Exception as e:
    logger.error(f"========== ERROR INITIALIZING GMAIL_CONFIGS COLLECTION: {str(e)} ==========")
    logger.error(traceback.format_exc())
    # Fail loudly - we need the collection to be initialized
    raise

def get_gmail_config_collection():
    """Get the MongoDB collection for Gmail configurations"""
    # Return the already initialized collection
    try:
        collection = db.get_collection('gmail_configs')
        logger.info(f"Successfully got gmail_configs collection: {collection.name}")
        
        # Only try to access current_app if we're in a Flask application context
        try:
            if hasattr(current_app, 'logger'):
                current_app.logger.info(f"Successfully got gmail_configs collection: {collection.name}")
        except RuntimeError:
            # We're outside of a Flask application context, which is fine
            logger.info("Not in Flask application context - this is normal for diagnostic scripts")
            
        return collection
    except Exception as e:
        logger.error(f"Error getting gmail_configs collection: {str(e)}")
        
        # Only try to access current_app if we're in a Flask application context
        try:
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"Error getting gmail_configs collection: {str(e)}")
        except RuntimeError:
            # We're outside of a Flask application context
            pass
            
        # Fail loudly
        raise

def get_user_gmail_config(user_id):
    """
    Get the Gmail configuration for a specific user
    
    Args:
        user_id: The user ID to get the configuration for
        
    Returns:
        dict: The user's Gmail configuration, or the default if not found
    """
    if not user_id:
        if hasattr(current_app, 'logger'):
            current_app.logger.error("No user_id provided to get_user_gmail_config")
        logger.error("No user_id provided to get_user_gmail_config")
        return DEFAULT_CONFIG.copy()
    
    # Ensure user_id is a string
    user_id = str(user_id)
    logger.info(f"Getting Gmail config for user: {user_id}")
    
    collection = get_gmail_config_collection()
    
    # Try to find the user's configuration
    # First try with the user_id field (which is what we set in our code)
    config = collection.find_one({"user_id": user_id})
    
    # If not found, try with _id field (which might be set by token_required)
    if not config:
        logger.info(f"No config found with user_id={user_id}, trying with _id")
        config = collection.find_one({"_id": user_id})
    
    if config:
        logger.info(f"Found existing config for user {user_id}: {config}")
        # Make a copy to avoid modifying the original
        config_copy = config.copy()
        # Remove MongoDB _id field before returning
        if "_id" in config_copy and config_copy["_id"] != user_id:
            del config_copy["_id"]
        # Ensure user_id is set correctly
        config_copy["user_id"] = user_id
        return config_copy
    else:
        logger.info(f"Creating new config for user {user_id}")
        # Create a new configuration for the user with defaults
        new_config = DEFAULT_CONFIG.copy()
        # Use user_id as the identifier to match token_required
        new_config["user_id"] = user_id
        new_config["created_at"] = datetime.datetime.utcnow()
        new_config["updated_at"] = datetime.datetime.utcnow()
        
        # Insert the new configuration
        try:
            result = collection.insert_one(new_config)
            logger.info(f"Inserted new config with ID: {result.inserted_id}")
        except Exception as e:
            logger.error(f"Error inserting new config: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Remove MongoDB _id field before returning
        if "_id" in new_config:
            del new_config["_id"]
            
        return new_config

def update_user_gmail_config(user_id, config_updates):
    """
    Update the Gmail configuration for a specific user
    
    Args:
        user_id: The user ID to update the configuration for
        config_updates: Dictionary of configuration updates to apply
        
    Returns:
        dict: The updated configuration
    """
    if not user_id:
        if hasattr(current_app, 'logger'):
            current_app.logger.error("No user_id provided to update_user_gmail_config")
        logger.error("No user_id provided to update_user_gmail_config")
        return DEFAULT_CONFIG.copy()
    
    # Ensure user_id is a string
    user_id = str(user_id)
    logger.info(f"Updating Gmail config for user: {user_id}")
    logger.info(f"Config updates: {config_updates}")
    if hasattr(current_app, 'logger'):
        current_app.logger.info(f"Updating Gmail config for user: {user_id}")
        current_app.logger.info(f"Config updates: {config_updates}")
    
    # Get the current configuration
    current_config = get_user_gmail_config(user_id)
    logger.info(f"Current config before update: {current_config}")
    if hasattr(current_app, 'logger'):
        current_app.logger.info(f"Current config before update: {current_config}")
    
    # Update with new values - use update() method like in iMessage config
    current_config.update(config_updates)
    # Use user_id as the identifier to match token_required
    current_config["user_id"] = user_id
    current_config["updated_at"] = datetime.datetime.utcnow()
    
    # Save to MongoDB
    collection = get_gmail_config_collection()
    logger.info(f"Using collection: {collection.name}")
    if hasattr(current_app, 'logger'):
        current_app.logger.info(f"Using collection: {collection.name}")
    
    try:
        # First try to update with user_id field
        result = collection.update_one(
            {"user_id": user_id},
            {"$set": current_config},
            upsert=True
        )
        logger.info(f"Update result: {result.modified_count} documents modified, {result.upserted_id} upserted")
        if hasattr(current_app, 'logger'):
            current_app.logger.info(f"Update result: {result.modified_count} documents modified, {result.upserted_id} upserted")
        return current_config
    except Exception as e:
        logger.error(f"Error updating Gmail config for user {user_id}: {str(e)}")
        logger.error(traceback.format_exc())
        if hasattr(current_app, 'logger'):
            current_app.logger.error(f"Error updating Gmail config for user {user_id}: {str(e)}")
        return current_config

def get_current_user_gmail_config():
    """
    Get the Gmail configuration for the current user (from Flask g object)
    
    Returns:
        dict: The current user's Gmail configuration
    """
    # Check for user_id in Flask g object
    user_id = getattr(g, 'user_id', None)
    
    # If not found, check for _id in g.user (which is set by token_required)
    if not user_id and hasattr(g, 'user') and g.user and '_id' in g.user:
        user_id = g.user['_id']
        logger.info(f"Using _id from g.user: {user_id}")
    
    if not user_id:
        logger.warning("No user_id in Flask g object, using default Gmail config")
        if hasattr(current_app, 'logger'):
            current_app.logger.warning("No user_id in Flask g object, using default Gmail config")
        return DEFAULT_CONFIG.copy()
    
    logger.info(f"Getting Gmail config for current user: {user_id}")
    return get_user_gmail_config(user_id)

def update_current_user_gmail_config(config_updates):
    """
    Update the Gmail configuration for the current user (from Flask g object)
    
    Args:
        config_updates: Dictionary of configuration updates to apply
        
    Returns:
        dict: The updated configuration
    """
    # Check for user_id in Flask g object
    user_id = getattr(g, 'user_id', None)
    
    # If not found, check for _id in g.user (which is set by token_required)
    if not user_id and hasattr(g, 'user') and g.user and '_id' in g.user:
        user_id = g.user['_id']
        logger.info(f"Using _id from g.user for update: {user_id}")
    
    if not user_id:
        logger.warning("No user_id in Flask g object, cannot update Gmail config")
        if hasattr(current_app, 'logger'):
            current_app.logger.warning("No user_id in Flask g object, cannot update Gmail config")
        return DEFAULT_CONFIG.copy()
    
    logger.info(f"Updating Gmail config for current user: {user_id}")
    return update_user_gmail_config(user_id, config_updates)
