# iMessage Suggestions Flow

This document explains the complete flow of how iMessage suggestions are generated in the Alexis AI desktop app.

## Overview

The iMessage suggestions feature provides personalized, contextually relevant message suggestions based on the user's active conversation in the Messages app. The system uses a combination of:

1. **Active Chat Detection**: Monitors the Messages app and extracts conversation context
2. **RAG-Enhanced Prompting**: Retrieves relevant past messages using Pinecone vector search
3. **Fine-Tuned Model**: Generates personalized suggestions using a fine-tuned GPT-4o-mini model
4. **HTTP Polling**: Delivers suggestions to the overlay UI via polling

## Detailed Flow

### 1. Active Chat Detection
**File: `/scripts/active_chat_detector.py`**

- Monitors the macOS Messages database (`~/Library/Messages/chat.db`)
- Detects when the active conversation changes
- Extracts recent messages (up to 10) from the active conversation
- Formats them into a conversation context with "Me:" and "Other:" prefixes
- Sends this context to the backend API for suggestion generation

### 2. Backend Processing
**File: `/backend/app.py` - `/api/message-suggestions` endpoint**

- Receives conversation context and user_id
- Parses the context into a structured conversation history with roles
- Extracts the last user message
- Uses a concise system prompt: "You draft message suggestions that match the user's writing style, fit the conversation context, and are ready to send without editing."
- Enhances the prompt with RAG context using `enhance_prompt_with_rag` from `rag/enhanced_rag_integration.py`
- Calls `HybridResponseGenerator.generate_response_suggestions()` to generate 3 personalized suggestions
- Returns suggestions as JSON
- Stores the latest suggestions for polling

### 3. RAG Enhancement
**Files: `/rag/enhanced_rag_integration.py` and `/rag/pinecone_rag.py`**

- Initializes the PineconeRAGSystem for the user
- Retrieves relevant past messages from Pinecone using vector search with OpenAI embeddings
- Filters and formats the RAG context to append to the system prompt
- Handles errors gracefully with fallback to the original system prompt
- Caches Pinecone RAG instances per user for efficiency

### 4. Message Generation
**File: `/utils/hybrid_response.py`**

- Analyzes conversation flow (greetings, questions, corrections)
- Generates a primary response with lower temperature (0.5)
- Generates additional diverse suggestions with increasing temperatures
- Filters suggestions to ensure they're sufficiently different
- Uses the fine-tuned GPT-4o-mini model for personalized suggestions

### 5. Suggestion Delivery
**Files: `/backend/app.py` and `/overlay-agent-xcode/WebSocketServer.swift`**

- Active chat detector sends suggestions to backend via `/api/update-suggestions`
- Backend stores these in a global `latest_suggestions` variable
- Overlay agent polls the `/api/latest-suggestions` endpoint every second
- When new suggestions are available, it updates the UI
- When a user selects a suggestion, it notifies the backend via `/api/suggestion-selected`

## Key Components

1. **PineconeRAGSystem**: Connects to Pinecone for vector storage and retrieval
2. **HybridResponseGenerator**: Generates personalized message suggestions
3. **HTTP Polling**: Reliable mechanism for delivering suggestions to the overlay UI

## Dependencies

- OpenAI API key (`OPENAI_API_KEY`) for embeddings and completions
- Pinecone API key and environment variables for vector search
- Flask backend running on port 5002
- SQLite access to the macOS Messages database

## Notes on Deprecated Code

Several older implementations have been moved to deprecated directories:
- `/rag/deprecated/` - Contains old RAG implementations
- `/deprecated/` - Contains unused integration scripts
- `/scripts/deprecated/` - Contains unused test scripts

The current active implementation uses the simplified RAG approach described in `/rag/README_SIMPLIFIED_RAG.md`.
