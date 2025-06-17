#!/usr/bin/env python3

"""
Retrieval Augmented Generation (RAG) System for AI Clone

This module provides a RAG system that enhances response generation by retrieving
relevant examples from the user's message history. It uses a vector database to
store and retrieve message embeddings for semantic similarity search, combined with
stateful memory to maintain context across sessions.
"""

import os
import json
import uuid
import re
from datetime import datetime
from collections import Counter
from .state_management import AgentState

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RAG_DIR = os.path.join(DATA_DIR, 'rag')

# Ensure directories exist
os.makedirs(RAG_DIR, exist_ok=True)

class MessageRAG:
    """
    Simple RAG system for enhancing AI clone responses with message history context.
    
    This class handles the storage and retrieval of messages using simple text-based
    similarity to provide contextually relevant examples for response generation.
    """
    
    def __init__(self, user_id="default", clear_existing=False):
        """
        Initialize the RAG system.
        
        Args:
            user_id: Identifier for the user (for future multi-user support)
            clear_existing: If True, clear existing messages in the database
        """
        self.user_id = user_id
        self.messages = []
        self.db_path = os.path.join(RAG_DIR, f'{user_id}_message_db.json')
        self.state_manager = AgentState(user_id=user_id)
        self.initialize_database(clear_existing)
    
    def initialize_database(self, clear_existing=False):
        """
        Initialize or load existing message database.
        
        Args:
            clear_existing: If True, clear existing messages in the database
        """
        # Initialize empty collections first as fallbacks
        self.messages = []
        
        if os.path.exists(self.db_path) and not clear_existing:
            # Load existing database
            try:
                with open(self.db_path, 'r') as f:
                    stored_data = json.load(f)
                    self.messages = stored_data.get('messages', [])
                print(f"Loaded {len(self.messages)} messages from database")
            except Exception as e:
                print(f"Error loading RAG database: {str(e)}")
        elif os.path.exists(self.db_path) and clear_existing:
            print("Clearing existing RAG database for fresh initialization")
    
    def add_message_batch(self, message_data):
        """
        Process and add a batch of messages to the database.
        
        Args:
            message_data: List of message dictionaries with text, context, etc.
        """
        if not message_data:
            return
            
        new_messages = []
        
        for msg in message_data:
            try:
                # Create context by combining previous and current message
                context = msg.get('previous_message', '')
                text = msg.get('text', '')
                
                # Skip empty messages
                if not text or not text.strip():
                    continue
                    
                # Store message without embedding
                message_entry = {
                    'text': text,
                    'context': context,
                    'sender': msg.get('sender', ''),
                    'timestamp': msg.get('timestamp', datetime.now().isoformat()),
                    'keywords': self._extract_keywords(text),
                    'model_version': msg.get('model_version', None)
                }
                
                new_messages.append(message_entry)
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                continue
        
        # Add to storage
        self.messages.extend(new_messages)
        
        # Save to disk
        try:
            self.save_database()
            print(f"Added {len(new_messages)} messages to RAG database")
        except Exception as e:
            print(f"Error saving database: {str(e)}")
    
    def _extract_keywords(self, text):
        """
        Extract keywords from text for simple matching.
        
        Args:
            text: The text to extract keywords from
            
        Returns:
            list: Keywords extracted from the text
        """
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into words and filter out common words and short words
        words = text.split()
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
                      'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'like',
                      'through', 'over', 'before', 'after', 'between', 'from', 'up',
                      'down', 'of', 'this', 'that', 'these', 'those', 'it', 'they',
                      'i', 'you', 'he', 'she', 'we', 'my', 'your', 'his', 'her', 'our'}
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return keywords
    
    def _analyze_message_intent(self, message):
        """
        Analyze the intent of a message.
        
        Args:
            message: The message to analyze
            
        Returns:
            dict: Intent analysis results
        """
        # Default intent analysis
        intent = {
            'is_question': False,
            'is_greeting': False,
            'is_personal': False,
            'is_request': False,
            'is_opinion': False,
            'emotional_tone': 'neutral'
        }
        
        # Convert to lowercase for analysis
        message_lower = message.lower()
        
        # Check if it's a question
        if '?' in message or any(q in message_lower for q in ['what', 'how', 'when', 'where', 'who', 'why', 'which']):
            intent['is_question'] = True
            
        # Check if it's a greeting
        if any(greeting in message_lower.split() for greeting in ['hi', 'hello', 'hey', 'morning', 'afternoon', 'evening']):
            intent['is_greeting'] = True
            
        # Check if it's a request
        if any(req in message_lower for req in ['can you', 'could you', 'please', 'help', 'show me', 'tell me']):
            intent['is_request'] = True
            
        # Check if it's personal (contains personal pronouns)
        if any(pronoun in message_lower.split() for pronoun in ['i', 'me', 'my', 'mine', 'myself', 'you', 'your']):
            intent['is_personal'] = True
            
        # Check if it's an opinion
        if any(opinion in message_lower for opinion in ['think', 'believe', 'feel', 'opinion', 'view', 'perspective']):
            intent['is_opinion'] = True
            
        # Simple emotional tone detection
        positive_words = ['good', 'great', 'awesome', 'excellent', 'happy', 'love', 'like', 'thanks']
        negative_words = ['bad', 'terrible', 'awful', 'sad', 'hate', 'dislike', 'angry', 'upset']
        
        positive_count = sum(1 for word in positive_words if word in message_lower.split())
        negative_count = sum(1 for word in negative_words if word in message_lower.split())
        
        if positive_count > negative_count:
            intent['emotional_tone'] = 'positive'
        elif negative_count > positive_count:
            intent['emotional_tone'] = 'negative'
            
        return intent
    
    def _extract_topics(self, text):
        """
        Extract topics from text.
        
        Args:
            text: The text to extract topics from
            
        Returns:
            list: Topics extracted from the text
        """
        # Define topic categories and their associated keywords
        topic_categories = {
            'work': ['work', 'job', 'career', 'company', 'startup', 'business', 'office', 'project', 'team', 'meeting'],
            'technology': ['tech', 'ai', 'code', 'programming', 'software', 'app', 'computer', 'algorithm', 'data', 'website'],
            'personal': ['family', 'friend', 'relationship', 'feel', 'life', 'hobby', 'weekend', 'home', 'personal', 'health'],
            'education': ['school', 'college', 'university', 'class', 'course', 'learn', 'study', 'education', 'student', 'teacher'],
            'entertainment': ['movie', 'show', 'music', 'game', 'book', 'play', 'watch', 'read', 'listen', 'entertainment'],
            'travel': ['travel', 'trip', 'vacation', 'visit', 'country', 'city', 'place', 'flight', 'hotel', 'destination']
        }
        
        # Convert to lowercase for analysis
        text_lower = text.lower()
        
        # Identify topics based on keyword presence
        detected_topics = []
        for topic, keywords in topic_categories.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_topics.append(topic)
                
        return detected_topics
    
    def retrieve_similar_messages(self, query, conversation_history=None, conversation_id=None, top_k=5, channel=None):
        """
        Retrieve messages similar to the query with enhanced context awareness.
        
        Args:
            query: The user's message to find similar examples for
            conversation_history: Recent conversation history for context
            conversation_id: Identifier for the conversation (for stateful context)
            top_k: Number of similar messages to retrieve
            channel: Optional channel filter (text, email, etc.) to filter results by channel
            
        Returns:
            list: Similar messages with their context
        """
        try:
            # Check if we have messages to search
            if not self.messages:
                print("No messages in repository to search")
                return []
                
            # Generate a conversation ID if not provided
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
                
            # Try to get stateful context from previous sessions
            stateful_context = None
            try:
                if conversation_id:
                    stateful_context = self.state_manager.get_conversation_context(conversation_id)
            except Exception as e:
                print(f"Error getting conversation context: {str(e)}")
            
            # Analyze query intent and topics
            query_intent = self._analyze_message_intent(query)
            query_topics = self._extract_topics(query)
            
            # Extract conversation context
            conversation_topics = []
            conversation_context = ""
            conversation_facts = {}  # Store key facts from the conversation
            
            if conversation_history and len(conversation_history) > 0:
                # Get the last few messages for context
                recent_messages = conversation_history[-5:]  # Increased from 3 to 5 for better context
                conversation_context = " ".join([msg.get('text', '') for msg in recent_messages if msg.get('text')])
                
                # Extract topics from conversation history
                for msg in recent_messages:
                    msg_text = msg.get('text', '')
                    if msg_text:
                        conversation_topics.extend(self._extract_topics(msg_text))
                
                # Extract key facts from conversation (like opinions on specific topics)
                self._extract_conversation_facts(recent_messages, conversation_facts)
            
            # Add stateful context if available
            if stateful_context and 'recent_topics' in stateful_context:
                conversation_context = f"{stateful_context['recent_topics']} {conversation_context}"
                
            # Combine query with context for keyword extraction
            query_with_context = f"{conversation_context} {query}" if conversation_context else query
            query_keywords = self._extract_keywords(query_with_context)
            
            # Calculate multi-factor similarity scores
            scored_messages = []
            for msg in self.messages:
                # Skip messages that don't match the channel filter if provided
                if channel and msg.get('metadata', {}).get('channel') != channel:
                    continue
                    
                # Initialize score components
                keyword_similarity = 0
                intent_match_score = 0
                topic_match_score = 0
                context_match_score = 0
                fact_consistency_score = 0  # New score component for fact consistency
                
                # 1. Keyword similarity (base similarity)
                msg_keywords = msg.get('keywords', [])
                if not msg_keywords:
                    msg_keywords = self._extract_keywords(msg.get('text', ''))
                
                # Count matching keywords
                matches = sum(1 for keyword in query_keywords if keyword in msg_keywords)
                total_keywords = len(set(query_keywords + msg_keywords))
                keyword_similarity = matches / max(total_keywords, 1)  # Avoid division by zero
                
                # 2. Intent matching
                msg_intent = self._analyze_message_intent(msg.get('context', ''))
                
                # Boost score if intents match (e.g., question-answer pairs)
                if query_intent['is_question'] and '?' in msg.get('context', ''):
                    intent_match_score = 0.2  # Significant boost for question-answer pairs
                elif query_intent['is_greeting'] and msg_intent['is_greeting']:
                    intent_match_score = 0.15  # Boost for greeting-greeting pairs
                elif query_intent['is_opinion'] and msg_intent['is_opinion']:
                    intent_match_score = 0.1  # Boost for opinion-opinion pairs
                
                # Match emotional tone
                if query_intent['emotional_tone'] == msg_intent['emotional_tone']:
                    intent_match_score += 0.1
                
                # 3. Topic matching
                msg_topics = self._extract_topics(msg.get('text', ''))
                
                # Calculate topic overlap
                if query_topics and msg_topics:
                    common_topics = set(query_topics).intersection(set(msg_topics))
                    topic_match_score = len(common_topics) * 0.15  # Each matching topic adds to score
                
                # Also consider conversation context topics
                if conversation_topics and msg_topics:
                    common_context_topics = set(conversation_topics).intersection(set(msg_topics))
                    context_match_score = len(common_context_topics) * 0.1
                
                # 4. Check fact consistency with conversation history
                if conversation_facts:
                    # Check if the message is consistent with established facts
                    fact_consistency_score = self._check_fact_consistency(msg, conversation_facts)
                
                # 5. Calculate final composite score
                # Base weight on keyword similarity but boost with other factors
                final_score = keyword_similarity + intent_match_score + topic_match_score + context_match_score + fact_consistency_score
                
                # IMPROVED: Apply stricter filtering to reduce hallucinations
                # Only include messages that have a minimum relevance score
                min_score_threshold = 0.25  # Increased from implicit 0
                
                # IMPROVED: Penalize responses that are too generic or could apply to many contexts
                generic_phrases = ['yes', 'no', 'maybe', 'ok', 'sure', 'thanks', 'hello', 'hi', 'hey']
                if msg.get('text', '').lower().strip() in generic_phrases:
                    final_score *= 0.5  # Reduce score for very generic responses
                
                # IMPROVED: Ensure context continuity by checking if this message makes sense given recent history
                if conversation_history and len(conversation_history) > 1:
                    last_user_msg = next((m.get('text', '') for m in reversed(conversation_history) 
                                         if m.get('sender') == 'user'), '')
                    if last_user_msg and not self._is_contextually_relevant(msg.get('text', ''), last_user_msg):
                        final_score *= 0.7  # Reduce score for contextually irrelevant messages
                
                if final_score > min_score_threshold:
                    # Create a copy of the message with score components
                    msg_copy = msg.copy()
                    msg_copy['similarity'] = final_score
                    msg_copy['score_components'] = {
                        'keyword_similarity': keyword_similarity,
                        'intent_match': intent_match_score,
                        'topic_match': topic_match_score,
                        'context_match': context_match_score,
                        'fact_consistency': fact_consistency_score
                    }
                    scored_messages.append(msg_copy)
            
            # Sort by final score (descending)
            scored_messages.sort(key=lambda x: x['similarity'], reverse=True)
            
            # IMPROVED: Apply diversity filtering to avoid repetitive examples
            diverse_results = self._select_diverse_examples(scored_messages, top_k)
            
            # Get top results
            results = []
            for msg in diverse_results:
                # Add debug info about why this message was selected
                score_components = msg.get('score_components', {})
                score_explanation = f"Score: {msg['similarity']:.2f} (Keywords: {score_components.get('keyword_similarity', 0):.2f}, " + \
                                  f"Intent: {score_components.get('intent_match', 0):.2f}, " + \
                                  f"Topic: {score_components.get('topic_match', 0):.2f}, " + \
                                  f"Context: {score_components.get('context_match', 0):.2f}, " + \
                                  f"Fact Consistency: {score_components.get('fact_consistency', 0):.2f})"
                
                print(f"Selected message: '{msg.get('text', '')[:50]}...' - {score_explanation}")
                results.append(msg)
                
                # Add to agent memory if it's a high-quality match
                try:
                    if msg['similarity'] > 0.3:  # Threshold for "good" matches
                        self.state_manager.add_memory(
                            memory_type="similar_message",
                            content=json.dumps({
                                "query": query,
                                "similar_message": msg['text'],
                                "context": msg.get('context', ''),
                                "match_quality": score_explanation
                            }),
                            importance=msg['similarity']  # Use final score as importance score
                        )
                except Exception as e:
                    print(f"Error adding to agent memory: {str(e)}")
                    
            # IMPROVED: Filter to ensure we have quality examples
            quality_results = [msg for msg in results if msg['similarity'] > 0.3]
            if quality_results:
                print(f"After filtering, {len(quality_results)} quality examples remain")
                return quality_results
            else:
                # If we don't have quality examples, return a limited number to avoid noise
                print(f"No high-quality examples found, returning limited set")
                return results[:min(3, len(results))]
                
        except Exception as e:
            print(f"Error in retrieve_similar_messages: {str(e)}")
            return []
            
    def _is_contextually_relevant(self, message, previous_message):
        """
        Check if a message is contextually relevant to the previous message.
        
        Args:
            message: The message to check
            previous_message: The previous message in the conversation
            
        Returns:
            bool: True if the message is contextually relevant
        """
        # Simple heuristic: Check if there are any common non-stopwords
        message_words = set(self._extract_keywords(message))
        prev_words = set(self._extract_keywords(previous_message))
        
        # If there's word overlap, it's more likely to be contextually relevant
        common_words = message_words.intersection(prev_words)
        if len(common_words) > 0:
            return True
            
        # Check for question-answer patterns
        if '?' in previous_message and len(message.split()) > 2:
            return True
            
        # Check for greeting-response patterns
        greetings = ['hi', 'hello', 'hey', 'morning', 'afternoon', 'evening']
        if any(g in previous_message.lower() for g in greetings) and len(message) < 20:
            return True
            
        return False
        
    def _select_diverse_examples(self, scored_messages, top_k):
        """
        Select a diverse set of examples from the scored messages.
        
        Args:
            scored_messages: List of scored messages
            top_k: Number of examples to select
            
        Returns:
            list: Diverse set of examples
        """
        if len(scored_messages) <= top_k:
            return scored_messages
            
        # Always include the top result
        results = [scored_messages[0]]
        remaining = scored_messages[1:]
        
        # Select diverse examples based on content similarity
        while len(results) < top_k and remaining:
            # Find the message that's most different from what we've already selected
            most_diverse = None
            max_diversity = -1
            
            for candidate in remaining:
                # Calculate average similarity to already selected messages
                avg_similarity = 0
                for selected in results:
                    # Simple word overlap similarity
                    candidate_words = set(self._extract_keywords(candidate.get('text', '')))
                    selected_words = set(self._extract_keywords(selected.get('text', '')))
                    
                    if not candidate_words or not selected_words:
                        continue
                        
                    overlap = len(candidate_words.intersection(selected_words))
                    similarity = overlap / max(len(candidate_words.union(selected_words)), 1)
                    avg_similarity += similarity
                    
                if results:
                    avg_similarity /= len(results)
                    
                # Diversity is inverse of similarity
                diversity = 1 - avg_similarity
                
                # Weight by the original score to ensure we still get good matches
                weighted_diversity = diversity * candidate['similarity']
                
                if weighted_diversity > max_diversity:
                    max_diversity = weighted_diversity
                    most_diverse = candidate
            
            if most_diverse:
                results.append(most_diverse)
                remaining.remove(most_diverse)
            else:
                break
                
        return results
    
    def _extract_conversation_facts(self, messages, facts_dict):
        """
        Extract key facts from conversation history to maintain consistency.
        
        Args:
            messages: List of messages in the conversation
            facts_dict: Dictionary to store extracted facts
            
        Returns:
            Updated facts_dict with extracted facts
        """
        # Define patterns for extracting opinions and facts
        opinion_patterns = [
            (r'(?:is|are|was|were)\s+(?:the\s+)?(?:best|worst|greatest|goat)', 'opinion_superlative'),
            (r'(?:better|worse)\s+than', 'opinion_comparative'),
            (r'(?:favorite|prefer|like|love|hate)', 'opinion_preference'),
            (r'(?:think|believe|feel)\s+that', 'opinion_belief')
        ]
        
        # Process each message to extract facts
        for i, msg in enumerate(messages):
            if msg.get('sender') == 'clone':  # Only consider clone's statements as facts
                text = msg.get('text', '').lower()
                
                # Look for opinions
                for pattern, fact_type in opinion_patterns:
                    if re.search(pattern, text):
                        # Try to identify the topic
                        if 'nba' in text or 'basketball' in text:
                            if 'goat' in text or 'greatest' in text:
                                # Extract who was mentioned as the GOAT
                                if 'lebron' in text:
                                    facts_dict['nba_goat'] = 'lebron'
                                elif 'jordan' in text or 'mj' in text:
                                    facts_dict['nba_goat'] = 'jordan'
                                elif 'kobe' in text:
                                    facts_dict['nba_goat'] = 'kobe'
                        
                        # Extract team preferences
                        team_mentions = re.findall(r'(lakers|celtics|warriors|bulls|heat|nuggets|mavericks|mavs|pelicans)', text)
                        if team_mentions:
                            for team in team_mentions:
                                if 'win' in text or 'champion' in text or 'title' in text:
                                    facts_dict['nba_champion_pick'] = team
                
                # Extract specific facts about trades or players
                if 'trade' in text:
                    player_mentions = re.findall(r'(lebron|jordan|kobe|luka|zion|durant|curry)', text)
                    team_mentions = re.findall(r'(lakers|celtics|warriors|bulls|heat|nuggets|mavericks|mavs|pelicans)', text)
                    
                    if player_mentions and team_mentions:
                        facts_dict['trade_info'] = {
                            'player': player_mentions[0],
                            'team': team_mentions[0]
                        }
        
        return facts_dict
    
    def _check_fact_consistency(self, message, conversation_facts):
        """
        Check if a message is consistent with established facts from the conversation.
        
        Args:
            message: The message to check
            conversation_facts: Dictionary of facts extracted from conversation
            
        Returns:
            float: Consistency score (higher is better)
        """
        consistency_score = 0
        text = message.get('text', '').lower()
        
        # Check NBA GOAT consistency
        if 'nba_goat' in conversation_facts:
            goat = conversation_facts['nba_goat']
            if 'goat' in text or 'greatest' in text:
                if goat == 'lebron' and 'lebron' in text:
                    consistency_score += 0.5
                elif goat == 'jordan' and ('jordan' in text or 'mj' in text):
                    consistency_score += 0.5
                elif goat == 'kobe' and 'kobe' in text:
                    consistency_score += 0.5
                # Penalize inconsistency
                elif goat == 'lebron' and ('jordan' in text or 'mj' in text or 'kobe' in text):
                    consistency_score -= 0.3
                elif goat == 'jordan' and ('lebron' in text or 'kobe' in text):
                    consistency_score -= 0.3
                elif goat == 'kobe' and ('lebron' in text or 'jordan' in text or 'mj' in text):
                    consistency_score -= 0.3
        
        # Check team preferences consistency
        if 'nba_champion_pick' in conversation_facts:
            team = conversation_facts['nba_champion_pick']
            if 'win' in text or 'champion' in text or 'title' in text:
                if team in text:
                    consistency_score += 0.3
        
        # Check trade information consistency
        if 'trade_info' in conversation_facts:
            trade = conversation_facts['trade_info']
            if 'trade' in text and trade['player'] in text:
                if trade['team'] in text:
                    consistency_score += 0.3
        
        return consistency_score
    
    def save_database(self):
        """
        Save the database to disk.
        """
        try:
            with open(self.db_path, 'w') as f:
                json.dump({'messages': self.messages}, f)
        except Exception as e:
            print(f"Error saving RAG database: {str(e)}")
    
    def add_from_chat_history(self, chat_history_path, days=30, extract_identity=True, min_date=None, model_version=None):
        """
        Add messages from chat history to the RAG database.
        
        Args:
            chat_history_path: Path to the chat history JSON file
            days: Number of days of history to include
            extract_identity: Whether to extract identity information for the state manager
            min_date: Minimum date for messages to include (ISO format string)
            model_version: Only include messages from this model version or newer
        """
        if not os.path.exists(chat_history_path):
            print(f"Chat history file not found: {chat_history_path}")
            return
            
        try:
            with open(chat_history_path, 'r') as f:
                chat_data = json.load(f)
                
            # Process conversations
            message_batch = []
            
            # Identity extraction patterns (simple approach)
            identity_patterns = [
                "i am", "i'm", "my name", "about me", "about myself",
                "i like", "i enjoy", "i work", "i live", "i study"
            ]
            
            # Convert min_date to datetime object if provided
            min_datetime = None
            if min_date:
                try:
                    min_datetime = datetime.fromisoformat(min_date.replace('Z', '+00:00'))
                    print(f"Filtering messages after {min_datetime}")
                except (ValueError, TypeError) as e:
                    print(f"Invalid min_date format: {e}")
            
            for conversation in chat_data.get('conversations', []):
                messages = conversation.get('messages', [])
                conversation_id = conversation.get('id', str(uuid.uuid4()))
                
                # Check if this conversation has a model_version and if it meets our criteria
                conversation_model = conversation.get('model_version', None)
                if model_version and conversation_model and conversation_model < model_version:
                    print(f"Skipping conversation with older model version: {conversation_model}")
                    continue
                
                # Process each message with its context
                for i in range(1, len(messages)):
                    current_msg = messages[i]
                    prev_msg = messages[i-1]
                    
                    # Skip messages before min_date if specified
                    if min_datetime and 'timestamp' in current_msg:
                        try:
                            msg_datetime = datetime.fromisoformat(current_msg['timestamp'].replace('Z', '+00:00'))
                            if msg_datetime < min_datetime:
                                continue
                        except (ValueError, TypeError):
                            # If we can't parse the timestamp, include the message by default
                            pass
                    
                    # Skip messages that are not marked for RAG
                    if 'add_to_rag' in current_msg and not current_msg.get('add_to_rag', False):
                        print(f"Skipping message not marked for RAG: {current_msg.get('text', '')[:30]}...")
                        continue
                    
                    # Extract identity information if enabled
                    if extract_identity and current_msg.get('sender') == 'user':
                        text = current_msg.get('text', '').lower()
                        
                        # Check for identity-related content
                        if any(pattern in text for pattern in identity_patterns):
                            # Extract a simple fact (this could be enhanced with NLP)
                            self.state_manager.add_identity_fact(
                                fact=current_msg.get('text', ''),
                                confidence=0.7,  # Medium confidence since this is a simple extraction
                                source='chat_history'
                            )
                    
                    # Only include substantive user messages with context
                    if current_msg.get('sender') == 'user':
                        # Filter out simple test messages like repeated hellos
                        user_message = current_msg.get('text', '').lower().strip()
                        simple_greetings = ['hi', 'hello', 'hey', 'hi there', 'hello there', 'hey there', 'morning', 'afternoon', 'evening']
                        
                        # Skip if it's just a simple greeting or very short message
                        is_simple_greeting = user_message in simple_greetings or (len(user_message) < 10 and any(greeting in user_message for greeting in simple_greetings))
                        
                        if not is_simple_greeting and len(user_message.split()) > 2:
                            message_batch.append({
                                'text': current_msg.get('text', ''),
                                'previous_message': prev_msg.get('text', ''),
                                'sender': 'user',
                                'timestamp': current_msg.get('timestamp', ''),
                                'model_version': conversation.get('model_version', None)
                            })
                        else:
                            print(f"Skipping simple test message from chat history: {user_message}")
            
            # Add messages to the database
            self.add_message_batch(message_batch)
            print(f"Added {len(message_batch)} messages from chat history to RAG database")
            
        except Exception as e:
            print(f"Error processing chat history: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Initialize RAG system
    rag = MessageRAG()
    
    # Add messages from chat history
    chat_history_path = os.path.join(DATA_DIR, 'chat_history.json')
    rag.add_from_chat_history(chat_history_path)
    
    # Test retrieval
    similar_messages = rag.retrieve_similar_messages("How's your startup going?")
    print(f"Retrieved {len(similar_messages)} similar messages")
    for msg in similar_messages:
        print(f"Context: {msg['context']}")
        print(f"Response: {msg['text']}")
        print("---")
