"""
Setup script for Discord message collection.

This script helps you set up your environment for collecting Discord messages.
It will guide you through the process of creating a Discord bot, setting up
the necessary permissions, and configuring your .env file.
"""

import os
import sys
import re
from dotenv import load_dotenv

def check_env_file():
    """Check if .env file exists and has required variables."""
    env_file = os.path.join(os.getcwd(), '.env')
    
    if not os.path.exists(env_file):
        print("No .env file found. Creating one...")
        with open(env_file, 'w') as f:
            f.write("# Discord Configuration\n")
            f.write("DISCORD_TOKEN=\n")
            f.write("DISCORD_USER_ID=\n")
            f.write("\n# OpenAI Configuration\n")
            f.write("OPENAI_API_KEY=\n")
            f.write("AI_MODEL=gpt-4-turbo\n")
        print("Created .env file. Please fill in the required values.")
        return False
    
    # Load environment variables
    load_dotenv()
    
    # Check required variables
    missing_vars = []
    if not os.getenv('DISCORD_TOKEN'):
        missing_vars.append('DISCORD_TOKEN')
    if not os.getenv('DISCORD_USER_ID'):
        missing_vars.append('DISCORD_USER_ID')
    if not os.getenv('OPENAI_API_KEY'):
        missing_vars.append('OPENAI_API_KEY')
    
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("Please update your .env file with these values.")
        return False
    
    print("Environment file (.env) is properly configured.")
    return True

def guide_discord_bot_setup():
    """Guide the user through setting up a Discord bot."""
    print("\n=== Discord Bot Setup Guide ===\n")
    print("To collect your Discord messages, you need to create a Discord bot with the right permissions.")
    print("Follow these steps:\n")
    
    print("1. Go to the Discord Developer Portal: https://discord.com/developers/applications")
    print("2. Click 'New Application' and give it a name (e.g., 'Clone')")
    print("3. Go to the 'Bot' tab and click 'Add Bot'")
    print("4. Under the 'TOKEN' section, click 'Copy' to get your bot token")
    print("   - Add this token to your .env file as DISCORD_TOKEN")
    print("5. Enable ALL Privileged Gateway Intents:")
    print("   - PRESENCE INTENT")
    print("   - SERVER MEMBERS INTENT")
    print("   - MESSAGE CONTENT INTENT")
    print("6. Go to the 'OAuth2' tab, then 'URL Generator'")
    print("7. Select the following scopes:")
    print("   - bot")
    print("   - applications.commands")
    print("8. Select the following bot permissions:")
    print("   - Read Messages/View Channels")
    print("   - Send Messages")
    print("   - Read Message History")
    print("9. Copy the generated URL and open it in your browser")
    print("10. Add the bot to your server\n")
    
    print("To find your Discord User ID:")
    print("1. Open Discord Settings > Advanced")
    print("2. Enable 'Developer Mode'")
    print("3. Right-click on your username and select 'Copy ID'")
    print("   - Add this ID to your .env file as DISCORD_USER_ID\n")
    
    input("Press Enter when you've completed these steps...")

def guide_personal_token():
    """Guide the user through getting their personal Discord token."""
    print("\n=== Personal Discord Token Guide ===\n")
    print("WARNING: Using your personal Discord token is against Discord's Terms of Service.")
    print("This is for educational purposes only. Use at your own risk!\n")
    
    print("To get your personal Discord token:")
    print("1. Open Discord in your web browser (not the app)")
    print("2. Press F12 to open Developer Tools")
    print("3. Go to the 'Network' tab")
    print("4. Refresh the page")
    print("5. Look for a request to 'api/v9' or similar")
    print("6. In the request headers, find 'Authorization' - that's your token")
    print("7. Add this token to your .env file as DISCORD_USER_TOKEN\n")
    
    input("Press Enter when you've completed these steps (or press Ctrl+C to skip)...")

def guide_openai_setup():
    """Guide the user through setting up OpenAI API access."""
    print("\n=== OpenAI API Setup Guide ===\n")
    print("To fine-tune a model, you need an OpenAI API key.")
    print("Follow these steps:\n")
    
    print("1. Go to https://platform.openai.com/api-keys")
    print("2. Sign in or create an account")
    print("3. Click 'Create new secret key'")
    print("4. Add this key to your .env file as OPENAI_API_KEY\n")
    
    input("Press Enter when you've completed these steps...")

def update_env_file():
    """Update the .env file with user input."""
    env_file = os.path.join(os.getcwd(), '.env')
    
    # Load current values
    current_values = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    current_values[key] = value
    
    # Get new values
    print("\n=== Update Environment Variables ===\n")
    
    discord_token = input(f"Discord Bot Token [{current_values.get('DISCORD_TOKEN', '')}]: ")
    if discord_token:
        current_values['DISCORD_TOKEN'] = discord_token
    
    discord_user_id = input(f"Discord User ID [{current_values.get('DISCORD_USER_ID', '')}]: ")
    if discord_user_id:
        current_values['DISCORD_USER_ID'] = discord_user_id
    
    discord_user_token = input(f"Discord User Token (optional) [{current_values.get('DISCORD_USER_TOKEN', '')}]: ")
    if discord_user_token:
        current_values['DISCORD_USER_TOKEN'] = discord_user_token
    
    openai_api_key = input(f"OpenAI API Key [{current_values.get('OPENAI_API_KEY', '')}]: ")
    if openai_api_key:
        current_values['OPENAI_API_KEY'] = openai_api_key
    
    # Write updated values
    with open(env_file, 'w') as f:
        f.write("# Discord Configuration\n")
        f.write(f"DISCORD_TOKEN={current_values.get('DISCORD_TOKEN', '')}\n")
        f.write(f"DISCORD_USER_ID={current_values.get('DISCORD_USER_ID', '')}\n")
        if 'DISCORD_USER_TOKEN' in current_values:
            f.write(f"DISCORD_USER_TOKEN={current_values.get('DISCORD_USER_TOKEN', '')}\n")
        
        f.write("\n# OpenAI Configuration\n")
        f.write(f"OPENAI_API_KEY={current_values.get('OPENAI_API_KEY', '')}\n")
        f.write(f"AI_MODEL={current_values.get('AI_MODEL', 'gpt-4-turbo')}\n")
    
    print("\nEnvironment file updated successfully.")

def main():
    print("=== Discord Message Collection Setup ===\n")
    print("This script will help you set up your environment for collecting Discord messages.")
    
    # Check if .env file exists and has required variables
    env_configured = check_env_file()
    
    if not env_configured:
        # Guide the user through setup
        guide_discord_bot_setup()
        guide_personal_token()
        guide_openai_setup()
        update_env_file()
    
    print("\n=== Setup Complete ===\n")
    print("You can now collect your Discord messages using one of the following methods:")
    print("1. Bot Collection (recommended):")
    print("   python collect_discord_data.py")
    print("2. Personal Token Collection (educational only):")
    print("   python collect_personal_dms.py")
    print("3. Manual Collection:")
    print("   - Copy conversations from Discord")
    print("   - Save to a text file")
    print("   - Run: python convert_discord_chat.py your_file.txt models/your_model_name --your-name YourName")

if __name__ == "__main__":
    main()
