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

def cancel_fine_tuning_job(job_id):
    """Cancel a fine-tuning job."""
    try:
        response = client.fine_tuning.jobs.cancel(job_id)
        print(f"Successfully cancelled job {job_id}")
        print(f"Status: {response.status}")
        return response
    except Exception as e:
        print(f"Error cancelling job {job_id}: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cancel_finetune_job.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    cancel_fine_tuning_job(job_id)
