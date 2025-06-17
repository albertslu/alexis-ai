#!/usr/bin/env python3
"""
Simple Email Auto-Response System for AI Clone

This script integrates with your existing backend to provide email auto-response capabilities.
It uses your existing memory-enhanced RAG system to generate personalized responses.

Usage:
    python simple_email_responder.py --mode=check
    python simple_email_responder.py --mode=respond --email_id=<email_id>
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app import app, generate_response
from rag.memory_enhanced_rag import memory_rag

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Directory for pending responses
PENDING_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pending_responses')
os.makedirs(PENDING_DIR, exist_ok=True)

def check_unread_emails():
    """
    Check for unread emails that might need responses
    
    This is a placeholder function. In a production system, you would:
    1. Connect to your email account
    2. Retrieve unread emails
    3. Filter out automated emails
    4. Generate responses for personal emails
    
    For now, this just prints instructions for manual checking
    """
    print("\n" + "="*80)
    print("Email Auto-Response System")
    print("="*80)
    
    print("\nTo use this system with your existing email setup:")
    print("\n1. Check your inbox for new personal emails")
    print("2. For emails you want to auto-respond to, note the email ID or subject")
    print("3. Run this script with --mode=respond and provide the email content")
    
    print("\nExample:")
    print("python simple_email_responder.py --mode=respond --subject=\"Meeting request\" --content=\"Hey Albert, would you be available for a meeting next week? Best, John\"")
    
    print("\nThis will generate a response using your AI clone and save it for your review.")
    print("="*80)

def generate_email_response(subject, content, sender="example@example.com"):
    """
    Generate a response to an email using the AI clone
    
    Args:
        subject: Email subject
        content: Email content
        sender: Sender email address
        
    Returns:
        Generated response text
    """
    # Create a conversation history with just this email
    conversation_history = [{
        'sender': 'user',
        'text': content,
        'channel': 'email',
        'subject': subject
    }]
    
    # Enhance the prompt with memory context
    enhanced_prompt = memory_rag.enhance_prompt(
        system_prompt="You are an AI clone that mimics the user's communication style. When responding, naturally incorporate your memories and personal experiences when they're relevant to the conversation.",
        user_message=content,
        conversation_history=conversation_history
    )
    
    # Generate response using your existing backend
    with app.app_context():
        response = generate_response(
            message=content,
            system_prompt=enhanced_prompt,
            conversation_history=conversation_history,
            channel='email'
        )
    
    return response

def save_pending_response(email_id, email_details, response):
    """
    Save a pending response to file for later approval
    
    Args:
        email_id: Email ID or identifier
        email_details: Email details dictionary
        response: Generated response text
    """
    pending_file = os.path.join(PENDING_DIR, f"{email_id}.json")
    
    with open(pending_file, 'w') as f:
        json.dump({
            'email_id': email_id,
            'details': email_details,
            'response': response,
            'generated_at': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\nResponse saved to: {pending_file}")

def list_pending_responses():
    """
    List all pending responses
    
    Returns:
        List of pending response filenames
    """
    if not os.path.exists(PENDING_DIR):
        return []
    
    pending_files = [f for f in os.listdir(PENDING_DIR) if f.endswith('.json')]
    
    if pending_files:
        print("\n" + "="*80)
        print("Pending Email Responses")
        print("="*80)
        
        for i, filename in enumerate(pending_files):
            email_id = filename.replace('.json', '')
            pending_file = os.path.join(PENDING_DIR, filename)
            
            with open(pending_file, 'r') as f:
                data = json.load(f)
            
            print(f"\n{i+1}. Email ID: {email_id}")
            print(f"   Subject: {data['details']['subject']}")
            print(f"   From: {data.get('details', {}).get('sender', 'Unknown')}")
            print(f"   Generated: {data['generated_at']}")
            print(f"   Response Preview: {data['response'][:100]}...")
    else:
        print("\nNo pending responses found.")
    
    return pending_files

def view_response(email_id):
    """
    View a pending response
    
    Args:
        email_id: Email ID or identifier
    """
    pending_file = os.path.join(PENDING_DIR, f"{email_id}.json")
    
    if not os.path.exists(pending_file):
        print(f"\nNo pending response found for email {email_id}")
        return
    
    with open(pending_file, 'r') as f:
        data = json.load(f)
    
    print("\n" + "="*80)
    print(f"Response for Email: {email_id}")
    print("="*80)
    print(f"Subject: {data['details']['subject']}")
    print(f"From: {data.get('details', {}).get('sender', 'Unknown')}")
    print(f"Generated: {data['generated_at']}")
    print("="*80)
    print(data['response'])
    print("="*80)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Simple Email Auto-Response System')
    parser.add_argument('--mode', choices=['check', 'respond', 'list', 'view'], 
                        default='check', help='Operation mode')
    parser.add_argument('--email_id', help='Email ID for view mode')
    parser.add_argument('--subject', help='Email subject for respond mode')
    parser.add_argument('--content', help='Email content for respond mode')
    parser.add_argument('--sender', default='example@example.com', 
                        help='Sender email address for respond mode')
    args = parser.parse_args()
    
    # Execute based on mode
    if args.mode == 'check':
        check_unread_emails()
    elif args.mode == 'list':
        list_pending_responses()
    elif args.mode == 'view':
        if not args.email_id:
            print("Email ID is required for view mode")
            return
        view_response(args.email_id)
    elif args.mode == 'respond':
        if not args.subject or not args.content:
            print("Subject and content are required for respond mode")
            return
        
        # Generate response
        response = generate_email_response(args.subject, args.content, args.sender)
        
        # Create email details
        email_details = {
            'subject': args.subject,
            'body': args.content,
            'sender': args.sender,
            'to': 'you@example.com',
            'date': datetime.now().isoformat()
        }
        
        # Save pending response
        email_id = args.subject.lower().replace(' ', '_')
        save_pending_response(email_id, email_details, response)
        
        # Display response
        print("\n" + "="*80)
        print("Generated Response")
        print("="*80)
        print(f"Subject: Re: {args.subject}")
        print(f"To: {args.sender}")
        print("="*80)
        print(response)
        print("="*80)

if __name__ == "__main__":
    main()
