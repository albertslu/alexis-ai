#!/usr/bin/env python3

"""
Memory Tools for AI Clone

This script provides tools for managing the memory system, including:
1. Cleaning up redundant memories
2. Dry-running memory extraction from messages
3. Analyzing memory content
"""

import os
import json
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any
import logging
from fuzzywuzzy import fuzz
import uuid
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the memory-enhanced RAG system
from rag.memory_enhanced_rag import MemoryEnhancedRAG
from rag.rag_system import MessageRAG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize OpenAI client if API key is available
openai_client = None
if os.getenv('OPENAI_API_KEY'):
    try:
        import openai
        # Create a simple client without extra parameters
        openai_client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {e}")
        logger.info("Continuing without OpenAI capabilities")

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MEMORY_DIR = os.path.join(DATA_DIR, 'memory')
CHAT_HISTORY_PATH = os.path.join(DATA_DIR, 'chat_history.json')
RAG_DB_PATH = os.path.join(DATA_DIR, 'rag', 'default_message_db.json')

def load_memory(user_id="albert"):
    """
    Load memory from file
    
    Args:
        user_id: User ID
        
    Returns:
        dict: Memory data
    """
    memory_file = os.path.join(MEMORY_DIR, f'{user_id}_memory.json')
    
    if not os.path.exists(memory_file):
        logger.error(f"Memory file not found: {memory_file}")
        return None
    
    try:
        with open(memory_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading memory: {e}")
        return None

def save_memory(memory_data, user_id="albert"):
    """
    Save memory to file
    
    Args:
        memory_data: Memory data
        user_id: User ID
        
    Returns:
        bool: Success status
    """
    memory_file = os.path.join(MEMORY_DIR, f'{user_id}_memory.json')
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        
        # Update last_updated timestamp
        memory_data["last_updated"] = datetime.now().isoformat()
        
        with open(memory_file, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        logger.info(f"Memory saved to: {memory_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return False

def calculate_similarity(str1, str2):
    """
    Calculate similarity between two strings
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        float: Similarity score (0-1)
    """
    # Use token sort ratio to handle word order differences
    return fuzz.token_sort_ratio(str1.lower(), str2.lower()) / 100.0

def deduplicate_memories(memory_data, similarity_threshold=0.8):
    """
    Remove duplicate or highly similar memories
    
    Args:
        memory_data: Memory data
        similarity_threshold: Threshold for considering memories similar (0-1)
        
    Returns:
        dict: Deduplicated memory data
        list: Removed duplicates
    """
    # Create a copy of the memory data
    deduplicated_data = {
        "core_memory": [],
        "episodic_memory": memory_data.get("episodic_memory", []),
        "archival_memory": memory_data.get("archival_memory", []),
        "last_updated": memory_data.get("last_updated", datetime.now().isoformat())
    }
    
    # Track removed duplicates
    removed_duplicates = []
    
    # Process core memories
    core_memories = memory_data.get("core_memory", [])
    processed_contents = []
    
    for memory in core_memories:
        content = memory.get("content", "")
        is_duplicate = False
        
        # Check if this memory is similar to any we've already processed
        for processed_content in processed_contents:
            similarity = calculate_similarity(content, processed_content)
            if similarity >= similarity_threshold:
                removed_duplicates.append({
                    "content": content,
                    "similar_to": processed_content,
                    "similarity": similarity
                })
                is_duplicate = True
                break
        
        if not is_duplicate:
            processed_contents.append(content)
            deduplicated_data["core_memory"].append(memory)
    
    return deduplicated_data, removed_duplicates

def extract_memories_from_messages_dry_run(max_messages=100):
    """
    Perform a dry run of memory extraction from messages
    
    Args:
        max_messages: Maximum number of messages to process
        
    Returns:
        dict: Potential new memories by category
    """
    # Load the RAG database
    rag = MessageRAG()
    
    # Get all messages
    all_messages = rag.messages
    
    # Process the most recent messages first
    recent_messages = all_messages[-max_messages:] if len(all_messages) > max_messages else all_messages
    
    logger.info(f"Processing {len(recent_messages)} recent messages")
    
    # Extract potential memories using LLM
    potential_memories = extract_memories_with_llm(recent_messages)
    
    return potential_memories

def extract_memories_with_llm(messages):
    """
    Extract potential memories from messages using an LLM
    
    Args:
        messages: List of messages
        
    Returns:
        dict: Potential memories by category
    """
    if not openai_client:
        logger.error("OpenAI client not initialized. Set OPENAI_API_KEY environment variable.")
        return {"core": [], "episodic": []}
    
    # Filter to user messages only
    user_messages = []
    for msg in messages:
        if "user_message" in msg and msg["user_message"]:
            user_messages.append({
                "text": msg["user_message"],
                "ai_response": msg.get("ai_message", "")
            })
    
    logger.info(f"Found {len(user_messages)} user messages")
    
    # Process messages in batches
    batch_size = 10
    message_batches = [user_messages[i:i + batch_size] for i in range(0, len(user_messages), batch_size)]
    
    potential_memories = {
        "core": [],
        "episodic": []
    }
    
    for batch_index, message_batch in enumerate(message_batches):
        if batch_index % 5 == 0:
            logger.info(f"Processing batch {batch_index + 1}/{len(message_batches)}...")
        
        # Format messages for the LLM
        messages_text = "\n\n".join([
            f"User: {msg.get('text', '')}\nAI: {msg.get('ai_response', '')}" 
            for msg in message_batch
        ])
        
        # Create the prompt for the LLM
        prompt = f"""
        You are an AI assistant tasked with extracting personal information from a user's messages.
        
        Extract information that falls into these categories:
        1. Core memories: Essential facts about the user that should be remembered long-term, including:
           - Education (schools, degrees, graduation dates)
           - Work (jobs, companies, roles, time periods)
           - Location (where they live or have lived)
           - Skills (technical skills, languages, certifications)
           - Interests (hobbies, activities, sports, topics they enjoy)
           - Preferences (things they like or dislike)
           - Social connections (family, friends, relationships)
           - Projects (work projects, side projects, startups)
           - Personal details (age, birthday, background)
        
        2. Episodic memories: Specific interactions or conversations that provide context, including:
           - Specific plans they've mentioned (trips, events, meetings)
           - Recent activities they've done
           - Ongoing conversations or topics they're discussing
           - Problems or challenges they're working through
        
        Here are the messages:
        
        {messages_text}
        
        For each message, determine if it contains information that should be remembered.
        Be very thorough and extract any potentially useful information.
        
        Format your response as a JSON object with these categories as keys and lists of extracted memories as values.
        If no information is found for a category, return an empty list for that category.
        
        IMPORTANT: Your response must be a valid JSON object that can be parsed with json.loads().
        Format it exactly like this example:
        {{"core": ["The user studied at UT Austin", "The user works as a photographer"], "episodic": ["The user mentioned planning a trip to Japan next month"]}}
        """
        
        try:
            # Call the OpenAI API
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You extract memories from messages and format them as valid JSON. Be thorough and extract any potentially useful information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            
            # Parse the JSON response
            try:
                # Clean the content to ensure it's valid JSON
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                extracted_info = json.loads(content)
                
                # Add the extracted information to our categories
                for category, memories in extracted_info.items():
                    if category in potential_memories and isinstance(memories, list):
                        potential_memories[category].extend(memories)
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response: {e}")
                logger.error(f"Response content: {content}")
        
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
    
    return potential_memories

def extract_memories_from_messages_simple(max_messages=100):
    """
    Extract memories from messages using pattern matching and keyword detection
    
    Args:
        max_messages: Maximum number of messages to process
        
    Returns:
        dict: Potential new memories by category
    """
    # Load the RAG database
    rag = MessageRAG()
    
    # Get all messages
    all_messages = rag.messages
    
    # Process the most recent messages first
    recent_messages = all_messages[-max_messages:] if len(all_messages) > max_messages else all_messages
    
    logger.info(f"Processing {len(recent_messages)} recent messages")
    
    # Define categories and keywords
    categories = {
        "education": ["study", "school", "university", "college", "degree", "class", "course", "major", "graduate", "education", "student", "learning", "UT Austin", "Coppell"],
        "work": ["job", "work", "career", "company", "business", "startup", "office", "project", "client", "boss", "colleague", "meeting", "interview", "hired", "position", "role", "photography", "photographer", "freelance"],
        "location": ["live", "living", "moved", "moving", "location", "city", "town", "state", "country", "address", "neighborhood", "area", "Dallas", "Austin", "Texas", "TX"],
        "interests": ["hobby", "interest", "enjoy", "like", "love", "passion", "fan", "favorite", "photography", "photo", "picture", "camera", "sport", "game", "play", "read", "watch", "listen", "music", "movie", "book", "travel", "cook", "grappling"],
        "preferences": ["prefer", "favorite", "like", "love", "hate", "dislike", "rather", "better", "best", "worst", "opinion", "think", "feel", "believe"],
        "skills": ["skill", "ability", "can", "know how", "expert", "proficient", "experienced", "trained", "certified", "programming", "code", "develop", "software", "language", "framework", "tool"],
        "plans": ["plan", "going to", "will", "future", "next", "soon", "tomorrow", "weekend", "month", "year", "schedule", "appointment", "meeting", "event", "trip", "vacation", "holiday", "visit"],
        "projects": ["project", "working on", "building", "creating", "developing", "making", "startup", "app", "website", "program", "system", "platform", "product", "service"]
    }
    
    # Initialize potential memories
    potential_memories = {
        "core": [],
        "episodic": []
    }
    
    # Process each message
    for message in recent_messages:
        user_message = message.get("user_message", "")
        ai_message = message.get("ai_message", "")
        
        if not user_message:
            continue
        
        # Skip very short messages
        if len(user_message) < 10:
            continue
        
        # Skip simple greetings or test messages
        if user_message.lower() in ["hello", "hi", "hey", "test"]:
            continue
        
        # Process the user message
        sentences = re.split(r'[.!?]', user_message)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue
            
            # Skip questions
            if '?' in sentence or sentence.lower().startswith(('what', 'how', 'why', 'when', 'where', 'who', 'is', 'are', 'can', 'could', 'would', 'will')):
                continue
            
            # Check for first-person statements (likely about the user)
            if re.search(r'\b(i|my|me|mine|myself)\b', sentence.lower()):
                # Check each category
                for category, keywords in categories.items():
                    if any(keyword.lower() in sentence.lower() for keyword in keywords):
                        # For core categories
                        if category in ["education", "work", "location", "interests", "preferences", "skills"]:
                            potential_memories["core"].append(f"{category.capitalize()}: {sentence}")
                        # For episodic categories
                        elif category in ["plans", "projects"]:
                            potential_memories["episodic"].append(sentence)
    
    # Deduplicate memories
    potential_memories["core"] = list(set(potential_memories["core"]))
    potential_memories["episodic"] = list(set(potential_memories["episodic"]))
    
    return potential_memories

def apply_extracted_memories(extracted_memories, user_id="albert"):
    """
    Apply extracted memories to the user's memory file
    
    Args:
        extracted_memories: Dictionary of extracted memories
        user_id: User ID
        
    Returns:
        bool: Success status
    """
    # Load existing memory
    memory_data = load_memory(user_id)
    
    if not memory_data:
        logger.error(f"Could not load memory for user {user_id}")
        return False
    
    # Add core memories
    core_memories_added = 0
    for memory_content in extracted_memories.get("core", []):
        # Check if this memory already exists (to avoid duplicates)
        exists = False
        for existing_memory in memory_data["core_memory"]:
            if calculate_similarity(memory_content, existing_memory["content"]) > 0.7:
                exists = True
                break
        
        if not exists:
            memory_data["core_memory"].append({
                "id": str(uuid.uuid4()),
                "content": memory_content,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            })
            core_memories_added += 1
    
    # Add episodic memories
    episodic_memories_added = 0
    for memory_content in extracted_memories.get("episodic", []):
        # Check if this memory already exists (to avoid duplicates)
        exists = False
        for existing_memory in memory_data["episodic_memory"]:
            if calculate_similarity(memory_content, existing_memory["content"]) > 0.7:
                exists = True
                break
        
        if not exists:
            memory_data["episodic_memory"].append({
                "id": str(uuid.uuid4()),
                "content": memory_content,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            })
            episodic_memories_added += 1
    
    # Save updated memory
    if save_memory(memory_data, user_id):
        logger.info(f"Added {core_memories_added} core memories and {episodic_memories_added} episodic memories")
        return True
    else:
        logger.error("Failed to save updated memory")
        return False

def analyze_memory(user_id="albert"):
    """
    Analyze memory content and provide statistics
    
    Args:
        user_id: User ID
        
    Returns:
        dict: Memory statistics
    """
    memory_data = load_memory(user_id)
    
    if not memory_data:
        return None
    
    stats = {
        "core_memory_count": len(memory_data.get("core_memory", [])),
        "episodic_memory_count": len(memory_data.get("episodic_memory", [])),
        "archival_memory_count": len(memory_data.get("archival_memory", [])),
        "categories": {},
        "last_updated": memory_data.get("last_updated", "")
    }
    
    # Analyze core memory categories
    categories = {}
    for memory in memory_data.get("core_memory", []):
        content = memory.get("content", "")
        category = content.split(":")[0] if ":" in content else "Unknown"
        categories[category] = categories.get(category, 0) + 1
    
    stats["categories"] = categories
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Memory Tools for AI Clone")
    parser.add_argument("--user", help="User ID", default="albert")
    parser.add_argument("--action", choices=["deduplicate", "dry-run", "analyze", "apply"], required=True,
                        help="Action to perform")
    parser.add_argument("--max-messages", type=int, default=100,
                        help="Maximum number of messages to process for dry run")
    parser.add_argument("--similarity", type=float, default=0.8,
                        help="Similarity threshold for deduplication (0-1)")
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes (for deduplicate action)")
    
    args = parser.parse_args()
    
    if args.action == "deduplicate":
        memory_data = load_memory(args.user)
        if memory_data:
            deduplicated_data, removed_duplicates = deduplicate_memories(memory_data, args.similarity)
            
            print(f"Found {len(removed_duplicates)} duplicate memories:")
            for i, duplicate in enumerate(removed_duplicates):
                print(f"{i+1}. {duplicate['content']}")
                print(f"   Similar to: {duplicate['similar_to']}")
                print(f"   Similarity: {duplicate['similarity']:.2f}")
            
            if args.apply:
                if save_memory(deduplicated_data, args.user):
                    print(f"Deduplicated memory saved with {len(deduplicated_data['core_memory'])} core memories")
            else:
                print("Dry run completed. Use --apply to save changes.")
    
    elif args.action == "dry-run":
        potential_memories = extract_memories_from_messages_simple(args.max_messages)
        
        print("\nPotential core memories:")
        for i, memory in enumerate(potential_memories["core"]):
            print(f"{i+1}. {memory}")
        
        print("\nPotential episodic memories:")
        for i, memory in enumerate(potential_memories["episodic"]):
            print(f"{i+1}. {memory}")
    
    elif args.action == "analyze":
        stats = analyze_memory(args.user)
        
        if stats:
            print(f"Memory Analysis for {args.user}:")
            print(f"Core memories: {stats['core_memory_count']}")
            print(f"Episodic memories: {stats['episodic_memory_count']}")
            print(f"Archival memories: {stats['archival_memory_count']}")
            print(f"Last updated: {stats['last_updated']}")
            
            print("\nCore memory categories:")
            for category, count in stats["categories"].items():
                print(f"- {category}: {count}")
    
    elif args.action == "apply":
        potential_memories = extract_memories_from_messages_simple(args.max_messages)
        apply_extracted_memories(potential_memories, args.user)

if __name__ == "__main__":
    main()
