#!/usr/bin/env python3

"""
Check Pinecone RAG for Email Content

This script checks if there are emails stored in the Pinecone RAG system
by querying the index for email-related content and examining metadata.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Pinecone RAG system
from rag.pinecone_rag import PineconeRAGSystem

def check_pinecone_emails(user_id=None):
    """
    Check if there are emails in the Pinecone RAG system.
    
    Args:
        user_id: User ID to check
        
    Returns:
        bool: True if emails are found, False otherwise
    """
    print(f"Checking Pinecone RAG for emails for user: {user_id}")
    
    # Initialize the Pinecone RAG system
    try:
        rag_system = PineconeRAGSystem(user_id=user_id)
        
        # Wait for verification to complete
        if not rag_system.is_verified():
            print("Waiting for Pinecone verification...")
            rag_system.wait_for_verification(timeout=10)
        
        if not rag_system.verification_success:
            print("Pinecone verification failed. Cannot proceed.")
            return False
        
        # Search for email-related content
        print("Searching for email content...")
        
        # First, try to search for content with the "email" source
        email_results = rag_system.search("email communication", top_k=10)
        
        # Check if any results have 'email' in their source
        email_specific_results = []
        for result in email_results:
            if 'email' in result.get('source', '').lower():
                email_specific_results.append(result)
        
        if email_specific_results:
            print(f"Found {len(email_specific_results)} email-specific results:")
            for i, result in enumerate(email_specific_results, 1):
                print(f"\n--- Result {i} ---")
                print(f"Score: {result['score']}")
                print(f"Source: {result['source']}")
                print(f"Text: {result['text'][:100]}..." if len(result['text']) > 100 else f"Text: {result['text']}")
                print(f"Timestamp: {result['timestamp']}")
            return True
        else:
            print("No email-specific content found in the first search.")
            
            # Try another search with common email terms
            print("Trying alternative search with email-specific terms...")
            alt_results = rag_system.search("gmail inbox sent received subject", top_k=10)
            
            # Check if any results have 'email' in their source
            email_specific_alt_results = []
            for result in alt_results:
                if 'email' in result.get('source', '').lower():
                    email_specific_alt_results.append(result)
            
            if email_specific_alt_results:
                print(f"Found {len(email_specific_alt_results)} email-specific results in alternative search:")
                for i, result in enumerate(email_specific_alt_results, 1):
                    print(f"\n--- Result {i} ---")
                    print(f"Score: {result['score']}")
                    print(f"Source: {result['source']}")
                    print(f"Text: {result['text'][:100]}..." if len(result['text']) > 100 else f"Text: {result['text']}")
                    print(f"Timestamp: {result['timestamp']}")
                return True
            else:
                print("No email-specific content found in the alternative search.")
                
                # Try to directly check the metadata in Pinecone
                print("\nChecking for 'source=email' metadata in Pinecone...")
                try:
                    # Use a direct query to Pinecone to check for source=email metadata
                    # First get an embedding for a generic query
                    query_embedding = rag_system._get_embedding("email communication")
                    
                    # Query with metadata filter for source=email
                    results = rag_system.index.query(
                        vector=query_embedding,
                        top_k=10,
                        include_metadata=True,
                        namespace="",
                        filter={"source": "email"}
                    )
                    
                    if results.matches:
                        print(f"Found {len(results.matches)} vectors with source=email metadata:")
                        for i, match in enumerate(results.matches, 1):
                            print(f"\n--- Result {i} ---")
                            print(f"Score: {match.score}")
                            print(f"ID: {match.id}")
                            print(f"Text: {match.metadata.get('text', '')[:100]}..." if len(match.metadata.get('text', '')) > 100 else f"Text: {match.metadata.get('text', '')}")
                            print(f"Source: {match.metadata.get('source', 'unknown')}")
                            print(f"Channel: {match.metadata.get('channel', 'unknown')}")
                            print(f"Timestamp: {match.metadata.get('timestamp', '')}")
                        return True
                    else:
                        print("No vectors found with source=email metadata.")
                        
                        # Try one more search with a broader filter
                        print("\nTrying one final search with broader criteria...")
                        # Get all vectors for this user
                        results = rag_system.index.query(
                            vector=query_embedding,
                            top_k=20,
                            include_metadata=True,
                            namespace="",
                            filter={"user_id": user_id}
                        )
                        
                        if results.matches:
                            print(f"Found {len(results.matches)} vectors for user {user_id}:")
                            email_count = 0
                            
                            # Print all vectors to inspect their metadata
                            print("\nAll vectors for this user:")
                            for i, match in enumerate(results.matches, 1):
                                print(f"\n--- Vector {i} ---")
                                print(f"ID: {match.id}")
                                print(f"Source: {match.metadata.get('source', 'unknown')}")
                                print(f"Channel: {match.metadata.get('channel', 'unknown')}")
                                
                                # Check if this is an email-related vector
                                source = match.metadata.get('source', 'unknown')
                                channel = match.metadata.get('channel', 'unknown')
                                text = match.metadata.get('text', '')
                                
                                is_email_related = (
                                    'email' in source.lower() or 
                                    'email' in channel.lower() or
                                    'gmail' in text.lower() or
                                    '@' in text
                                )
                                
                                if is_email_related:
                                    email_count += 1
                                    print(f"\n--- Email-Related Vector {email_count} ---")
                                    print(f"Score: {match.score}")
                                    print(f"Source: {source}")
                                    print(f"Channel: {channel}")
                                    print(f"Text: {text[:100]}..." if len(text) > 100 else f"Text: {text}")
                            
                            if email_count > 0:
                                print(f"\nFound {email_count} email-related vectors out of {len(results.matches)} total.")
                                return True
                            else:
                                print("\nNo email-related vectors found among user vectors.")
                        else:
                            print(f"No vectors found for user {user_id}.")
                        
                        return False
                
                except Exception as e:
                    print(f"Error during metadata check: {e}")
                    return False
    
    except Exception as e:
        print(f"Error checking Pinecone RAG: {e}")
        return False

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Get user ID from command line or use default
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if user_id is None:
        print("No user ID provided. Please provide a user ID as a command line argument.")
        sys.exit(1)
    
    # Check for emails
    check_pinecone_emails(user_id)
