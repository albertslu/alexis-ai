import os
import json
from flask import Blueprint, request, jsonify, g, current_app
from .data_integration import DataIntegration
from .simple_repository import SimpleDataRepository

# Create a Blueprint for RAG-related routes
rag_bp = Blueprint('rag', __name__)

# Get the current user ID from Flask's g object
def get_user_id():
    # Get user_id from g object if available, otherwise use default
    user_id = g.get('user_id', 'default')
    return user_id

@rag_bp.route('/integrate/imessage-test', methods=['POST'])
def integrate_imessage_test():
    """Test endpoint for iMessage integration (doesn't access actual database)"""
    try:
        user_id = get_user_id()
        current_app.logger.info(f"Testing iMessage integration for user: {user_id}")
        
        # Get days parameter from request, default to 365 days
        data = request.json or {}
        days = data.get('days', 365)
        
        return jsonify({
            "success": True,
            "message": f"This is a test endpoint. In production, this would process iMessages from the last {days} days.",
            "message_count": 0,
            "is_test": True
        })
    except Exception as e:
        current_app.logger.error(f"Error in iMessage test endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Error in test endpoint: " + str(e)
        }), 500

@rag_bp.route('/integrate/imessage', methods=['POST'])
def integrate_imessage():
    """API endpoint to integrate iMessage data"""
    try:
        user_id = get_user_id()
        current_app.logger.info(f"Integrating iMessage data for user: {user_id}")
        
        # Get days parameter from request, default to 365 days (about 1 year)
        data = request.json or {}
        days = data.get('days', 365)  # Default to 1 year of messages
        
        # Check if we're on macOS (iMessage integration only works on macOS)
        import platform
        if platform.system() != 'Darwin':
            current_app.logger.error("iMessage integration failed: Not running on macOS")
            return jsonify({
                "success": False,
                "message": "iMessage integration is only available on macOS devices."
            }), 400
            
        # Check if Messages database exists
        messages_db_path = os.path.expanduser("~/Library/Messages/chat.db")
        if not os.path.exists(messages_db_path):
            current_app.logger.error(f"iMessage integration failed: Messages database not found at {messages_db_path}")
            return jsonify({
                "success": False,
                "message": "iMessage database not found. To fix this issue, please follow these steps:\n\n1. Open System Settings/Preferences\n2. Go to Privacy & Security > Privacy > Full Disk Access\n3. Click the '+' button and add Terminal (or your preferred terminal app)\n4. Restart the app after granting permission"
            }), 400
        
        try:
            # Process iMessage data with specified days
            integrator = DataIntegration(user_id=user_id)
            message_count = integrator.process_imessage_data(days=days)
            
            current_app.logger.info(f"Successfully processed {message_count} iMessages for user {user_id}")
            return jsonify({
                "success": True,
                "message": f"Successfully processed {message_count} messages from iMessage (last {days} days)",
                "message_count": message_count
            })
        except Exception as e:
            current_app.logger.error(f"Error processing iMessage data: {str(e)}")
            return jsonify({
                "success": False,
                "message": "Failed to access iMessage database. Please grant Full Disk Access to AI Clone:\n\n1. Open System Settings/Preferences\n2. Go to Privacy & Security > Privacy > Full Disk Access\n3. Click the '+' button and add AI Clone\n4. Restart the app after granting permission"
            }), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in iMessage integration: {str(e)}")
        return jsonify({
            "success": False,
            "message": "An unexpected error occurred. Please try again later."
        }), 500

@rag_bp.route('/integrate/linkedin', methods=['POST'])
def integrate_linkedin():
    """API endpoint to integrate LinkedIn data"""
    try:
        data = request.json
        if not data or 'linkedin_data' not in data:
            return jsonify({
                "success": False,
                "error": "LinkedIn data is required"
            }), 400
        
        linkedin_data = data['linkedin_data']
        user_id = get_user_id()
        integrator = DataIntegration(user_id=user_id)
        
        # Process LinkedIn data
        success = integrator.process_linkedin_data(linkedin_data)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Successfully processed LinkedIn data"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to process LinkedIn data"
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/repository/status', methods=['GET'])
def repository_status():
    """API endpoint to get the status of the user's data repository"""
    try:
        user_id = get_user_id()
        repository = SimpleDataRepository(user_id=user_id)
        
        # Get repository metadata
        metadata = repository.get_metadata()
        sources = repository.get_sources()
        message_count = repository.get_message_count()
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "sources": sources,
            "message_count": message_count,
            "last_updated": metadata.get("last_updated"),
            "created_at": metadata.get("created_at")
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/search', methods=['POST'])
def search_repository():
    """API endpoint to search the repository for similar messages"""
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({
                "success": False,
                "error": "Query is required"
            }), 400
        
        query = data['query']
        top_k = data.get('top_k', 5)
        source_filter = data.get('source_filter', None)
        
        user_id = get_user_id()
        repository = SimpleDataRepository(user_id=user_id)
        
        # Search for similar messages
        results = repository.retrieve_similar(query, top_k=top_k, source_filter=source_filter)
        
        # Format results for API response
        formatted_results = []
        for result in results:
            formatted_results.append({
                "text": result.get("text"),
                "source": result.get("source"),
                "similarity": result.get("similarity"),
                "context": result.get("context"),
                "previous_message": result.get("previous_message"),
                "timestamp": result.get("timestamp")
            })
        
        return jsonify({
            "success": True,
            "query": query,
            "results": formatted_results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
