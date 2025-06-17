import os
import sys
from openai import OpenAI
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

# Configure OpenAI with custom httpx client to avoid proxy issues
http_client = httpx.Client()
client = OpenAI(api_key=api_key, http_client=http_client)

def list_fine_tuning_jobs():
    """List all fine-tuning jobs."""
    try:
        response = client.fine_tuning.jobs.list(limit=10)
        print(f"Found {len(response.data)} fine-tuning jobs:")
        for job in response.data:
            print(f"Job ID: {job.id}")
            print(f"Status: {job.status}")
            print(f"Model: {job.model}")
            print(f"Created at: {job.created_at}")
            print("-" * 50)
        return response.data
    except Exception as e:
        print(f"Error listing jobs: {e}")
        return None

if __name__ == "__main__":
    list_fine_tuning_jobs()
