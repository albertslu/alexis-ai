# Simplified iMessage RAG Integration

This document explains the simplified Retrieval Augmented Generation (RAG) implementation for iMessage suggestions.

## Overview

We've simplified the RAG integration to focus exclusively on iMessage suggestions, removing complexity and improving robustness. The implementation uses Pinecone as the vector database for storing and retrieving relevant message examples.

## Key Components

### 1. Enhanced RAG Integration (`enhanced_rag_integration.py`)

The main implementation file that provides:
- Simple context retrieval from Pinecone
- Basic filtering to exclude bad examples
- Conversation context extraction
- Error handling with fallback to original prompt

```python
# Example usage
from rag.enhanced_rag_integration import enhance_prompt_with_rag

enhanced_prompt = enhance_prompt_with_rag(
    system_prompt="You draft message suggestions that match the user's writing style.",
    user_message="Are you free this weekend?",
    conversation_history=recent_messages,
    user_id="user123"
)
```

### 2. Pinecone RAG System (`pinecone_rag.py`)

The core vector database integration that:
- Manages connections to Pinecone
- Handles vector search and retrieval
- Provides verification and error handling

### 3. RAG Storage (`rag_storage.py`)

Contains the `add_interaction_to_rag` function which is used to store new message examples in the RAG system. This is a focused extraction from the original app_integration.py, keeping only the essential functionality.

### 4. App Integration (`app_integration.py`)

Retained for backward compatibility. Contains the original implementation of various RAG functions.

## Implementation Details

1. **Simplified Approach**: We've removed complex filtering, prioritization, and email-specific logic to focus solely on iMessage suggestions.

2. **No Monkey Patching**: The implementation avoids monkey patching to reduce confusion and improve maintainability.

3. **Robust Error Handling**: If RAG fails (e.g., Pinecone verification issues), the system falls back to the original prompt.

4. **Focused Context**: Retrieves fewer, more relevant examples (up to 5) to improve suggestion quality.

5. **Conversation Context**: Includes recent conversation history for better contextual understanding.

## Backend Integration

The backend `/api/message-suggestions` endpoint uses this simplified implementation with proper error handling:

```python
# Initialize with basic system prompt
enhanced_prompt = system_prompt

try:
    # Try to enhance with RAG
    enhanced_prompt = enhance_prompt_with_rag(
        system_prompt=system_prompt,
        user_message=last_user_message,
        conversation_history=conversation_history,
        user_id=effective_user_id
    )
except Exception as e:
    # Fall back to basic prompt if RAG fails
    logger.error(f"Error using Pinecone RAG: {e}. Continuing with basic prompt.")
    # Continue with the basic system prompt
```

## Deprecated Implementations

Older, more complex implementations have been moved to the `rag/deprecated/` directory to reduce confusion and simplify the codebase. These include:

- `memory_enhanced_rag.py` - Experimental memory-enhanced RAG system that is not used in production
- `clean_database.py` - Utility for cleaning up the RAG database
- `test_rag.py` - Test script for the RAG system
- `initialize_rag.py` - Old initialization script superseded by `initialize_enhanced_rag`

Additional test scripts and integration files have been moved to `/deprecated/` and `/scripts/deprecated/` directories.

## Complete Documentation

For a full explanation of the iMessage suggestions flow, including how the RAG system integrates with the active chat detector and overlay agent, see the `IMESSAGE_SUGGESTIONS_FLOW.md` file in the root directory.
