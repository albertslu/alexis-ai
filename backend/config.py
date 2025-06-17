"""
Configuration module for the AI Clone

Loads environment variables and provides configuration settings
for the Discord bot and AI components.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the AI Clone"""
    
    # Discord configuration
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    DISCORD_USER_ID = int(os.getenv('DISCORD_USER_ID')) if os.getenv('DISCORD_USER_ID') else None
    
    # Handle guild IDs more robustly
    guild_ids_raw = os.getenv('DISCORD_GUILD_IDS', '')
    # Remove any comments that might be in the .env file
    if '#' in guild_ids_raw:
        guild_ids_raw = guild_ids_raw.split('#')[0].strip()
    DISCORD_GUILD_IDS = [int(id.strip()) for id in guild_ids_raw.split(',') if id.strip()]
    
    # Response channels configuration
    # Special handling for 'dm' in response channels
    RESPONSE_CHANNELS_RAW = os.getenv('RESPONSE_CHANNELS', '').split(',')
    RESPONSE_CHANNELS = []
    DM_ENABLED = False
    
    for channel in RESPONSE_CHANNELS_RAW:
        channel = channel.strip()
        if channel.lower() == 'dm':
            DM_ENABLED = True
        elif channel:
            try:
                RESPONSE_CHANNELS.append(int(channel))
            except ValueError:
                print(f"Warning: Invalid channel ID '{channel}' in RESPONSE_CHANNELS")
    
    # Bot behavior configuration
    RESPONSE_PROBABILITY = float(os.getenv('RESPONSE_PROBABILITY', '0.8'))
    SUPERVISED_MODE = os.getenv('SUPERVISED_MODE', 'true').lower() == 'true'
    
    # OpenAI configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    AI_MODEL = os.getenv('AI_MODEL', 'gpt-4')
    
    # Validate configuration
    @classmethod
    def validate(cls):
        """Validate the configuration and return a list of errors"""
        errors = []
        
        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN is not set in .env file")
        
        if not cls.DISCORD_USER_ID:
            errors.append("DISCORD_USER_ID is not set in .env file")
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set in .env file")
        
        return errors
