"""
ChromaDB Manager - UPDATED WITH RETRIEVAL METHOD
Manages ChromaDB collections for temporary vector storage

FIXED: Added get_conversation_history() method for context retrieval
"""

import numpy as np

# --- PATCH for NumPy 2.x backward compatibility ---
if not hasattr(np, "float_"):
    np.float_ = np.float64
if not hasattr(np, "int_"):
    np.int_ = np.int64
if not hasattr(np, "uint"):
    np.uint = np.uint64
# --------------------------------------------------

import chromadb
from datetime import datetime
import json
from typing import List, Dict, Optional


class ChromaDBManager:
    """
    Manages ChromaDB collections for temporary vector storage
    FIXED: Now includes get_conversation_history() for context retrieval
    """

    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB client (compatible with Chroma v0.5+)
        """
        # ✅ Use PersistentClient (new API)
        self.client = chromadb.PersistentClient(path=persist_directory)

        # Create or get collections
        self.conversation_collection = self._get_or_create_collection(
            "conversations", "Store conversation history for context retrieval"
        )

        self.user_preferences_collection = self._get_or_create_collection(
            "user_preferences", "Store user preferences and behavior patterns"
        )

        self.menu_collection = self._get_or_create_collection(
            "menu_items", "Store menu items for semantic search"
        )

        print(f"✅ Initialized ChromaDB at: {persist_directory}")

    def _get_or_create_collection(self, name: str, description: str):
        """Get existing collection or create new one"""
        try:
            return self.client.get_collection(name=name)
        except Exception:
            return self.client.create_collection(
                name=name, metadata={"description": description}
            )

    # ============================================
    # CONVERSATION HISTORY STORAGE & RETRIEVAL
    # ============================================

    def store_conversation(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        agent_response: str,
        intent: str,
        metadata: Optional[Dict] = None,
    ):
        """Store a conversation turn in ChromaDB"""
        doc_id = f"user_{user_id}_session_{session_id}_{datetime.now().timestamp()}"

        conversation_text = f"User: {user_message}\nAssistant: {agent_response}"

        meta = {
            "user_id": str(user_id),
            "session_id": session_id,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "agent_response": agent_response,
        }

        if metadata:
            meta.update(metadata)

        self.conversation_collection.add(
            documents=[conversation_text],
            metadatas=[meta],
            ids=[doc_id],
        )

        print(f"✓ Stored conversation: {doc_id}")

    def get_conversation_history(
        self, user_id: int, session_id: str, limit: int = 5
    ) -> List[Dict]:
        """
        Retrieve recent conversation history for context
        
        Args:
            user_id: User ID
            session_id: Session ID
            limit: Number of recent messages to retrieve
            
        Returns:
            List of conversation messages in format:
            [{"role": "user/assistant", "content": "...", "intent": "..."}]
        """
        try:
            # Query conversation collection with filters
            results = self.conversation_collection.get(
                where={
                    "$and": [
                        {"user_id": {"$eq": str(user_id)}},
                        {"session_id": {"$eq": session_id}}
                    ]
                },
                include=["documents", "metadatas"],
                limit=limit
            )

            if not results or not results.get('documents') or len(results['documents']) == 0:
                return []

            # Format history
            history = []
            for i, doc in enumerate(results['documents']):
                metadata = results['metadatas'][i] if results.get('metadatas') else {}

                # Add user message
                history.append({
                    "role": "user",
                    "content": metadata.get("user_message", doc),
                    "intent": metadata.get("intent", "unknown"),
                    "timestamp": metadata.get("timestamp", "")
                })

                # Add assistant response
                history.append({
                    "role": "assistant",
                    "content": metadata.get("agent_response", ""),
                    "intent": metadata.get("intent", "unknown"),
                    "timestamp": metadata.get("timestamp", "")
                })

            print(f"✓ Retrieved {len(history)} conversation turns from history")
            return history[-limit*2:]  # Return last limit messages

        except Exception as e:
            print(f"⚠️ ChromaDB history retrieval failed: {e}")
            return []

    def get_relevant_conversations(
        self, query: str, user_id: Optional[int] = None, n_results: int = 5
    ) -> List[Dict]:
        """Retrieve relevant past conversations via similarity search"""
        where_clause = {"user_id": str(user_id)} if user_id else None

        results = self.conversation_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause,
        )

        conversations = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                conversations.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results.get("distances", [[None]])[0][i],
                })

        return conversations

    # ============================================
    # USER PREFERENCES STORAGE & RETRIEVAL
    # ============================================

    def store_user_preference(
        self,
        user_id: int,
        preference_type: str,
        preference_value: str,
        confidence: float = 1.0,
        context: Optional[str] = None,
    ):
        """Store a user preference"""
        doc_id = (
            f"pref_user_{user_id}_{preference_type}_{preference_value}_"
            f"{datetime.now().timestamp()}"
        )

        doc_text = f"{preference_type}: {preference_value}"
        if context:
            doc_text += f" (from: {context})"

        metadata = {
            "user_id": str(user_id),
            "preference_type": preference_type,
            "preference_value": preference_value,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "context": context or "",
        }

        self.user_preferences_collection.add(
            documents=[doc_text],
            metadatas=[metadata],
            ids=[doc_id],
        )

        print(f"✓ Stored preference: {preference_type}={preference_value} for user {user_id}")

    def get_user_preferences(
        self, user_id: int, preference_type: Optional[str] = None
    ) -> List[Dict]:
        """Retrieve stored user preferences"""
        where_clause = {"user_id": str(user_id)}
        if preference_type:
            where_clause["preference_type"] = preference_type

        results = self.user_preferences_collection.get(
            where=where_clause, include=["documents", "metadatas"]
        )

        preferences = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"]):
                preferences.append(
                    {"text": doc, "metadata": results["metadatas"][i]}
                )

        return preferences

    # ============================================
    # MENU ITEMS STORAGE (FOR SEMANTIC SEARCH)
    # ============================================

    def index_menu_items(self, menu_items: List[Dict]):
        """Index menu items for semantic search"""
        documents, metadatas, ids = [], [], []

        for item in menu_items:
            tags_str = ", ".join(item.get("tags", []))
            doc_text = (
                f"{item['name']} - {item.get('description', '')} "
                f"({item.get('cuisine_type', '')}). Tags: {tags_str}"
            )

            documents.append(doc_text)
            metadatas.append({
                "item_id": str(item["item_id"]),
                "name": item["name"],
                "restaurant_id": str(item.get("restaurant_id", "")),
                "restaurant_name": item.get("restaurant_name", ""),
                "price": float(item.get("price", 0)),
                "cuisine_type": item.get("cuisine_type", ""),
                "tags": json.dumps(item.get("tags", [])),
            })
            ids.append(f"item_{item['item_id']}")

        self.menu_collection.add(
            documents=documents, metadatas=metadatas, ids=ids
        )

        print(f"✓ Indexed {len(menu_items)} menu items")

    def search_menu_items(
        self,
        query: str,
        cuisine_filter: Optional[str] = None,
        max_price: Optional[float] = None,
        tags_filter: Optional[List[str]] = None,
        n_results: int = 10,
    ) -> List[Dict]:
        """Semantic search for menu items"""
        where_clause = {}
        if cuisine_filter:
            where_clause["cuisine_type"] = cuisine_filter

        results = self.menu_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause if where_clause else None,
        )

        items = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]

                try:
                    tags = json.loads(metadata.get("tags", "[]"))
                except Exception:
                    tags = []

                if max_price and float(metadata.get("price", 0)) > max_price:
                    continue

                if tags_filter and not any(tag in tags for tag in tags_filter):
                    continue

                items.append({
                    "item_id": int(metadata["item_id"]),
                    "name": metadata["name"],
                    "restaurant_name": metadata.get("restaurant_name", ""),
                    "price": float(metadata["price"]),
                    "cuisine_type": metadata.get("cuisine_type", ""),
                    "tags": tags,
                    "relevance_score": 1 - results.get("distances", [[1]])[0][i],
                    "text": doc,
                })

        return items

    # ============================================
    # UTILITIES
    # ============================================

    def clear_session_data(self, session_id: str):
        """Clear all data for a session"""
        print(f"⚠️ Manual session cleanup needed for session {session_id}")

    def get_collection_stats(self):
        """Get statistics about all collections"""
        return {
            "conversations": self.conversation_collection.count(),
            "user_preferences": self.user_preferences_collection.count(),
            "menu_items": self.menu_collection.count(),
        }

    def reset_all_collections(self):
        """⚠️ Delete all collections (for testing only)"""
        try:
            self.client.delete_collection("conversations")
            self.client.delete_collection("user_preferences")
            self.client.delete_collection("menu_items")
            print("✓ All collections deleted")
        except Exception as e:
            print(f"Error deleting collections: {e}")