import os
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from .simple_repository import SimpleDataRepository

class DataIntegration:
    """Handles integration of data from various sources into the unified repository."""
    
    def __init__(self, user_id="default"):
        """Initialize the data integration module.
        
        Args:
            user_id: Identifier for the user
        """
        self.user_id = user_id
        self.repository = SimpleDataRepository(user_id=user_id)
        
        # We'll use contextual analysis instead of hardcoded terms
        # This will help the model better understand conversation context
        self.max_context_messages = 5  # Maximum number of previous messages to include for context
    
    def process_imessage_data(self, db_path=None, days=30):
        """Process iMessage data from the user's Messages database.
        
        Args:
            db_path: Path to the Messages.db file (default: ~/Library/Messages/chat.db)
            days: Number of days of history to extract
            
        Returns:
            Number of messages processed
        """
        # Use the script's functionality to extract iMessage data
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts',
            'extract_imessage_training.py'
        )
        
        # Import the script as a module
        import sys
        sys.path.append(os.path.dirname(script_path))
        import importlib.util
        spec = importlib.util.spec_from_file_location("extract_imessage", script_path)
        extract_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(extract_module)
        
        try:
            # Extract raw iMessage data
            training_examples, raw_data_path = extract_module.extract_from_imessage_db(days=days, save_raw=True)
            
            if not raw_data_path or not os.path.exists(raw_data_path):
                raise FileNotFoundError("Failed to extract iMessage data")
                
            # Load the raw data
            with open(raw_data_path, 'r') as f:
                raw_data = json.load(f)
                
            # Process the raw data into our repository format
            messages = []
            # Raw data is a list of objects with 'contact' and 'messages' fields
            for conversation in raw_data:
                contact = conversation.get('contact', '')
                conversation_messages = conversation.get('messages', [])
                
                for msg in conversation_messages:
                    # Skip messages not from the user
                    if not msg.get('is_from_me', False):
                        continue
                        
                    # Skip empty messages
                    if not msg.get('text'):
                        continue
                        
                    # Create message object
                    message = {
                        "text": msg.get('text', ''),
                        "sender": "user",
                        "timestamp": msg.get('timestamp', ''),
                        "thread_id": contact,  # Use contact as thread_id
                        "previous_message": "",  # We don't have previous message in this format
                        "original_format": "imessage",
                        "is_identity_context": any(term in msg.get('text', '').lower() for term in ['i am', "i'm", 'my name', 'about me', 'about myself']),
                        "has_second_person_reference": any(term in msg.get('text', '').lower() for term in ['you', 'your', "you're"])
                    }
                    
                    messages.append(message)
            
            # Add messages to repository
            added_count = self.repository.add_messages(messages, source="imessage")
            
            return added_count
            
        except Exception as e:
            print(f"Error extracting iMessage data: {str(e)}")
            raise Exception(f"Failed to extract iMessage data: {str(e)}")
    
    def process_text_data(self, text_data, source_type="conversation"):
        """Process text data pasted by the user.
        
        Args:
            text_data: Text containing messages
            source_type: Type of text data ('conversation' or 'messages')
            
        Returns:
            Number of messages processed
        """
        if not text_data.strip():
            return 0
        
        messages = []
        
        if source_type == "conversation":
            # Process conversation format (with sender names)
            # Pattern to match "Name: Message" format
            pattern = r"([^:]+):\s*(.+)(?:\n|$)"
            matches = re.findall(pattern, text_data)
            
            # Group by conversation
            conversation = []
            for sender, text in matches:
                sender = sender.strip()
                text = text.strip()
                
                if not text:
                    continue
                
                conversation.append((sender, text))
            
            # Extract user messages with context
            for i, (sender, text) in enumerate(conversation):
                # Determine if this is a user message based on common patterns
                is_user = False
                
                # Common patterns for user identification
                user_patterns = [
                    r"^me$",
                    r"^i$",
                    r"^self$",
                    r"^user$",
                    # Add more patterns as needed
                ]
                
                for pattern in user_patterns:
                    if re.search(pattern, sender.lower()):
                        is_user = True
                        break
                
                if is_user:
                    # Get previous messages for context (up to 5 consecutive messages)
                    previous_messages = []
                    consecutive_count = 0
                    j = i - 1
                    
                    # Current sender to track consecutive messages
                    current_sender = None
                    
                    while j >= 0 and consecutive_count < 5:
                        prev_sender, prev_text = conversation[j]
                        
                        # Skip user messages when looking for context
                        is_prev_user = False
                        for pattern in user_patterns:
                            if re.search(pattern, prev_sender.lower()):
                                is_prev_user = True
                                break
                        
                        if is_prev_user:
                            break
                            
                        # Add this message to the context
                        previous_messages.append(prev_text)
                        consecutive_count += 1
                        j -= 1
                    
                    # Reverse to get chronological order
                    previous_messages.reverse()
                    
                    # Join multiple messages with a separator if they exist
                    previous_message = "\n".join(previous_messages) if previous_messages else None
                    
                    # Analyze message context to better understand conversation flow
                    # Instead of hardcoding specific terms, we'll use the surrounding context
                    is_identity_context = any(term in text.lower() for term in ['i am', "i'm", 'my name', 'about me', 'about myself'])
                    has_second_person_reference = any(term in text.lower() for term in ['you', 'your', "you're"])
                    
                    # Create message object
                    message = {
                        "text": text,
                        "sender": "user",
                        "timestamp": datetime.now().isoformat(),
                        "previous_message": previous_message,
                        "original_format": "text_conversation",
                        "is_identity_context": is_identity_context,
                        "has_second_person_reference": has_second_person_reference
                    }
                    
                    messages.append(message)
        
        elif source_type == "messages":
            # Process just messages format (one per line)
            lines = text_data.strip().split("\n")
            
            for text in lines:
                text = text.strip()
                if not text:
                    continue
                
                # Analyze message context to better understand conversation flow
                # Instead of hardcoding specific terms, we'll use the surrounding context
                is_identity_context = any(term in text.lower() for term in ['i am', "i'm", 'my name', 'about me', 'about myself'])
                has_second_person_reference = any(term in text.lower() for term in ['you', 'your', "you're"])
                
                # Create message object
                message = {
                    "text": text,
                    "sender": "user",
                    "timestamp": datetime.now().isoformat(),
                    "original_format": "text_messages",
                    "is_identity_context": is_identity_context,
                    "has_second_person_reference": has_second_person_reference
                }
                
                messages.append(message)
        
        # Add messages to repository
        added_count = self.repository.add_messages(messages, source="text_upload")
        
        return added_count
    
    def process_linkedin_data(self, linkedin_text):
        """Process LinkedIn profile data.
        
        Args:
            linkedin_text: Text of the LinkedIn profile or URL
            
        Returns:
            True if successful, False otherwise
        """
        # Check if it's a URL
        if linkedin_text.startswith("http") and "linkedin.com" in linkedin_text:
            # Extract the profile name from the URL
            match = re.search(r"linkedin\.com/in/([\w-]+)", linkedin_text)
            if match:
                profile_name = match.group(1)
                
                try:
                    # Import the LinkedIn scraper module
                    import sys
                    import os
                    import asyncio
                    from pathlib import Path
                    from utils.auth import db
                    
                    # Make sure we can import the LinkedIn scraper
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if base_dir not in sys.path:
                        sys.path.append(base_dir)
                    
                    # Import the LinkedIn scraper
                    from scrapers.linkedin.browser_use_scraper import LinkedInBrowserUseScraper
                    
                    # Create a temporary output path for the profile data
                    temp_dir = os.path.join(base_dir, 'temp')
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_output_path = os.path.join(temp_dir, f"{profile_name}_temp.json")
                    
                    print(f"Extracting LinkedIn profile data for {profile_name}...")
                    
                    # Set up browser scraper - now using the Cloud API version
                    scraper = LinkedInBrowserUseScraper(verbose=True)
                    
                    # Get LinkedIn credentials to allow proper login
                    from scrapers.linkedin.browser_use_scraper import get_linkedin_credentials
                    credentials = get_linkedin_credentials()
                    
                    # Create and run the event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Extract profile data - run the scraper asynchronously with credentials
                    profile_data = loop.run_until_complete(
                        scraper.scrape_profile(profile_url=linkedin_text, credentials=credentials)
                    )
                    
                    # Close the event loop
                    loop.close()
                    
                    # If we have profile data, first save to MongoDB for persistence
                    if profile_data:
                        # Save the profile data to MongoDB - fail loudly if this fails
                        try:
                            db.users.update_one(
                                {"user_id": self.user_id},
                                {"$set": {"linkedin_data": profile_data}}
                            )
                            print(f"Saved LinkedIn profile for user {self.user_id} to MongoDB")
                        except Exception as e:
                            error_msg = f"Error saving LinkedIn data to MongoDB: {e}"
                            print(error_msg)
                            # Fail loudly - don't silently fall back to local storage
                            return False
                        
                        # Also save to the local file system for compatibility with
                        # existing RAG loading code (not as a fallback)
                        try:
                            # Create output path for the profile data
                            output_dir = os.path.join(
                                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'scrapers', 'data', 'linkedin_profiles'
                            )
                            
                            # Ensure the output directory exists
                            os.makedirs(output_dir, exist_ok=True)
                            
                            # Save the profile data to the local file
                            output_path = os.path.join(output_dir, f"{profile_name}_persona.json")
                            with open(output_path, 'w') as f:
                                json.dump(profile_data, f, indent=2)
                            print(f"Saved LinkedIn profile to local file: {output_path}")
                            
                            # Add to repository for immediate use
                            # NOTE: We're no longer using SimpleDataRepository
                            # This will be updated in the future to add LinkedIn data to the memory system
                            # For now, we'll just return success if we saved to MongoDB
                            print("LinkedIn data saved to MongoDB. Will be added to memory system in a future update.")
                            return True
                        except Exception as e:
                            print(f"Warning: Could not save LinkedIn data to local file: {e}")
                            # If we saved to MongoDB, consider this a success even if local file fails
                            return True
                    
                    return False
                    
                except Exception as e:
                    print(f"Error extracting LinkedIn profile: {str(e)}")
                    return False
        
        # If it's not a URL, assume it's the profile text
        # Try to parse sections
        sections = {}
        
        # Simple section detection
        current_section = "profile"
        sections[current_section] = linkedin_text
        
        # Look for common LinkedIn sections
        section_patterns = {
            "experience": [r"Experience", r"Work", r"Employment"],
            "education": [r"Education", r"Academic", r"School"],
            "skills": [r"Skills", r"Expertise"],
            "summary": [r"Summary", r"About", r"Bio"]
        }
        
        for section, patterns in section_patterns.items():
            for pattern in patterns:
                if re.search(f"\b{pattern}\b", linkedin_text, re.IGNORECASE):
                    sections[section] = "Found"
        
        # Create LinkedIn data structure
        linkedin_data = {
            "profile": {
                "text": sections.get("profile", ""),
                "summary": sections.get("summary", "")
            },
            "has_experience": "experience" in sections,
            "has_education": "education" in sections,
            "has_skills": "skills" in sections,
            "source": "linkedin_text"
        }
        
        # Add to repository
        print("LinkedIn text data received. Will be added to memory system in a future update.")
        return True
