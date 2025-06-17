import os
import json
from flask import Flask, request, jsonify
from openai import OpenAI
from backend.app import app, get_email_topic
from rag.app_integration import enhance_prompt_with_rag

# Create a test Flask app context
app.config['TESTING'] = True
test_app = app.test_client()

# Test data
test_email = {
    "subject": "Meeting Request",
    "recipient": "John Smith",
    "message": "Hi there, I hope you're doing well. I wanted to reach out to see if you'd be available for a quick call next week to discuss potential collaboration opportunities. I've been following your work and think there might be some interesting ways we could work together. Let me know what times work best for you. Thanks for considering this!",
    "formality": "professional"
}

# Run the test
with app.test_request_context(json=test_email):
    print("\n===== Testing Email Response Generation =====\n")
    print(f"Original email: {test_email['message']}\n")
    
    # Extract the email topic
    email_topic = get_email_topic(test_email['message'])
    print(f"Extracted topic: {email_topic}\n")
    
    # Make the request
    response = test_app.post('/api/draft-email', json=test_email)
    response_data = json.loads(response.data)
    
    print("===== Generated Email Response =====\n")
    print(response_data['draft'])
    
    # Check if the response contains phrases from the original email
    original_phrases = [
        "hope you're doing well",
        "reach out",
        "available for a quick call",
        "discuss potential collaboration",
        "following your work",
        "interesting ways",
        "work together",
        "times work best",
        "thanks for considering"
    ]
    
    print("\n===== Checking for Repetition =====\n")
    found_phrases = []
    for phrase in original_phrases:
        if phrase.lower() in response_data['draft'].lower():
            found_phrases.append(phrase)
    
    if found_phrases:
        print(f"WARNING: Found {len(found_phrases)} repeated phrases from the original email:")
        for phrase in found_phrases:
            print(f"- '{phrase}'")
    else:
        print("SUCCESS: No phrases from the original email were repeated in the response!")
