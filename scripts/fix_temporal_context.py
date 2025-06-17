#!/usr/bin/env python3

"""
Fix Temporal Context in Memory File

This script updates the temporal context (Past/Future) in the memory file
based on the current date. Events that have already occurred will be marked
as Past, while events that haven't occurred yet will be marked as Future.
"""

import os
import json
import re
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MEMORY_DIR = os.path.join(DATA_DIR, 'memory')
MEMORY_FILE = os.path.join(MEMORY_DIR, 'albert_memory.json')

def extract_date(content):
    """
    Extract date from memory content.
    
    Args:
        content: Memory content string
        
    Returns:
        datetime object or None if no date found
    """
    # Look for dates in format "Month DD, YYYY" or "Month DD YYYY"
    date_patterns = [
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,|\s+)\s*\d{4}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,|\s+)\s*\d{4}'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, content)
        if match:
            try:
                date_str = match.group(0)
                # Handle both formats: "Month DD, YYYY" and "Month DD YYYY"
                date_str = date_str.replace(',', '')
                return datetime.strptime(date_str, '%B %d %Y')
            except ValueError:
                try:
                    return datetime.strptime(date_str, '%b %d %Y')
                except ValueError:
                    pass
    
    # Look for dates in format "MM/DD/YYYY" or "MM-DD-YYYY"
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{1,2}-\d{1,2}-\d{4}'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, content)
        if match:
            try:
                date_str = match.group(0)
                if '/' in date_str:
                    return datetime.strptime(date_str, '%m/%d/%Y')
                else:
                    return datetime.strptime(date_str, '%m-%d-%Y')
            except ValueError:
                pass
    
    # Look for specific date mentions in the content
    date_mentions = re.findall(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,|\s+)\s*\d{4}', content)
    if date_mentions:
        try:
            # Clean up the date string
            date_str = date_mentions[0]
            date_str = re.sub(r'(?:st|nd|rd|th)', '', date_str)
            date_str = date_str.replace(',', '')
            return datetime.strptime(date_str, '%B %d %Y')
        except ValueError:
            pass
    
    # Look for year mentions with month and day
    year_mentions = re.findall(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}', content)
    if year_mentions:
        try:
            # Clean up the date string
            date_str = year_mentions[0]
            date_str = re.sub(r'(?:st|nd|rd|th)', '', date_str)
            date_str = date_str.replace(',', '')
            return datetime.strptime(date_str, '%B %d %Y')
        except ValueError:
            pass
    
    # Look for specific date formats like "January 23, 2025"
    match = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', content)
    if match:
        try:
            date_str = match.group(0).replace(',', '')
            return datetime.strptime(date_str, '%B %d %Y')
        except ValueError:
            pass
    
    # Look for specific date formats like "January 23 to January 31, 2025"
    match = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\s+to\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', content)
    if match:
        try:
            # Extract the end date
            date_parts = match.group(0).split(' to ')
            end_date_str = date_parts[1].replace(',', '')
            return datetime.strptime(end_date_str, '%B %d %Y')
        except (ValueError, IndexError):
            pass
    
    return None

def fix_temporal_context(dry_run=True):
    """
    Fix temporal context in memory file.
    
    Args:
        dry_run: If True, don't save changes
        
    Returns:
        tuple: (num_fixed, num_total)
    """
    try:
        # Load memory file
        with open(MEMORY_FILE, 'r') as f:
            memory_data = json.load(f)
        
        # Get current date
        current_date = datetime.now()
        logger.info(f"Current date: {current_date.strftime('%Y-%m-%d')}")
        
        # Track changes
        num_fixed = 0
        num_total = 0
        
        # Process episodic memories
        for memory in memory_data.get('episodic_memory', []):
            content = memory.get('content', '')
            
            # Skip memories that don't have temporal markers
            if not (content.startswith('Past') or content.startswith('Future')):
                continue
            
            num_total += 1
            
            # Extract date from content
            event_date = extract_date(content)
            
            if event_date:
                # Determine correct temporal context
                is_past = event_date < current_date
                current_context = 'Past' if content.startswith('Past') else 'Future'
                correct_context = 'Past' if is_past else 'Future'
                
                # Check if temporal context needs to be fixed
                if current_context != correct_context:
                    logger.info(f"Fixing: {content}")
                    logger.info(f"  Event date: {event_date.strftime('%Y-%m-%d')}")
                    logger.info(f"  Current context: {current_context}")
                    logger.info(f"  Correct context: {correct_context}")
                    
                    # Update content
                    if current_context == 'Past' and correct_context == 'Future':
                        # Change from Past to Future
                        new_content = content.replace('Past', 'Future', 1)
                    else:
                        # Change from Future to Past
                        new_content = content.replace('Future', 'Past', 1)
                    
                    logger.info(f"  New content: {new_content}")
                    memory['content'] = new_content
                    num_fixed += 1
        
        # Save changes if not dry run
        if not dry_run and num_fixed > 0:
            with open(MEMORY_FILE, 'w') as f:
                json.dump(memory_data, f, indent=2)
            logger.info(f"Saved {num_fixed} fixes to {MEMORY_FILE}")
        
        return num_fixed, num_total
    
    except Exception as e:
        logger.error(f"Error fixing temporal context: {e}")
        return 0, 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix temporal context in memory file')
    parser.add_argument('--apply', action='store_true', help='Apply fixes (default is dry run)')
    args = parser.parse_args()
    
    num_fixed, num_total = fix_temporal_context(dry_run=not args.apply)
    
    if args.apply:
        print(f"Fixed {num_fixed} out of {num_total} temporal contexts")
    else:
        print(f"Would fix {num_fixed} out of {num_total} temporal contexts (dry run)")
        print("Use --apply to save changes")
