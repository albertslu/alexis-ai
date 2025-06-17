"""
Personal Discord Message Collector

This script collects your personal Discord messages using your user token.
NOTE: Using a user token instead of a bot token is against Discord's Terms of Service.
This script is for educational purposes only.
"""

import os
import json
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import time
import sys

# Load environment variables
load_dotenv()

# Configuration
USER_TOKEN = os.getenv('DISCORD_USER_TOKEN')  # Your personal Discord token
USER_ID = os.getenv('DISCORD_USER_ID')
OUTPUT_FILE = f'data/raw/discord_messages_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
DAYS_TO_COLLECT = 30  # Number of days of message history to collect

def get_dm_channels():
    """Get a list of DM channels"""
    headers = {
        'Authorization': USER_TOKEN,
        'Content-Type': 'application/json'
    }
    
    response = requests.get('https://discord.com/api/v9/users/@me/channels', headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching DM channels: {response.status_code}")
        print(response.text)
        return []
        
    return response.json()

def get_messages(channel_id, limit=100):
    """Get messages from a channel"""
    headers = {
        'Authorization': USER_TOKEN,
        'Content-Type': 'application/json'
    }
    
    # Calculate timestamp for messages from the last X days
    after_date = datetime.now() - timedelta(days=DAYS_TO_COLLECT)
    after_timestamp = int(after_date.timestamp() * 1000)
    
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching messages: {response.status_code}")
        print(response.text)
        return []
        
    return response.json()

def get_context_messages(channel_id, message_id, limit=5):
    """Get messages before a specific message (context)"""
    headers = {
        'Authorization': USER_TOKEN,
        'Content-Type': 'application/json'
    }
    
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages?before={message_id}&limit={limit}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching context messages: {response.status_code}")
        return []
        
    return response.json()

def collect_messages():
    """Collect messages from DM channels"""
    if not USER_TOKEN:
        print("Error: DISCORD_USER_TOKEN not found in .env file")
        print("Please add your personal Discord token to the .env file as DISCORD_USER_TOKEN")
        return
        
    if not USER_ID:
        print("Error: DISCORD_USER_ID not found in .env file")
        return
        
    print("Fetching DM channels...")
    dm_channels = get_dm_channels()
    print(f"Found {len(dm_channels)} DM channels")
    
    all_messages = []
    user_id = USER_ID
    
    for channel in dm_channels:
        # Skip group DMs for simplicity
        if channel.get('type') != 1:  # 1 = DM, 3 = Group DM
            continue
            
        recipient = channel['recipients'][0]
        print(f"Processing DMs with {recipient['username']}#{recipient['discriminator']}")
        
        # Get messages from this channel
        messages = get_messages(channel['id'])
        print(f"Found {len(messages)} messages")
        
        # Process messages
        for msg in messages:
            # Only collect your own messages
            if msg['author']['id'] == user_id:
                # Get context (previous messages)
                context_messages = get_context_messages(channel['id'], msg['id'])
                
                # Format context messages
                formatted_context = []
                for ctx_msg in context_messages:
                    if ctx_msg['author']['id'] != user_id:  # Only include messages from others
                        formatted_context.append({
                            'author_id': ctx_msg['author']['id'],
                            'author_name': ctx_msg['author']['username'],
                            'content': ctx_msg['content'],
                            'timestamp': ctx_msg['timestamp']
                        })
                
                # Add message to collection
                all_messages.append({
                    'message_id': msg['id'],
                    'channel_id': channel['id'],
                    'channel_name': f"DM with {recipient['username']}",
                    'guild_id': None,
                    'guild_name': 'DMs',
                    'content': msg['content'],
                    'timestamp': msg['timestamp'],
                    'context': formatted_context,
                    'has_attachments': len(msg.get('attachments', [])) > 0,
                    'mentions_users': [mention['id'] for mention in msg.get('mentions', [])],
                    'mentions_roles': [],
                    'reference': msg.get('referenced_message', {}).get('id') if msg.get('referenced_message') else None
                })
                
                # Respect rate limits
                time.sleep(0.1)
        
        print(f"Collected {len([m for m in all_messages if m['channel_id'] == channel['id']])} of your messages")
        
        # Respect rate limits between channels
        time.sleep(1)
    
    # Save collected messages
    if all_messages:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_messages, f, ensure_ascii=False, indent=2)
            
        # Also save as CSV
        csv_file = OUTPUT_FILE.replace('.json', '.csv')
        df = pd.DataFrame([{k: v for k, v in msg.items() if k != 'context'} for msg in all_messages])
        df.to_csv(csv_file, index=False)
        
        print(f"\nCollected {len(all_messages)} messages total")
        print(f"Data saved to {OUTPUT_FILE} and {csv_file}")
    else:
        print("\nNo messages collected")

if __name__ == "__main__":
    print("=== Personal Discord Message Collector ===")
    print("WARNING: Using a user token is against Discord's Terms of Service.")
    print("This script is for educational purposes only.")
    print("Continuing automatically...")
    
    collect_messages()
