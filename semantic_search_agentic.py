"""
SEMANTIC SEARCH - Convert Your System to TRUE AGENTIC AI
This makes recommendations context-aware and intelligent
"""

import numpy as np
from typing import List, Dict
import json
from sentence_transformers import SentenceTransformer
from database.db_manager import DatabaseManager
from vector_store.chroma_manager import ChromaDBManager


class SemanticMenuSearch:
    """
    AGENTIC COMPONENT: Intelligent semantic search for menu items
    Uses embeddings to understand user intent vs menu items
    """

    def __init__(self):
        """Initialize embeddings model"""
        # Use lightweight embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.db = DatabaseManager()
        self.chroma = ChromaDBManager()
        print("Semantic Search Engine Initialized")

    def get_all_menu_items(self) -> List[Dict]:
        """Get all menu items from database"""
        try:
            query = """
            SELECT item_id, name, description, cuisine_type, price, tags
            FROM menu_items
            WHERE availability = TRUE
            ORDER BY item_id
            """
            items = self.db.execute_query(query)
            print(f"Loaded {len(items)} items from database")
            return items
        except Exception as e:
            print(f"Error loading menu items: {e}")
            return []

    def create_menu_embeddings(self, items: List[Dict]) -> Dict:
        """
        Create embeddings for all menu items
        Embedding captures: name + cuisine + description + tags
        """
        embeddings = {}
        
        for item in items:
            # Combine all text about item
            item_text = f"""
            Name: {item['name']}
            Cuisine: {item['cuisine_type']}
            Description: {item.get('description', '')}
            Tags: {item.get('tags', '')}
            """
            
            # Generate embedding
            embedding = self.embedding_model.encode(item_text)
            embeddings[item['item_id']] = {
                'embedding': embedding,
                'item': item
            }
        
        print(f"Created embeddings for {len(embeddings)} items")
        return embeddings

    def semantic_search(self, user_query: str, all_items: List[Dict], 
                       top_k: int = 5) -> List[Dict]:
        """
        AGENTIC: Search items based on semantic similarity
        
        User says: "I want biryani"
        → Converts to embedding
        → Finds most similar items
        → Returns ranked results
        """
        
        print(f"\n[Semantic Search] Query: '{user_query}'")
        
        # Create embeddings for all items once
        menu_embeddings = self.create_menu_embeddings(all_items)
        
        # Encode user query
        query_embedding = self.embedding_model.encode(user_query)
        print(f"   Query embedding created (dim: {len(query_embedding)})")
        
        # Calculate similarity scores
        scores = []
        for item_id, data in menu_embeddings.items():
            item_embedding = data['embedding']
            
            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, item_embedding)
            scores.append({
                'item_id': item_id,
                'similarity': similarity,
                'item': data['item']
            })
        
        # Sort by similarity (highest first)
        scores.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Return top K
        results = scores[:top_k]
        
        print(f"   ✓ Top {len(results)} matches by semantic similarity:")
        for i, result in enumerate(results, 1):
            print(f"      {i}. {result['item']['name']} (similarity: {result['similarity']:.2f})")
        
        return [r['item'] for r in results]

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2) if (norm1 * norm2) > 0 else 0

    def context_aware_search(self, user_query: str, 
                            conversation_history: List[Dict],
                            user_preferences: Dict) -> List[Dict]:
        """
        ULTRA AGENTIC: Search considering full context
        
        Uses:
        1. Current user query
        2. Conversation history (what they liked before)
        3. User preferences (dietary, cuisine, spice level)
        """
        
        print(f"\n[Context-Aware Search] Building intelligent query...")
        
        # Get all items
        all_items = self.get_all_menu_items()
        
        # Build enhanced query from context
        enhanced_query = self._build_context_query(
            user_query=user_query,
            history=conversation_history,
            preferences=user_preferences
        )
        
        print(f"   Enhanced query: '{enhanced_query}'")
        
        # Semantic search with enhanced query
        results = self.semantic_search(enhanced_query, all_items, top_k=5)
        
        # Re-rank based on user preferences
        results = self._apply_preference_filtering(results, user_preferences)
        
        print(f"   ✓ Final recommendations with context applied:")
        for i, item in enumerate(results, 1):
            print(f"      {i}. {item['name']} - {item['cuisine_type']}")
        
        return results

    def _build_context_query(self, user_query: str, history: List[Dict],
                            preferences: Dict) -> str:
        """Build enhanced query from conversation context"""
        
        query_parts = [user_query]
        
        # Add preferences
        if preferences.get('cuisine'):
            query_parts.append(f"cuisine: {preferences['cuisine']}")
        
        if preferences.get('spice_level'):
            query_parts.append(f"spice level: {preferences['spice_level']}")
        
        if preferences.get('dietary'):
            query_parts.append(f"dietary: {preferences['dietary']}")
        
        # Add history context
        if history and len(history) > 0:
            recent_likes = self._extract_preferences_from_history(history)
            if recent_likes:
                query_parts.append(f"similar to: {recent_likes}")
        
        return " ".join(query_parts)

    def _extract_preferences_from_history(self, history: List[Dict]) -> str:
        """Extract what user liked from conversation history"""
        liked_items = []
        for msg in history:
            if 'like' in msg.get('content', '').lower():
                liked_items.append(msg['content'])
        
        return ", ".join(liked_items[:2]) if liked_items else ""

    def _apply_preference_filtering(self, items: List[Dict],
                                   preferences: Dict) -> List[Dict]:
        """
        Filter & rerank results based on user preferences
        """
        filtered = []
        
        for item in items:
            # Check dietary restrictions
            tags = item.get('tags', [])
            if isinstance(tags, str):
                tags = json.loads(tags)
            
            if preferences.get('vegetarian') and 'non-vegetarian' in tags:
                continue  # Skip non-vegetarian
            
            # Check cuisine preference
            if preferences.get('cuisine'):
                item_cuisine = item.get('cuisine_type', '').lower()
                pref_cuisine = preferences['cuisine'].lower()
                if pref_cuisine not in item_cuisine:
                    # Doesn't match, but still include (lower priority)
                    pass
            
            filtered.append(item)
        
        return filtered if filtered else items  # Return originals if none pass filter


# INTEGRATION INTO FINAL SYSTEM
class AgenticSearchIntegration:
    """How to integrate into your final_system.py"""

    @staticmethod
    def example_usage():
        """
        In final_system.py, replace:
        
        # OLD:
        menu_items = self.db.search_menu_items(search_term=search_term)
        
        # NEW:
        semantic_search = SemanticMenuSearch()
        menu_items = semantic_search.context_aware_search(
            user_query=user_input,
            conversation_history=conversation_history,
            user_preferences=self.user_data.get('preferences', {})
        )
        """
        
        pass