#!/usr/bin/env python3
import requests
import logging
import sys
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_api_connection():
    """Test connection to the backend API"""
    try:
        message = "Test message from email listener"
        
        logger.info(f"Sending test message to API: {message}")
        
        # First, let's try a simple GET request to make sure the server is running
        try:
            test_response = requests.get("http://localhost:5000/api/test")
            logger.info(f"Test API Response: {test_response.status_code} - {test_response.text}")
        except Exception as e:
            logger.error(f"Error testing API connection with GET: {e}")
        
        # Make API call to the AI clone backend with minimal headers
        response = requests.post(
            "http://localhost:5000/api/chat",
            data=json.dumps({
                "message": message,
                "addToRag": False,
                "channel": "email",
                "subject": "Test Email",
                "saveToHistory": False
            }),
            headers={
                "Content-Type": "application/json"
            }
        )
        
        logger.info(f"API Response Status: {response.status_code}")
        logger.info(f"API Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            if "response" in response_data:
                logger.info(f"Received response from AI clone: {response_data['response']}")
                return True
            else:
                logger.error(f"Unexpected response format: {response_data}")
                return False
        else:
            logger.error(f"Error from backend API: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Error testing API connection: {e}")
        return False

if __name__ == "__main__":
    test_api_connection()
