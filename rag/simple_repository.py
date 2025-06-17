#!/usr/bin/env python3

"""
Simple Data Repository

A lightweight repository for storing and retrieving messages without external dependencies.
"""

import os
import json
import uuid
import math
from datetime import datetime
from pathlib import Path
from collections import Counter

class SimpleDataRepository:
    """
    A simplified repository for storing and retrieving user communications.
    
    This class provides storage for messages from various sources and simple
    text-based search functionality without external dependencies.
    """
    
    def __init__(self, user_id="default", data_dir=None):
        """
        Initialize the repository for a specific user.
        
        Args:
            user_id: Identifier for the user
            data_dir: Directory to store the data (default: project_root/data/repository)
        """
        self.user_id = user_id
        
        # Set up data directory
        if data_dir is None:
            # Default to project_root/data/repository
            project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.data_dir = project_root / "data" / "repository" / user_id
        else:
            self.data_dir = Path(data_dir) / user_id
            
        # Create directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize repository files
        self.messages_file = self.data_dir / "messages.json"
        self.linkedin_file = self.data_dir / "linkedin.json"
        self.metadata_file = self.data_dir / "metadata.json"
        
        # Initialize data structures
        self.messages = []
        self.linkedin_data = {}
        self.metadata = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "sources": [],
            "message_count": 0
        }
        
        # Load existing data if available
        self._load_data()
    
    def _load_data(self):
        """Load existing data from files."""
        # Load messages
        if self.messages_file.exists():
            with open(self.messages_file, 'r') as f:
                data = json.load(f)
                self.messages = data.get("messages", [])
        
        # Load LinkedIn data
        if self.linkedin_file.exists():
            with open(self.linkedin_file, 'r') as f:
                self.linkedin_data = json.load(f)
        
        # Load metadata
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
    
    def _save_data(self):
        """Save data to files."""
        # Update metadata
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["message_count"] = len(self.messages)
        
        # Save messages
        with open(self.messages_file, 'w') as f:
            json.dump({"messages": self.messages}, f, indent=2)
        
        # Save LinkedIn data
        with open(self.linkedin_file, 'w') as f:
            json.dump(self.linkedin_data, f, indent=2)
        
        # Save metadata
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def add_messages(self, messages, source="manual", context=None):
        """
        Add messages to the repository.
        
        Args:
            messages: List of message dictionaries with text, sender, timestamp
            source: Source of the messages (e.g., 'imessage', 'discord', 'manual')
            context: Additional context about the messages (e.g., conversation thread)
            
        Returns:
            Number of messages added
        """
        if not messages:
            return 0
        
        # Add source to metadata if not already present
        if source not in self.metadata["sources"]:
            self.metadata["sources"].append(source)
        
        # Process and add each message
        added_count = 0
        
        for msg in messages:
            # Ensure message has required fields
            if "text" not in msg:
                continue
                
            # Create message object with metadata
            message_obj = {
                "id": str(uuid.uuid4()),
                "text": msg["text"],
                "sender": msg.get("sender", "user"),
                "timestamp": msg.get("timestamp", datetime.now().isoformat()),
                "source": source,
                "context": context or {},
                "thread_id": msg.get("thread_id", None),
                "previous_message": msg.get("previous_message", None),
                "next_message": msg.get("next_message", None),
                "metadata": {
                    "added_at": datetime.now().isoformat(),
                    "original_format": msg.get("original_format", None),
                }
            }
            
            # Add message to repository
            self.messages.append(message_obj)
            added_count += 1
        
        # Save data
        self._save_data()
        
        return added_count
    
    def add_linkedin_data(self, linkedin_data):
        """
        Add LinkedIn profile data to the repository.
        
        Args:
            linkedin_data: Dictionary containing LinkedIn profile information
            
        Returns:
            True if successful, False otherwise
        """
        if not linkedin_data:
            return False
        
        # Add LinkedIn as a source if not already present
        if "linkedin" not in self.metadata["sources"]:
            self.metadata["sources"].append("linkedin")
        
        # Store LinkedIn data
        self.linkedin_data = {
            **linkedin_data,
            "added_at": datetime.now().isoformat()
        }
        
        # Save data
        self._save_data()
        
        # Process LinkedIn data into message-like format for retrieval
        self._process_linkedin_for_retrieval()
        
        return True
    
    def _process_linkedin_for_retrieval(self):
        """Process LinkedIn data into message-like format for retrieval."""
        if not self.linkedin_data:
            return
        
        linkedin_messages = []
        
        # Process profile information
        if "profile" in self.linkedin_data:
            profile = self.linkedin_data["profile"]
            
            # Add name as a message
            if "name" in profile:
                linkedin_messages.append({
                    "text": f"My name is {profile['name']}",
                    "sender": "user",
                    "source": "linkedin",
                    "context": {"section": "profile", "type": "name"}
                })
            
            # Add headline/summary as a message
            if "headline" in profile and profile["headline"]:
                linkedin_messages.append({
                    "text": f"My professional headline: {profile['headline']}",
                    "sender": "user",
                    "source": "linkedin",
                    "context": {"section": "profile", "type": "headline"}
                })
            
            # Add location as a message
            if "location" in profile and profile["location"]:
                linkedin_messages.append({
                    "text": f"I am located in {profile['location']}",
                    "sender": "user",
                    "source": "linkedin",
                    "context": {"section": "profile", "type": "location"}
                })
            
            # Add about/summary as a message
            if "about" in profile and profile["about"]:
                linkedin_messages.append({
                    "text": f"About me professionally: {profile['about']}",
                    "sender": "user",
                    "source": "linkedin",
                    "context": {"section": "profile", "type": "about"}
                })
            elif "summary" in profile and profile["summary"]:
                linkedin_messages.append({
                    "text": f"About me professionally: {profile['summary']}",
                    "sender": "user",
                    "source": "linkedin",
                    "context": {"section": "profile", "type": "summary"}
                })
        
        # Process experience
        if "experience" in self.linkedin_data:
            # Add a summary of current role
            current_jobs = [job for job in self.linkedin_data["experience"] if "Present" in job.get("duration", "")]
            if current_jobs:
                current_job = current_jobs[0]
                current_job_text = f"I currently work as {current_job.get('title', 'a professional')} at {current_job.get('company', 'a company')}."
                
                linkedin_messages.append({
                    "text": current_job_text,
                    "sender": "user",
                    "source": "linkedin",
                    "context": {"section": "experience", "type": "current", "company": current_job.get("company")}
                })
            
            # Process all experience entries
            for job in self.linkedin_data["experience"]:
                job_text = f"I worked at {job.get('company', 'a company')} as {job.get('title', 'a professional')}"
                
                if "duration" in job and job["duration"]:
                    job_text += f" ({job['duration']})"
                
                job_text += "."
                
                if "description" in job and job["description"]:
                    job_text += f" {job['description']}"
                
                linkedin_messages.append({
                    "text": job_text,
                    "sender": "user",
                    "source": "linkedin",
                    "context": {"section": "experience", "company": job.get("company")}
                })
        
        # Process education
        if "education" in self.linkedin_data:
            for edu in self.linkedin_data["education"]:
                edu_text = f"I studied at {edu.get('school', 'a school')}"
                
                if edu.get('degree') and edu.get('field'):
                    edu_text = f"I earned a {edu.get('degree')} in {edu.get('field')} at {edu.get('school', 'a school')}"
                elif edu.get('degree'):
                    edu_text = f"I earned a {edu.get('degree')} at {edu.get('school', 'a school')}"
                elif edu.get('field'):
                    edu_text = f"I studied {edu.get('field')} at {edu.get('school', 'a school')}"
                
                if edu.get('dates'):
                    edu_text += f" ({edu.get('dates')})"
                
                edu_text += "."
                
                linkedin_messages.append({
                    "text": edu_text,
                    "sender": "user",
                    "source": "linkedin",
                    "context": {"section": "education", "school": edu.get("school")}
                })
        
        # Process skills
        if "skills" in self.linkedin_data and self.linkedin_data["skills"]:
            # Handle both list and string formats
            skills = self.linkedin_data["skills"]
            if isinstance(skills, list) and skills:
                skills_text = f"My professional skills include: {', '.join(skills)}"
                
                linkedin_messages.append({
                    "text": skills_text,
                    "sender": "user",
                    "source": "linkedin",
                    "context": {"section": "skills"}
                })
        
        # Add access level information
        if "access_level" in self.linkedin_data:
            access_level = self.linkedin_data["access_level"]
            linkedin_messages.append({
                "text": f"My LinkedIn profile access level: {access_level}",
                "sender": "user",
                "source": "linkedin",
                "context": {"section": "metadata", "type": "access_level"}
            })
        
        # Add these messages to the repository
        if linkedin_messages:
            self.add_messages(linkedin_messages, source="linkedin")
    
    def retrieve_similar(self, query, top_k=5, source_filter=None):
        """
        Retrieve messages similar to the query using a simple text similarity algorithm.
        
        Args:
            query: The query text
            top_k: Number of similar messages to retrieve
            source_filter: Optional filter for specific sources
            
        Returns:
            List of similar messages with similarity scores
        """
        if not self.messages:
            return []
        
        # Filter by source first if specified
        messages_to_search = self.messages
        if source_filter:
            messages_to_search = [msg for msg in messages_to_search if msg["source"] == source_filter]
        
        # Simple word-based matching
        query_words = set(query.lower().split())
        
        # Calculate TF-IDF scores
        # First, count the frequency of each word across all documents
        word_document_counts = Counter()
        for msg in messages_to_search:
            text = msg.get('text', '').lower()
            unique_words = set(text.split())
            for word in unique_words:
                word_document_counts[word] += 1
        
        # Calculate scores for each message
        scored_messages = []
        total_documents = len(messages_to_search)
        
        for msg in messages_to_search:
            text = msg.get('text', '').lower()
            words = text.split()
            word_counts = Counter(words)
            
            # Calculate TF-IDF score for query words
            score = 0
            for word in query_words:
                if word in word_counts:
                    # Term frequency in this document
                    tf = word_counts[word] / max(1, len(words))
                    # Inverse document frequency
                    idf = math.log(total_documents / max(1, word_document_counts[word]))
                    score += tf * idf
            
            # Add message with score if it has any matching words
            if score > 0:
                msg_copy = msg.copy()
                msg_copy["similarity"] = score
                scored_messages.append((score, msg_copy))
        
        # Sort by similarity score (descending)
        scored_messages.sort(reverse=True, key=lambda x: x[0])
        
        # Return top_k results
        results = [msg for _, msg in scored_messages[:top_k]]
        return results
    
    def get_sources(self):
        """Get list of data sources in the repository."""
        return self.metadata["sources"]
    
    def get_message_count(self):
        """Get total number of messages in the repository."""
        return len(self.messages)
    
    def get_metadata(self):
        """Get repository metadata."""
        return self.metadata
