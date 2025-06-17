import json
import os
import time
from datetime import datetime
import sqlite3
from pathlib import Path

class AgentState:
    """Manages persistent state for AI clone agents.
    
    This class provides stateful memory for agents, allowing them to maintain
    context across multiple sessions and conversations.
    """
    
    def __init__(self, user_id="default", db_path=None):
        """Initialize the agent state manager.
        
        Args:
            user_id: Identifier for the user/agent
            db_path: Path to the state database file
        """
        self.user_id = user_id
        
        if db_path is None:
            # Default path in the data directory
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = base_dir / "data"
            os.makedirs(data_dir, exist_ok=True)
            db_path = data_dir / "agent_state.db"
        
        self.db_path = str(db_path)
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the SQLite database for storing agent state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            context TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS identity_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            fact TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
    
    def add_memory(self, memory_type, content, importance=0.5):
        """Add a new memory to the agent's state.
        
        Args:
            memory_type: Type of memory (e.g., 'conversation', 'fact', 'preference')
            content: Content of the memory
            importance: Importance score (0.0 to 1.0) for retrieval priority
            
        Returns:
            ID of the newly created memory
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO agent_memory (user_id, memory_type, content, importance) VALUES (?, ?, ?, ?)",
            (self.user_id, memory_type, content, importance)
        )
        
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return memory_id
    
    def get_memories(self, memory_type=None, limit=10, min_importance=0.0):
        """Retrieve memories from the agent's state.
        
        Args:
            memory_type: Optional filter for memory type
            limit: Maximum number of memories to retrieve
            min_importance: Minimum importance score for retrieved memories
            
        Returns:
            List of memory dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        query = "SELECT * FROM agent_memory WHERE user_id = ? AND importance >= ?"
        params = [self.user_id, min_importance]
        
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
        
        query += " ORDER BY importance DESC, last_accessed DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Update last_accessed timestamp for retrieved memories
        if rows:
            memory_ids = [row['id'] for row in rows]
            placeholders = ",".join(["?" for _ in memory_ids])
            cursor.execute(
                f"UPDATE agent_memory SET last_accessed = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
                memory_ids
            )
            conn.commit()
        
        # Convert rows to dictionaries
        memories = [dict(row) for row in rows]
        
        conn.close()
        return memories
    
    def update_conversation_context(self, conversation_id, context):
        """Update or create conversation context.
        
        Args:
            conversation_id: Identifier for the conversation
            context: JSON-serializable context object
            
        Returns:
            True if successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if context exists
        cursor.execute(
            "SELECT id FROM conversation_context WHERE user_id = ? AND conversation_id = ?",
            (self.user_id, conversation_id)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing context
            cursor.execute(
                "UPDATE conversation_context SET context = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(context), existing[0])
            )
        else:
            # Create new context
            cursor.execute(
                "INSERT INTO conversation_context (user_id, conversation_id, context) VALUES (?, ?, ?)",
                (self.user_id, conversation_id, json.dumps(context))
            )
        
        conn.commit()
        conn.close()
        return True
    
    def get_conversation_context(self, conversation_id):
        """Retrieve conversation context.
        
        Args:
            conversation_id: Identifier for the conversation
            
        Returns:
            Context object or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT context FROM conversation_context WHERE user_id = ? AND conversation_id = ?",
            (self.user_id, conversation_id)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def add_identity_fact(self, fact, confidence=1.0, source=None):
        """Add a fact about the user's identity.
        
        Args:
            fact: The identity fact to store
            confidence: Confidence score (0.0 to 1.0)
            source: Source of the fact (e.g., 'linkedin', 'messages')
            
        Returns:
            ID of the newly created fact
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO identity_facts (user_id, fact, confidence, source) VALUES (?, ?, ?, ?)",
            (self.user_id, fact, confidence, source)
        )
        
        fact_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return fact_id
    
    def get_identity_facts(self, min_confidence=0.5, source=None, limit=20):
        """Retrieve facts about the user's identity.
        
        Args:
            min_confidence: Minimum confidence score for retrieved facts
            source: Optional filter for fact source
            limit: Maximum number of facts to retrieve
            
        Returns:
            List of fact dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM identity_facts WHERE user_id = ? AND confidence >= ?"
        params = [self.user_id, min_confidence]
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        query += " ORDER BY confidence DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        facts = [dict(row) for row in rows]
        
        conn.close()
        return facts
