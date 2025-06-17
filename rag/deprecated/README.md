# Deprecated RAG Implementations

This directory contains RAG (Retrieval Augmented Generation) implementations that are no longer actively used in the main application. These files have been moved here to reduce confusion and simplify the codebase.

## Why These Files Were Deprecated

As part of our effort to simplify the iMessage RAG integration, we've consolidated our approach to use only Pinecone for vector storage and retrieval. The simplified implementation:

1. Focuses exclusively on iMessage text suggestions
2. Removes complex filtering and prioritization logic
3. Eliminates monkey patching
4. Provides better error handling with fallbacks
5. Reduces code complexity

## Current Implementation

The current RAG implementation uses:

- `enhanced_rag_integration.py` - Simplified RAG implementation for iMessage suggestions
- `pinecone_rag.py` - Core Pinecone vector database integration
- `app_integration.py` - Still used for the `add_interaction_to_rag` function

## Files in This Directory

- `embedding_rag.py` - Old embedding-based RAG implementation
- `faiss_rag.py` - Local vector storage using FAISS (replaced by Pinecone)
- `migrate_to_faiss.py` - Migration script for FAISS (no longer needed)
- `test_embedding_rag.py` - Tests for the old embedding RAG
- `embedding_integration.py` - Integration for the old embedding RAG
- `activate_embedding_rag.py` - Activation script for the old embedding RAG

## Note

These files are kept for reference purposes only and should not be imported or used in new code. If you need RAG functionality, please use the simplified implementation in `enhanced_rag_integration.py`.
