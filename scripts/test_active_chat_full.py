#!/usr/bin/env python3
"""
Full test script for active chat detection and context retrieval in Messages app
"""

import subprocess
import sqlite3
import time
from pathlib import Path

# Path to Messages database
MESSAGES_DB = Path.home() / "Library/Messages/chat.db"

def get_active_chat_guid():
    """Get the GUID of the active chat from Messages preferences"""
    try:
        print("Running: defaults read com.apple.MobileSMS.plist CKLastSelectedItemIdentifier")
        result = subprocess.run(
            ["defaults", "read", "com.apple.MobileSMS.plist", "CKLastSelectedItemIdentifier"],
            capture_output=True, text=True, check=False
        )
        
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            print(f"stderr: {result.stderr}")
            print("Make sure Messages app is open and you have a conversation selected")
            return None
            
        raw_id = result.stdout.strip()
        print(f"Raw preference value: {raw_id}")
        
        # The format is typically list-service;-;identifier
        # We want to extract just the identifier part
        if '-' not in raw_id:
            print(f"Unexpected format for preference value: {raw_id}")
            return raw_id
            
        guid = raw_id.replace(raw_id.split('-')[0] + '-', '')
        print(f"Extracted GUID: {guid}")
        return guid
    except Exception as e:
        print(f"Error reading preference: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_chat_info(guid):
    """Get information about a chat from its GUID"""
    try:
        # Extract the identifier from the GUID
        # For iMessage;-;+1234567890, we want +1234567890
        identifier = guid
        if ";" in guid:
            parts = guid.split(";")
            if len(parts) > 2:
                identifier = parts[2]
        
        print(f"Looking for chat with identifier: {identifier}")
        
        # Connect to the Messages database
        conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
        
        # Find the chat with this identifier
        cursor = conn.execute(
            "SELECT ROWID, chat_identifier, display_name FROM chat WHERE chat_identifier LIKE ?",
            (f"%{identifier}%",)
        )
        chat = cursor.fetchone()
        
        if not chat:
            print(f"No chat found for identifier: {identifier}")
            conn.close()
            return None
            
        chat_id, chat_identifier, display_name = chat
        print(f"Found chat: ID={chat_id}, Identifier={chat_identifier}, Name={display_name}")
        
        return chat_id
    except Exception as e:
        print(f"Error getting chat info: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_recent_messages(chat_id, limit=10):
    """Get recent messages from a chat"""
    try:
        conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
        
        # Get the most recent messages
        cursor = conn.execute("""
            SELECT 
                m.text, 
                m.is_from_me, 
                datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') as date_str
            FROM 
                message m
                JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            WHERE 
                cmj.chat_id = ?
                AND m.text IS NOT NULL
            ORDER BY 
                m.date DESC
            LIMIT ?
        """, (chat_id, limit))
        
        messages = cursor.fetchall()
        conn.close()
        
        if not messages:
            print(f"No messages found for chat ID: {chat_id}")
            return []
            
        print(f"Found {len(messages)} messages")
        
        # Format messages
        formatted_messages = []
        for text, is_from_me, date in messages:
            sender = "Me" if is_from_me else "Other"
            formatted_messages.append((sender, text, date))
        
        return formatted_messages
    except Exception as e:
        print(f"Error getting messages: {e}")
        import traceback
        traceback.print_exc()
        return []

def format_conversation(messages):
    """Format messages into a conversation string"""
    # Reverse to get chronological order
    messages.reverse()
    
    conversation = ""
    for sender, text, date in messages:
        conversation += f"{sender} ({date}): {text}\n"
    
    return conversation

def main():
    print("Full test for active chat detection and context retrieval")
    print("Make sure Messages app is open with a conversation selected")
    print("This script requires Full Disk Access permissions")
    
    # First, check if we can access the Messages database
    if not Path(MESSAGES_DB).exists():
        print(f"ERROR: Messages database not found at {MESSAGES_DB}")
        print("Make sure Messages app has been run at least once")
        print("and that this app has Full Disk Access permissions")
        return
    else:
        print(f"Messages database found at {MESSAGES_DB}")
        try:
            # Test database connection
            conn = sqlite3.connect(f"file:{MESSAGES_DB}?mode=ro", uri=True)
            conn.close()
            print("Successfully connected to Messages database")
        except sqlite3.OperationalError as e:
            print(f"ERROR: Cannot access Messages database: {e}")
            print("Make sure this app has Full Disk Access permissions")
            return
    
    # Now test the defaults command
    print("\nTesting defaults command to get active chat...")
    guid = get_active_chat_guid()
    if not guid:
        print("Could not get active chat GUID")
        print("Make sure Messages app is open with a conversation selected")
        return
    
    # Get chat info
    print("\nGetting chat information...")
    chat_id = get_chat_info(guid)
    if not chat_id:
        print("Could not get chat information")
        return
    
    # Get recent messages
    print("\nGetting recent messages...")
    messages = get_recent_messages(chat_id)
    if not messages:
        print("Could not get recent messages")
        return
    
    # Format conversation
    conversation = format_conversation(messages)
    print("\nCONVERSATION CONTEXT:")
    print(conversation)
    
    print("\nTest completed successfully!")
    print("This confirms we can detect the active chat and retrieve its context")
    print("We can now implement the one-way communication flow")

if __name__ == "__main__":
    main()
