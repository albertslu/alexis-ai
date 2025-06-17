import os
import json
import uuid
from datetime import datetime, timedelta
import difflib
import re
import random
import string
from pathlib import Path

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
FEEDBACK_DIR = os.path.join(DATA_DIR, 'feedback')
CHAT_HISTORY_DIR = DATA_DIR
DEFAULT_CHAT_HISTORY_PATH = os.path.join(CHAT_HISTORY_DIR, 'chat_history.json')

# Ensure directories exist
os.makedirs(FEEDBACK_DIR, exist_ok=True)

class FeedbackSystem:
    """
    System for recording and analyzing feedback on AI responses.
    """
    
    def __init__(self, user_id="default"):
        """
        Initialize the feedback system.
        
        Args:
            user_id: Identifier for the user/agent
        """
        self.user_id = user_id
        
        # Special case for albertlu43 account - use the main files
        if user_id == "albertlu43" or user_id == "user_albertlu43":
            self.feedback_path = os.path.join(FEEDBACK_DIR, 'default_feedback.json')
            self.chat_history_path = DEFAULT_CHAT_HISTORY_PATH
            print(f"Using main files for albertlu43 account")
        else:
            # For other users, use user-specific files
            self.feedback_path = os.path.join(FEEDBACK_DIR, f'{user_id}_feedback.json')
            self.chat_history_path = os.path.join(CHAT_HISTORY_DIR, f'{user_id}_chat_history.json')
            
            # Migrate default chat history to user-specific chat history if needed
            self._migrate_chat_history()
        
        self.feedback_data = self._load_feedback_data()
        
        print(f"Initialized feedback system for user: {user_id}")
        print(f"Using feedback path: {self.feedback_path}")
        print(f"Using chat history path: {self.chat_history_path}")
    
    def _load_feedback_data(self):
        """
        Load feedback data from file.
        
        Returns:
            dict: Feedback data
        """
        if os.path.exists(self.feedback_path):
            try:
                with open(self.feedback_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading feedback data: {str(e)}")
                # Return default structure
                return {
                    "feedback_records": [],
                    "stats": {
                        "total": 0
                    }
                }
        else:
            # Create default structure
            return {
                "feedback_records": [],
                "stats": {
                    "total": 0
                }
            }
    
    def _save_feedback_data(self):
        """
        Save feedback data to file.
        """
        try:
            with open(self.feedback_path, 'w') as f:
                json.dump(self.feedback_data, f, indent=2)
            print(f"Saved feedback data to {self.feedback_path}")
        except Exception as e:
            print(f"Error saving feedback data: {str(e)}")
    
    def _load_chat_history(self):
        """
        Load chat history from file.
        
        Returns:
            dict: Chat history data
        """
        if os.path.exists(self.chat_history_path):
            try:
                with open(self.chat_history_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading chat history: {str(e)}")
                # Return default structure
                return {
                    "conversations": [],
                    "stats": {}
                }
        else:
            # Create default structure
            return {
                "conversations": [],
                "stats": {}
            }
    
    def _migrate_chat_history(self):
        """
        Create an empty user-specific chat history file if needed.
        """
        # Skip for albertlu43 account
        if self.user_id == "albertlu43" or self.user_id == "user_albertlu43":
            return
            
        # Check if user-specific chat history already exists
        if os.path.exists(self.chat_history_path):
            print(f"User-specific chat history already exists: {self.chat_history_path}")
            return
        
        # Create an empty chat history file for new users
        try:
            # Initialize with an empty conversations list
            empty_chat_history = {
                "conversations": [],
                "stats": {
                    "total_messages": 0,
                    "user_messages": 0,
                    "clone_messages": 0
                }
            }
            
            # Create user-specific chat history
            with open(self.chat_history_path, 'w') as f:
                json.dump(empty_chat_history, f, indent=2)
            
            print(f"Created empty chat history for new user: {self.chat_history_path}")
        except Exception as e:
            print(f"Error creating chat history: {str(e)}")
    
    def record_feedback(self, message_id, original_message, corrected_message=None, feedback_type="approved", channel=None):
        """
        Record feedback on an AI response.
        
        Args:
            message_id: ID of the message being given feedback on
            original_message: Original AI response
            corrected_message: Corrected version of the response (for 'corrected' feedback type)
            feedback_type: Type of feedback (approved, corrected, rejected)
            channel: Channel the message was sent on (text, email, etc.)
            
        Returns:
            str: ID of the feedback record
        """
        # Generate a unique ID for this feedback record
        feedback_id = str(uuid.uuid4())
        
        # Create feedback record
        feedback_record = {
            "id": feedback_id,
            "message_id": message_id,
            "original_message": original_message,
            "corrected_message": corrected_message if corrected_message else None,
            "feedback_type": feedback_type,
            "channel": channel,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to feedback records
        self.feedback_data["feedback_records"].append(feedback_record)
        
        # Update stats
        self.feedback_data["stats"]["total"] = len(self.feedback_data["feedback_records"])
        
        # Update specific feedback type stats
        if feedback_type in self.feedback_data["stats"]:
            self.feedback_data["stats"][feedback_type] += 1
        else:
            self.feedback_data["stats"][feedback_type] = 1
        
        # Save feedback data
        self._save_feedback_data()
        
        return feedback_id
    
    def get_feedback_stats(self, days_ago=None, user_id=None):
        """
        Get feedback statistics.
        
        Args:
            days_ago: Optional filter for stats from the last X days
            user_id: Optional user ID to get stats for a specific user
            
        Returns:
            dict: Feedback statistics
        """
        # Use provided user_id or fall back to instance's user_id
        target_user_id = user_id if user_id is not None else self.user_id
        
        # Special case for albertlu43 account - use the main feedback file
        if target_user_id == "albertlu43" or target_user_id == "user_albertlu43":
            default_feedback_path = os.path.join(FEEDBACK_DIR, 'default_feedback.json')
            print(f"Using main feedback file for albertlu43: {default_feedback_path}")
            
            if os.path.exists(default_feedback_path):
                try:
                    with open(default_feedback_path, 'r') as f:
                        target_feedback_data = json.load(f)
                except Exception as e:
                    print(f"Error loading default feedback data: {str(e)}")
                    return {"total": 0, "error": f"Failed to load feedback data: {str(e)}"}
            else:
                print(f"Default feedback file not found")
                return {"total": 0}
        else:
            # For other users, use user-specific feedback file
            user_feedback_path = os.path.join(FEEDBACK_DIR, f'{target_user_id}_feedback.json')
            print(f"Using user-specific feedback file: {user_feedback_path}")
            
            if os.path.exists(user_feedback_path):
                try:
                    with open(user_feedback_path, 'r') as f:
                        target_feedback_data = json.load(f)
                except Exception as e:
                    print(f"Error loading user feedback data: {str(e)}")
                    return {"total": 0, "error": f"Failed to load feedback data: {str(e)}"}
            else:
                print(f"User-specific feedback file not found for {target_user_id}")
                return {"total": 0}
        
        if days_ago is None:
            return target_feedback_data["stats"]
        
        # Calculate stats for the specified time period
        cutoff_date = (datetime.now() - timedelta(days=days_ago)).isoformat()
        filtered_records = [r for r in target_feedback_data["feedback_records"] 
                           if r.get('timestamp', '') >= cutoff_date]
        
        # Calculate stats
        stats = {"total": len(filtered_records)}
        for record in filtered_records:
            feedback_type = record.get("feedback_type")
            if feedback_type in stats:
                stats[feedback_type] += 1
            else:
                stats[feedback_type] = 1
        
        return stats
    
    def get_feedback_records(self, feedback_type=None, channel=None, days_ago=None, limit=100):
        """
        Get feedback records with optional filtering.
        
        Args:
            feedback_type: Optional filter for feedback type (approved, corrected, rejected)
            channel: Optional filter for channel (text, email, etc.)
            days_ago: Optional filter for records from the last X days
            limit: Maximum number of records to return
            
        Returns:
            list: Filtered feedback records
        """
        # Get all records from the feedback data
        records = self.feedback_data.get("feedback_records", [])
        
        # Apply date filter if specified
        if days_ago is not None:
            cutoff_date = (datetime.now() - timedelta(days=days_ago)).isoformat()
            records = [r for r in records if r.get('timestamp', '') >= cutoff_date]
        
        # Apply feedback type filter
        if feedback_type:
            records = [r for r in records if r.get('feedback_type') == feedback_type]
        
        # Apply channel filter
        if channel:
            records = [r for r in records if r.get('channel') == channel]
        
        # Sort by timestamp (newest first)
        records = sorted(records, key=lambda r: r.get("timestamp", ""), reverse=True)
        
        # Apply limit
        return records[:limit]
    
    def get_conversations_with_feedback(self, days_ago=None, model_version=None, hide_reviewed=True, channel=None, user_id=None):
        """
        Get messages with feedback information.
        
        Args:
            days_ago: Optional filter for messages from the last X days
            model_version: Optional filter for messages from a specific model version
            hide_reviewed: If True, hide messages that have already received feedback
            channel: Optional filter for messages from a specific channel (email, text, etc.)
            user_id: Optional user ID to get conversations for a specific user
            
        Returns:
            dict: Dictionary containing a flat list of messages with their context and feedback information
        """
        # Use provided user_id or fall back to instance's user_id
        target_user_id = user_id if user_id is not None else self.user_id
        
        # Ensure data isolation between users
        current_user_id = self.user_id
        
        # Special case for albertlu43 account
        if current_user_id == "albertlu43" or current_user_id == "user_albertlu43":
            # albertlu43 account uses the main chat history file
            chat_history_path = DEFAULT_CHAT_HISTORY_PATH
            print(f"Using main chat history file for albertlu43: {chat_history_path}")
        else:
            # Other users should only see their own data
            # Force target_user_id to be the current user to prevent data leakage
            target_user_id = current_user_id
            chat_history_path = os.path.join(CHAT_HISTORY_DIR, f'{target_user_id}_chat_history.json')
            print(f"Using user-specific chat history file: {chat_history_path}")
            
        # If the current user is not albertlu43 but is trying to access albertlu43's data, return empty results
        if (current_user_id != "albertlu43" and current_user_id != "user_albertlu43" and 
            (target_user_id == "albertlu43" or target_user_id == "user_albertlu43")):
            print(f"Preventing access to albertlu43's data from user {current_user_id}")
            return {"messages": [], "stats": {}}
        
        # Load chat history from the appropriate file
        chat_history = {}
        if os.path.exists(chat_history_path):
            try:
                with open(chat_history_path, 'r') as f:
                    chat_history = json.load(f)
            except Exception as e:
                print(f"Error loading chat history: {str(e)}")
                return {"messages": [], "stats": {}}
        else:
            print(f"Chat history file not found: {chat_history_path}")
            return {"messages": [], "stats": {}}
        
        # Create a deep copy to avoid modifying the original
        import copy
        filtered_chat_history = copy.deepcopy(chat_history)
        
        # Get list of message IDs that already have feedback
        reviewed_message_ids = set()
        if hide_reviewed:
            # Special case for albertlu43 account - use the main feedback file
            if target_user_id == "albertlu43" or target_user_id == "user_albertlu43":
                feedback_path = os.path.join(FEEDBACK_DIR, 'default_feedback.json')
            else:
                # For other users, use user-specific feedback file
                feedback_path = os.path.join(FEEDBACK_DIR, f'{target_user_id}_feedback.json')
            
            if os.path.exists(feedback_path):
                try:
                    with open(feedback_path, 'r') as f:
                        feedback_data = json.load(f)
                        for record in feedback_data.get("feedback_records", []):
                            reviewed_message_ids.add(record.get("message_id"))
                except Exception as e:
                    print(f"Error loading feedback data: {str(e)}")
            
            print(f"Found {len(reviewed_message_ids)} messages that already have feedback")
        
        # Apply date filter if specified
        if days_ago is not None:
            # Create cutoff date as midnight X days ago
            now = datetime.now()
            cutoff_date = now - timedelta(days=days_ago)
            print(f"Current time: {now.isoformat()}")
            print(f"Filtering for messages after: {cutoff_date.isoformat()}")
            
            # Create a new list of conversations containing only recent messages
            filtered_conversations = []
            
            for conversation in filtered_chat_history.get("conversations", []):
                # Create a new conversation with only recent messages
                recent_messages = []
                
                for message in conversation.get("messages", []):
                    timestamp_str = message.get("timestamp", "")
                    if not timestamp_str:
                        continue
                    
                    # Try to parse the timestamp
                    try:
                        # Use dateutil parser which handles most formats
                        from dateutil import parser
                        message_date = parser.parse(timestamp_str)
                        
                        # Compare with cutoff date
                        if message_date >= cutoff_date:
                            recent_messages.append(message)
                    except Exception as e:
                        print(f"Error parsing timestamp '{timestamp_str}': {e}")
                
                # If we found recent messages, add this conversation to the filtered list
                if recent_messages:
                    # Create a copy of the conversation with only recent messages
                    filtered_conversation = copy.deepcopy(conversation)
                    filtered_conversation["messages"] = recent_messages
                    filtered_conversations.append(filtered_conversation)
            
            filtered_chat_history["conversations"] = filtered_conversations
        
        # If model_version is specified, filter messages to only include those from that version or newer
        if model_version and model_version != "all":
            print(f"Filtering for model version: {model_version}")
            
            # Filter messages by model version and hide reviewed messages if requested
            for conversation in filtered_chat_history.get("conversations", []):
                filtered_messages = []
                for message in conversation.get("messages", []):
                    # Keep user messages for context
                    if message.get("sender") == "user":
                        filtered_messages.append(message)
                    # Only keep clone messages that haven't been reviewed (if hide_reviewed is True)
                    elif message.get("sender") == "clone":
                        # Apply model version filter if specified
                        if model_version != "all":
                            # Special case for fine-tuned model
                            if model_version == "v1.4" and message.get("model_version", "").startswith("ft:gpt-4o-mini"):
                                pass  # Allow this message through
                            elif message.get("model_version") != model_version:
                                continue
                        if not hide_reviewed or message.get("id") not in reviewed_message_ids:
                            filtered_messages.append(message)
                
                # Update messages in conversation
                conversation["messages"] = filtered_messages
            
            # Remove conversations with no clone messages after filtering
            filtered_chat_history["conversations"] = [
                conv for conv in filtered_chat_history.get("conversations", [])
                if any(msg.get("sender") == "clone" for msg in conv.get("messages", []))
            ]
        
        # Apply channel filter if specified
        if channel and channel != "all":
            print(f"Filtering for channel: {channel}")
            filtered_conversations = []
            
            for conversation in filtered_chat_history.get("conversations", []):
                # Create a new conversation with only messages from the specified channel
                filtered_messages = []
                has_matching_channel = False
                
                for message in conversation.get("messages", []):
                    # Include the message if it's from the specified channel or if it's a user message (for context)
                    if message.get("channel") == channel:
                        has_matching_channel = True
                        filtered_messages.append(message)
                    elif message.get("sender") == "user" and any(m.get("channel") == channel for m in conversation.get("messages", [])):
                        # Only include user messages if there's at least one message from the specified channel in this conversation
                        filtered_messages.append(message)
                
                # Only include conversations that have at least one message from the specified channel
                if has_matching_channel and filtered_messages:
                    # Create a copy of the conversation with only filtered messages
                    filtered_conversation = copy.deepcopy(conversation)
                    filtered_conversation["messages"] = filtered_messages
                    filtered_conversations.append(filtered_conversation)
            
            filtered_chat_history["conversations"] = filtered_conversations
        
        # Convert conversations to a flat list of messages with context
        flat_messages = []
        for conversation in filtered_chat_history.get("conversations", []):
            messages = conversation.get("messages", [])
            for i, message in enumerate(messages):
                if message.get("sender") == "clone":
                    # Find the preceding user message for context
                    context_message = None
                    for j in range(i-1, -1, -1):
                        if j >= 0 and messages[j].get("sender") == "user":
                            context_message = messages[j]
                            break
                    
                    # Add the message with its context
                    flat_message = copy.deepcopy(message)
                    if context_message:
                        flat_message["context"] = context_message
                    flat_messages.append(flat_message)
        
        # Sort all messages by timestamp (newest first)
        flat_messages.sort(key=lambda msg: msg.get("timestamp", ""), reverse=True)
        
        # Return flat messages instead of conversations
        return {"messages": flat_messages, "stats": filtered_chat_history.get("stats", {})}
    
    def get_learning_examples(self, days_ago=None, limit=100):
        """
        Get learning examples from corrected responses.
        
        Args:
            days_ago: Optional filter for examples from the last X days
            limit: Maximum number of examples to return
            
        Returns:
            list: Learning examples with original and corrected text
        """
        # Load feedback records
        feedback_records = self.feedback_data.get("feedback_records", [])
        
        # Filter for corrected messages
        corrected_records = [r for r in feedback_records if r.get("feedback_type") == "corrected"]
        
        # Apply date filter if specified
        if days_ago is not None:
            cutoff_date = datetime.now() - timedelta(days=days_ago)
            cutoff_timestamp = cutoff_date.isoformat()
            corrected_records = [r for r in corrected_records if r.get("timestamp", "") >= cutoff_timestamp]
        
        # Sort by timestamp (newest first)
        corrected_records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Limit the number of examples
        corrected_records = corrected_records[:limit]
        
        # Format examples
        examples = []
        for record in corrected_records:
            examples.append({
                "original": record.get("original_message", ""),
                "corrected": record.get("corrected_message", ""),
                "timestamp": record.get("timestamp", ""),
                "channel": record.get("channel", "text")
            })
        
        return examples
        
    def generate_training_examples(self, min_confidence=0.8, user_id=None):
        """
        Generate training examples from corrected messages.
        
        Args:
            min_confidence: Minimum confidence score for examples
            user_id: Optional user ID to generate examples for a specific user
            
        Returns:
            list: Training examples
        """
        # Use provided user_id or fall back to instance's user_id
        target_user_id = user_id if user_id is not None else self.user_id
        
        # Get feedback records for the target user
        if target_user_id == self.user_id:
            # Use instance's feedback data
            feedback_records = self.feedback_data.get("feedback_records", [])
        else:
            # Load feedback data for the target user
            target_feedback_path = os.path.join(FEEDBACK_DIR, f'{target_user_id}_feedback.json')
            if os.path.exists(target_feedback_path):
                try:
                    with open(target_feedback_path, 'r') as f:
                        target_feedback_data = json.load(f)
                        feedback_records = target_feedback_data.get("feedback_records", [])
                except Exception as e:
                    print(f"Error loading target user feedback data: {str(e)}")
                    feedback_records = []
            else:
                print(f"Target user feedback file not found: {target_feedback_path}")
                feedback_records = []
        
        # Filter for corrected messages
        corrected_records = [r for r in feedback_records if r.get("feedback_type") == "corrected"]
        
        # Generate training examples
        training_examples = []
        for record in corrected_records:
            original_message = record.get("original_message", "")
            corrected_message = record.get("corrected_message", "")
            
            if not original_message or not corrected_message:
                continue
            
            # Calculate similarity score
            similarity = self._calculate_text_similarity(original_message, corrected_message)
            
            # Only include examples with high similarity
            if similarity >= min_confidence:
                training_examples.append({
                    "original": original_message,
                    "corrected": corrected_message,
                    "confidence": similarity
                })
        
        return training_examples
    
    def _calculate_text_similarity(self, text1, text2):
        """
        Calculate similarity between two text strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            float: Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0
            
        # Normalize texts
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Use difflib to calculate similarity
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def _calculate_jaccard_similarity(self, set1, set2):
        """
        Calculate Jaccard similarity between two sets.
        
        Args:
            set1: First set
            set2: Second set
            
        Returns:
            float: Similarity score between 0 and 1
        """
        if not set1 or not set2:
            return 0
            
        # Calculate intersection and union
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0

# Example usage
if __name__ == "__main__":
    # Initialize feedback system
    feedback_system = FeedbackSystem()
    
    # Record feedback
    feedback_id = feedback_system.record_feedback(
        message_id="test_message_id",
        original_message="Hello, how are you?",
        corrected_message="Hey there! How's it going?",
        feedback_type="corrected",
        channel="text"
    )
    
    print(f"Recorded feedback with ID: {feedback_id}")
    
    # Get feedback stats
    stats = feedback_system.get_feedback_stats()
    print(f"Feedback stats: {stats}")
