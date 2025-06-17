import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Print OpenAI package version
import openai
print(f"OpenAI version: {openai.__version__}")

try:
    # Initialize OpenAI client
    client = OpenAI()
    print("Client initialized successfully")
    
    # Test a simple API call
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
    )
    print("API call successful")
    print(f"Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
