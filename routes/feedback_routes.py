#!/usr/bin/env python3

"""
Feedback Routes for AI Clone

This module provides API routes for the feedback system, allowing users
to submit and retrieve feedback on AI clone responses.
"""

from flask import Blueprint, request, jsonify, g
import uuid
import json
import os
from datetime import datetime, timedelta

# Import feedback system
from utils.feedback_system import FeedbackSystem
# Import authentication decorator
from utils.auth import token_required

# Create blueprint
feedback_bp = Blueprint('feedback', __name__)

# Initialize feedback system
# We'll initialize it with the user_id for each request

@feedback_bp.route('/feedback/conversations', methods=['GET'])
@token_required
def get_conversations():
    """
    Get conversations with feedback information.
    
    Query parameters:
    - days_ago: Filter conversations from the last X days (default: all)
    - model_version: Filter for messages from a specific model version or newer (default: latest)
    - hide_reviewed: If 'true', hide messages that have already received feedback (default: true)
    - channel: Filter for messages from a specific channel (email, text, etc.) (default: all)
    """
    # Get user_id from request context if available
    from flask import g
    user_id = g.user_id if hasattr(g, 'user_id') else "default"
    print(f"Feedback route: Using user_id: {user_id}")
    
    # If user_id is default, we need to ensure they have access to their own data only
    if user_id == "default":
        print(f"Warning: Using default user_id. This should only happen in development.")
    
    try:
        # Get date filter from query parameters
        days_ago = request.args.get('days_ago', default=None, type=int)
        
        # Get model version filter from query parameters
        model_version = request.args.get('model_version', default="v1.4")
        
        # Get hide_reviewed parameter
        hide_reviewed_param = request.args.get('hide_reviewed', default='true')
        hide_reviewed = hide_reviewed_param.lower() == 'true'
        
        # Get channel filter from query parameters
        channel = request.args.get('channel', default=None)
        
        # Create user-specific feedback system instance
        user_feedback_system = FeedbackSystem(user_id=user_id)
        
        # Get conversations with feedback
        conversations_data = user_feedback_system.get_conversations_with_feedback(
            days_ago=days_ago,
            model_version=model_version,
            hide_reviewed=hide_reviewed,
            channel=channel
        )
        
        # Get feedback stats using the same user-specific feedback system
        stats = user_feedback_system.get_feedback_stats(days_ago=days_ago)
        
        return jsonify({
            "messages": conversations_data.get("messages", []),
            "stats": stats,
            "success": True,
            "filtered_by_model": model_version,
            "hide_reviewed": hide_reviewed,
            "filtered_by_channel": channel
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

@feedback_bp.route('/feedback/submit', methods=['POST'])
@token_required
def submit_feedback():
    """
    Submit feedback on a clone response.
    """
    try:
        # Get request data
        data = request.json
        
        # Validate required fields
        if 'message_id' not in data or 'feedback_type' not in data:
            return jsonify({
                "error": "Missing required fields: message_id, feedback_type",
                "success": False
            }), 400
        
        # Extract fields
        message_id = data.get('message_id')
        feedback_type = data.get('feedback_type')
        corrected_text = data.get('corrected_text')
        
        # Get user_id from request context if available
        from flask import g
        user_id = g.user_id if hasattr(g, 'user_id') else "default"
        print(f"Submit feedback route: Using user_id: {user_id}")
        
        # Get user-specific chat history path
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        chat_history_dir = os.path.join(data_dir, 'chat_history')
        chat_history_path = os.path.join(chat_history_dir, f'{user_id}_chat_history.json')
        
        # If user-specific chat history doesn't exist, fall back to default
        if not os.path.exists(chat_history_path):
            print(f"User-specific chat history not found for {user_id}, checking default path")
            default_chat_history_path = os.path.join(data_dir, 'chat_history.json')
            if os.path.exists(default_chat_history_path):
                chat_history_path = default_chat_history_path
                print(f"Using default chat history path: {default_chat_history_path}")
            else:
                print(f"No chat history found for user: {user_id}")
                return jsonify({
                    "error": f"No chat history found for user: {user_id}",
                    "success": False
                }), 404
        
        original_message = None
        channel = None
        metadata = None
        conversation_id = None
        
        if os.path.exists(chat_history_path):
            try:
                with open(chat_history_path, 'r') as f:
                    chat_history = json.load(f)
                    
                # Find the message
                for conversation in chat_history.get("conversations", []):
                    for message in conversation.get("messages", []):
                        if message.get("id") == message_id:
                            original_message = message.get("text")
                            channel = message.get("channel", "text")
                            conversation_id = conversation.get("id")
                            metadata = {
                                "sender": message.get("sender"),
                                "timestamp": message.get("timestamp"),
                                "conversation_id": conversation_id
                            }
                            break
                    
                    if original_message:
                        break
            except Exception as e:
                print(f"Error loading chat history: {str(e)}")
        
        # If original message not found, return error
        if not original_message:
            return jsonify({
                "error": f"Message with ID {message_id} not found",
                "success": False
            }), 404
        
        # Get user_id from request context if available
        from flask import g
        user_id = g.user_id if hasattr(g, 'user_id') else "default"
        print(f"Submit feedback route: Using user_id: {user_id}")
        
        # Create user-specific feedback system instance
        user_feedback_system = FeedbackSystem(user_id=user_id)
        
        # Record feedback for the specific user
        feedback_id = user_feedback_system.record_feedback(
            message_id=message_id,
            original_message=original_message,
            corrected_message=corrected_text,
            feedback_type=feedback_type,
            channel=channel,
            metadata=metadata
        )
        
        # If this is a quick approval from the chat interface, return a simple success
        if feedback_type == "approved" and request.headers.get('X-Source') == 'chat':
            return jsonify({
                "success": True,
                "message": "Response approved successfully"
            })
        
        return jsonify({
            "feedback_id": feedback_id,
            "success": True
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

@feedback_bp.route('/feedback/stats', methods=['GET'])
@token_required
def get_feedback_stats():
    """
    Get feedback statistics.
    
    Query parameters:
    - days_ago: Filter stats from the last X days (default: all)
    """
    try:
        # Get date filter from query parameters
        days_ago = request.args.get('days_ago', default=None, type=int)
        
        # Get user_id from request context if available
        from flask import g
        user_id = g.user_id if hasattr(g, 'user_id') else "default"
        print(f"Feedback stats route: Using user_id: {user_id}")
        
        # Create user-specific feedback system instance
        user_feedback_system = FeedbackSystem(user_id=user_id)
        
        # Get feedback stats using the user-specific feedback system
        stats = user_feedback_system.get_feedback_stats(days_ago=days_ago)
        
        return jsonify({
            "stats": stats,
            "success": True
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

@feedback_bp.route('/feedback/records', methods=['GET'])
@token_required
def get_feedback_records():
    """
    Get feedback records with optional filtering.
    """
    try:
        # Get query parameters
        feedback_type = request.args.get('type')
        channel = request.args.get('channel')
        limit = int(request.args.get('limit', 100))
        
        # Get user_id from request context if available
        from flask import g
        user_id = g.user_id if hasattr(g, 'user_id') else "default"
        print(f"Feedback records route: Using user_id: {user_id}")
        
        # Create user-specific feedback system instance
        user_feedback_system = FeedbackSystem(user_id=user_id)
        
        # Get feedback records for the specific user
        records = user_feedback_system.get_feedback_records(
            feedback_type=feedback_type,
            channel=channel,
            limit=limit
        )
        
        return jsonify({
            "records": records,
            "success": True
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

@feedback_bp.route('/feedback/learning-examples', methods=['GET'])
@token_required
def get_learning_examples():
    """
    Get learning examples from corrected responses.
    
    Query parameters:
    - days_ago: Filter examples from the last X days (default: all)
    - limit: Maximum number of examples to return (default: 100)
    """
    try:
        # Get parameters from query
        days_ago = request.args.get('days_ago', default=None, type=int)
        limit = request.args.get('limit', default=100, type=int)
        
        # Get user_id from request context if available
        from flask import g
        user_id = g.user_id if hasattr(g, 'user_id') else "default"
        print(f"Learning examples route: Using user_id: {user_id}")
        
        # Get learning examples for the specific user
        user_feedback_system = FeedbackSystem(user_id=user_id)
        
        # Handle the case where get_learning_examples method might not exist in older versions
        if not hasattr(user_feedback_system, 'get_learning_examples'):
            return jsonify({
                "examples": [],
                "count": 0,
                "success": True,
                "message": "No learning examples available"
            })
            
        examples = user_feedback_system.get_learning_examples(days_ago=days_ago, limit=limit)
        
        return jsonify({
            "examples": examples,
            "count": len(examples),
            "success": True
        })
    except Exception as e:
        print(f"Error in get_learning_examples: {str(e)}")
        # Return an empty list with success=true instead of an error
        # This prevents the frontend from showing an error message
        return jsonify({
            "examples": [],
            "count": 0,
            "success": True,
            "message": "Error retrieving learning examples: " + str(e)
        })
