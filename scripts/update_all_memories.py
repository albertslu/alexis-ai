#!/usr/bin/env python3

"""
Update All Memories

This script updates all memories in the memory file to ensure correct temporal context.
"""

import os
import json
import sys
import re
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the date extraction and validation functions
from scripts.extract_memories_simple import extract_date_from_memory, validate_temporal_context

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MEMORY_DIR = os.path.join(DATA_DIR, 'memory')

def update_all_memories(user_id="albert", dry_run=True):
    """
    Update all memories in the memory file to ensure correct temporal context.
    
    Args:
        user_id: User ID
        dry_run: If True, don't save changes
        
    Returns:
        tuple: (num_updated, num_total)
    """
    memory_file = os.path.join(MEMORY_DIR, f'{user_id}_memory.json')
    
    if not os.path.exists(memory_file):
        logger.error(f"Memory file not found: {memory_file}")
        return 0, 0
    
    try:
        # Load memory file
        with open(memory_file, 'r') as f:
            memory_data = json.load(f)
        
        # Track changes
        num_updated = 0
        num_total = 0
        
        # Update episodic memories
        for memory in memory_data.get('episodic_memory', []):
            content = memory.get('content', '')
            
            # Skip memories that don't have temporal markers
            if not (content.startswith('Past') or content.startswith('Future')):
                continue
            
            num_total += 1
            
            # Special case for May/June 2025 trip (which should be future as of March 28, 2025)
            if "End of May/June 2025" in content and "Middle East" in content:
                if content.startswith('Past'):
                    memory['content'] = content.replace('Past', 'Future', 1)
                    num_updated += 1
                    logger.info(f"Special case: Keeping as future event: {content}")
                continue
            
            # Validate and update temporal context
            new_content = validate_temporal_context(content)
            
            # Check if content was updated
            if new_content != content:
                memory['content'] = new_content
                num_updated += 1
        
        # Save changes if not dry run
        if not dry_run and num_updated > 0:
            with open(memory_file, 'w') as f:
                json.dump(memory_data, f, indent=2)
            logger.info(f"Saved {num_updated} updates to {memory_file}")
        
        return num_updated, num_total
    
    except Exception as e:
        logger.error(f"Error updating memories: {e}")
        return 0, 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Update all memories in the memory file')
    parser.add_argument('--apply', action='store_true', help='Apply updates (default is dry run)')
    args = parser.parse_args()
    
    num_updated, num_total = update_all_memories(dry_run=not args.apply)
    
    if args.apply:
        print(f"Updated {num_updated} out of {num_total} memories")
    else:
        print(f"Would update {num_updated} out of {num_total} memories (dry run)")
        print("Use --apply to save changes")
