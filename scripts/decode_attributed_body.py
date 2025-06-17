#!/usr/bin/env python3

import sqlite3
import re
import sys

def extract_text_from_attributed_body(blob):
    """
    Extract plain text from NSAttributedString BLOB data
    """
    if not blob:
        return ""
    
    # Convert blob to readable characters
    readable = ''.join([chr(b) if 32 <= b <= 126 else ' ' for b in blob])
    
    # Look for the pattern: NSString followed by message text before iI
    # The pattern seems to be: NSString....+"[MESSAGE]"...iI
    message_pattern = re.search(r'NSString[^"]*\+"([^"]+)"', readable)
    if message_pattern:
        message_text = message_pattern.group(1).strip()
        if message_text and len(message_text) > 1:
            return message_text
    
    # Alternative pattern: look for text between NSString and iI
    alt_pattern = re.search(r'NSString[^a-zA-Z]*([A-Za-z][^.]*?)(?:\s*iI|\s*\.\.\.)', readable)
    if alt_pattern:
        message_text = alt_pattern.group(1).strip()
        # Remove any remaining artifacts
        message_text = re.sub(r'\s*iI\s*', '', message_text)
        message_text = re.sub(r'\s+', ' ', message_text).strip()
        if message_text and len(message_text) > 1:
            return message_text
    
    # Fallback: Try to find readable text patterns and filter out metadata
    text_patterns = re.findall(r'[A-Za-z][A-Za-z0-9\s,.\'\!\?\-\/\(\)]*[A-Za-z0-9\.\!\?]', readable)
    
    # Filter out metadata patterns
    filtered_patterns = []
    for pattern in text_patterns:
        pattern = pattern.strip()
        # Keep patterns that look like actual message content
        if (len(pattern) > 3 and 
            'NSString' not in pattern and
            'NSObject' not in pattern and
            'NSAttributed' not in pattern and
            'NSNumber' not in pattern and
            'NSValue' not in pattern and
            'NSDictionary' not in pattern and
            'kIMMessage' not in pattern and
            'streamtyped' not in pattern and
            'AttributeName' not in pattern and
            pattern != 'iI' and
            pattern != 'i' and
            not pattern.isdigit()):
            filtered_patterns.append(pattern)
    
    # Join the patterns and clean up
    extracted_text = ' '.join(filtered_patterns)
    extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
    
    # Final cleanup - remove any remaining "iI" artifacts
    extracted_text = re.sub(r'\s*iI\s*$', '', extracted_text)
    extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
    
    return extracted_text

def main():
    # Connect to the database
    db_path = '/Users/albertlu/Library/Messages/chat.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get user's recent messages with empty text but non-empty attributedBody
    cursor.execute("""
        SELECT ROWID, text, attributedBody, is_from_me, date 
        FROM message 
        WHERE ROWID IN (SELECT message_id FROM chat_message_join WHERE chat_id = 15) 
        AND is_from_me = 1 
        AND (text IS NULL OR text = '') 
        AND attributedBody IS NOT NULL
        ORDER BY date DESC 
        LIMIT 10
    """)
    
    messages = cursor.fetchall()
    
    print("Decoding user's messages from attributedBody:")
    print("=" * 60)
    
    for rowid, text, blob, is_from_me, date in messages:
        extracted_text = extract_text_from_attributed_body(blob)
        print(f"ROWID {rowid}:")
        print(f"  Original text: '{text}'")
        print(f"  Extracted: '{extracted_text}'")
        print(f"  Blob length: {len(blob) if blob else 0} bytes")
        print()
    
    conn.close()

if __name__ == "__main__":
    main() 