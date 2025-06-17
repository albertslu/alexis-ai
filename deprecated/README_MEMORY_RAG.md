# Memory-Enhanced RAG System for AI Clone

This document explains how the memory-enhanced RAG system works and how to integrate it with your AI clone.

## Overview

The memory-enhanced RAG system improves upon the existing RAG by organizing memories into a hierarchical structure similar to Letta's memory system. It provides better context for responses by combining:

1. Core facts about you from personal_info.json
2. Relevant past interactions from conversation history
3. Traditional RAG examples from your message database

## How It Works

### Memory Types

The system organizes memories into three categories:

1. **Core Memory**: Essential facts that are always included in the context
   - Initialized from personal_info.json
   - Contains information about your education, work, location, etc.
   - High-priority information that defines your identity

2. **Episodic Memory**: Specific conversations and interactions
   - Recent interactions with users
   - Automatically updated during conversations
   - Limited to 100 items (older items move to archival memory)

3. **Archival Memory**: Long-term storage for less frequently used information
   - Older episodic memories
   - Less frequently accessed information
   - Retrieved only when relevant to the current query

### Memory Management

The system includes several memory management features:

1. **Recency Tracking**: Tracks when memories were last accessed
2. **Relevance-Based Retrieval**: Retrieves memories based on relevance to the current query
3. **Automatic Archiving**: Moves less frequently used memories from episodic to archival
4. **Fact Extraction**: Extracts potential personal facts from conversations

### Integration with Existing RAG

The memory-enhanced RAG system builds on top of your existing RAG system:

1. It uses your personal_info.json for initializing core memories
2. It leverages your MessageRAG for retrieving relevant examples
3. It enhances prompts with both structured memories and RAG examples

## How to Use

### 1. Testing the Memory System

Run the test script to see how the memory system works:

```bash
python test_memory_rag.py
```

This will:
- Initialize core memories from personal_info.json
- Test memory retrieval for different queries
- Demonstrate memory updates from conversations

### 2. Integrating with Your Backend

The simplest way to integrate the memory system with your backend is to run:

```bash
python integrate_memory_rag.py
```

This script:
- Monkey-patches the enhance_prompt_with_rag function to use the memory-enhanced version
- Adds a wrapper to the chat endpoint to update memories after generating responses

### 3. Manual Integration

If you prefer to manually integrate the memory system:

1. In your backend code where you call `enhance_prompt_with_rag()`, it will automatically use the memory-enhanced version due to monkey patching.

2. After generating a response, add:
   ```python
   from rag.memory_enhanced_rag import update_memory_from_conversation
   update_memory_from_conversation(user_message, ai_response)
   ```

## Benefits Over Standard RAG

1. **Structured Memory**: Organizes information by importance and relevance
2. **Persistent Context**: Memories persist across sessions
3. **Automatic Memory Management**: Handles memory organization automatically
4. **Improved Context**: Provides more relevant context for responses

## Files

- `rag/memory_enhanced_rag.py`: The main implementation of the memory-enhanced RAG system
- `test_memory_rag.py`: Test script to verify the memory system works correctly
- `integrate_memory_rag.py`: Script to integrate the memory system with your backend
- `data/memory/albert_memory.json`: The memory file that stores your structured memories

## Comparison with Letta

This implementation provides many of the key benefits of Letta:

1. **Structured Memory**: Like Letta, it organizes memories into different types
2. **Persistent Context**: Memories persist across sessions, just like with Letta
3. **Automatic Extraction**: The system can extract new facts from conversations
4. **Relevance-Based Retrieval**: Only the most relevant memories are included in prompts

The main difference is that this implementation runs locally within your existing system, without requiring an external Letta server.
