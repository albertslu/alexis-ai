#!/usr/bin/env python3

"""
Personal Information API Routes

This module provides API routes to view and manage personal information used by the RAG system.
Now uses the user's memories instead of the legacy personal_info.json file.
"""

import os
import json
from flask import Blueprint, jsonify, request, g
from datetime import datetime

# Create Blueprint
personal_info_bp = Blueprint('personal_info', __name__)

def get_user_memories(user_id="default"):
    """
    Get user memories from their memory file.
    
    Args:
        user_id: User identifier
        
    Returns:
        dict: User memories data
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Try different memory file formats
    memory_paths = [
        os.path.join(base_dir, 'data', 'memories', f'user_{user_id}_memories.json'),
        os.path.join(base_dir, 'data', 'memory', f'{user_id}_memory.json')
    ]
    
    for memory_path in memory_paths:
        if os.path.exists(memory_path):
            try:
                with open(memory_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading memory file {memory_path}: {e}")
    
    # Return empty memories if no file found
    return {"core_memory": [], "episodic_memory": []}

@personal_info_bp.route('/api/personal-info', methods=['GET'])
def get_personal_info():
    """Get all personal information stored in the system"""
    try:
        # Get user_id from request or context
        user_id = request.args.get('user_id', g.get('user_id', 'default'))
        
        # Get the user's memories
        memories = get_user_memories(user_id)
        
        # Format memories as personal info
        personal_info = {
            "name": "User",  # Default name
            "personal_facts": []
        }
        
        # Extract name from core memories if available
        if "core_memory" in memories:
            for memory in memories["core_memory"]:
                content = memory.get("content", "").lower()
                if "my name is" in content:
                    name_parts = content.split("my name is", 1)[1].strip().rstrip(".").split()
                    if name_parts:
                        personal_info["name"] = name_parts[0].capitalize()
                        break
        
        # Format core memories as personal facts
        if "core_memory" in memories:
            personal_info["personal_facts"] = [
                {
                    "category": "Personal Information",
                    "facts": [memory.get("content") for memory in memories["core_memory"] if "content" in memory]
                }
            ]
        
        return jsonify({
            'success': True,
            'personal_info': personal_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@personal_info_bp.route('/api/personal-info/categories', methods=['GET'])
def get_personal_info_categories():
    """Get available categories of personal information"""
    try:
        # Get user_id from request or context
        user_id = request.args.get('user_id', g.get('user_id', 'default'))
        
        # Get the user's memories
        memories = get_user_memories(user_id)
        
        # For now, we just have one category
        categories = ["Personal Information"]
        
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@personal_info_bp.route('/api/personal-info/facts', methods=['POST'])
def add_personal_fact():
    """Add a new personal fact"""
    try:
        # Get request data
        data = request.json
        category = data.get('category')
        fact = data.get('fact')
        
        if not category or not fact:
            return jsonify({
                'success': False,
                'error': 'Category and fact are required'
            }), 400
        
        # Get user_id from request or context
        user_id = data.get('user_id', g.get('user_id', 'default'))
        
        # Get the user's memories
        memories = get_user_memories(user_id)
        
        # Add fact as a new core memory
        if "core_memory" not in memories:
            memories["core_memory"] = []
        
        memories["core_memory"].append({
            "content": fact,
            "timestamp": str(datetime.now()),
            "category": category
        })
        
        # Save updated memories
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        memory_path = os.path.join(base_dir, 'data', 'memories', f'user_{user_id}_memories.json')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(memory_path), exist_ok=True)
        
        with open(memory_path, 'w') as f:
            json.dump(memories, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Personal fact added successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@personal_info_bp.route('/api/personal-info/facts/<category>', methods=['DELETE'])
def delete_personal_fact(category):
    """Delete a personal fact from the system"""
    try:
        data = request.json
        fact = data.get('fact')
        
        if not fact:
            return jsonify({
                'success': False,
                'error': 'Fact is required'
            }), 400
        
        # Get user_id from request or context
        user_id = data.get('user_id', g.get('user_id', 'default'))
        
        # Get the user's memories
        memories = get_user_memories(user_id)
        
        # Find the category
        found = False
        for memory in memories.get("core_memory", []):
            if memory.get("content") == fact:
                memories["core_memory"].remove(memory)
                found = True
                break
        
        if found:
            # Save the updated memories
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            memory_path = os.path.join(base_dir, 'data', 'memories', f'user_{user_id}_memories.json')
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(memory_path), exist_ok=True)
            
            with open(memory_path, 'w') as f:
                json.dump(memories, f, indent=2)
            
            return jsonify({
                'success': True,
                'message': f'Deleted fact from category {category}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Fact not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@personal_info_bp.route('/api/personal-info/test-retrieval', methods=['POST'])
def test_fact_retrieval():
    """Test what facts would be retrieved for a given message"""
    try:
        data = request.json
        message = data.get('message', '')
        channel = data.get('channel', 'text')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        # Get user_id from request or context
        user_id = data.get('user_id', g.get('user_id', 'default'))
        
        # Get the user's memories
        memories = get_user_memories(user_id)
        
        # Create a mock conversation history
        conversation_history = [{
            'channel': channel,
            'text': message
        }]
        
        # Create a test prompt
        test_prompt = "You are an AI assistant."
        
        # Enhance the prompt with personal info
        enhanced_prompt = test_prompt + "\n"
        
        # Extract the facts that were added
        facts_added = []
        for memory in memories.get("core_memory", []):
            enhanced_prompt += f"- {memory.get('content')}\n"
            facts_added.append(memory.get("content"))
        
        return jsonify({
            'success': True,
            'message': message,
            'channel': channel,
            'facts_retrieved': facts_added,
            'enhanced_prompt': enhanced_prompt
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@personal_info_bp.route('/api/personal-info/extract-from-messages', methods=['POST'])
def extract_facts_from_messages():
    """Extract facts from a batch of messages"""
    try:
        data = request.json
        messages = data.get('messages', [])
        add_to_personal_info = data.get('add_to_personal_info', False)
        
        if not messages:
            return jsonify({
                'success': False,
                'error': 'Messages are required'
            }), 400
        
        # Get user_id from request or context
        user_id = data.get('user_id', g.get('user_id', 'default'))
        
        # Get the user's memories
        memories = get_user_memories(user_id)
        
        # Extract facts
        extracted_facts = {}
        
        for message in messages:
            content = message.get("content", "").lower()
            if "my name is" in content:
                name_parts = content.split("my name is", 1)[1].strip().rstrip(".").split()
                if name_parts:
                    extracted_facts["name"] = name_parts[0].capitalize()
            else:
                extracted_facts.setdefault("facts", []).append(content)
        
        # Add to personal info if requested
        if add_to_personal_info:
            for fact in extracted_facts.get("facts", []):
                add_personal_fact_helper(user_id, "Personal Information", fact)
        
        return jsonify({
            'success': True,
            'extracted_facts': extracted_facts,
            'added_to_personal_info': add_to_personal_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def add_personal_fact_helper(user_id, category, fact):
    # Get the user's memories
    memories = get_user_memories(user_id)
    
    # Add fact as a new core memory
    if "core_memory" not in memories:
        memories["core_memory"] = []
    
    memories["core_memory"].append({
        "content": fact,
        "timestamp": str(datetime.now()),
        "category": category
    })
    
    # Save updated memories
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    memory_path = os.path.join(base_dir, 'data', 'memories', f'user_{user_id}_memories.json')
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(memory_path), exist_ok=True)
    
    with open(memory_path, 'w') as f:
        json.dump(memories, f, indent=2)
