"""
User RAG Manager for AI Clone

This module provides helper functions to initialize and check user-specific RAG systems.
"""
import os
from rag.rag_system import MessageRAG


def initialize_user_rag(user_id):
    """
    Initialize the RAG system for a user.
    Loads default data only for user_albertlu43, otherwise creates empty or loads existing user RAG.
    """
    # Only load default for the demo user
    if user_id == "user_albertlu43":
        rag = MessageRAG(user_id, clear_existing=False)
        # If no messages, initialize with default data
        if not rag.messages:
            # Optionally, load default data if needed (handled elsewhere)
            pass
    else:
        # For all other users, only load if the file exists, otherwise create empty
        rag = MessageRAG(user_id, clear_existing=False)
        if not rag.messages:
            # No RAG exists for this user, keep it empty
            pass
    return rag


def user_rag_exists(user_id):
    """
    Check if a user's RAG file exists and contains messages.
    """
    from rag.rag_system import RAG_DIR
    db_path = os.path.join(RAG_DIR, f'{user_id}_message_db.json')
    if not os.path.exists(db_path):
        return False
    try:
        import json
        with open(db_path, 'r') as f:
            data = json.load(f)
            return bool(data.get('messages', []))
    except Exception:
        return False
