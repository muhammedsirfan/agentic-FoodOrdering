"""
REINFORCEMENT LEARNING MODULE - FIXED STATE PERSISTENCE

FIXES:
- Proper JSON serialization of tuple keys (user_id, item_id)
- Correct state loading and restoration
- Verbose logging for debugging
- Proper type conversions
"""

import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict
import sys

sys.path.insert(0, '.')


class SimpleRLLoop:
    """
    Simple Reinforcement Learning loop with FIXED persistence
    
    Learns from:
    1. What items user selected from recommendations
    2. Did they complete order (reward signal)
    3. User feedback (ratings, preferences)
    4. Item popularity patterns
    """
    
    def __init__(self):
        """Initialize RL components"""
        # Q-values: {(user_id, item_id): reward_value}
        self.q_values = defaultdict(float)
        
        # State-action tracking
        self.state_action_history = []
        
        # User preference weights: {user_id: {item_id: weight}}
        self.user_preferences = defaultdict(lambda: defaultdict(float))
        
        # Item popularity: {item_id: popularity_score}
        self.item_popularity = defaultdict(float)
        
        # Learning rate and discount factor
        self.alpha = 0.1  # Learning rate
        self.gamma = 0.9  # Discount factor
        self.epsilon = 0.1  # Exploration rate
        
        print("RL Loop initialized")
    
    def record_recommendation_shown(self, user_id: int, recommendations: List[Dict]) -> str:
        """Record that recommendations were shown"""
        state_id = str(uuid.uuid4())
        
        state_action = {
            'state_id': state_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'action': 'show_recommendations',
            'recommendations': [
                {'item_id': r.get('item_id'), 'name': r.get('name')}
                for r in recommendations[:5]
            ],
            'reward': None,
            'completed': False
        }
        
        self.state_action_history.append(state_action)
        return state_id
    
    def record_item_selected(self, user_id: int, item_id: int, state_id: Optional[str] = None) -> None:
        """Record which item user selected"""
        # UPDATE Q-value
        old_q = self.q_values[(user_id, item_id)]
        self.q_values[(user_id, item_id)] += self.alpha
        new_q = self.q_values[(user_id, item_id)]
        
        # Increase item popularity
        self.item_popularity[item_id] += 0.1
        
        # Update user preference
        self.user_preferences[user_id][item_id] += 0.2
        
        # LOG FOR DEBUGGING
        print(f"  RL: User {user_id} selected item {item_id}")
        print(f"        Q-value: {old_q:.3f} → {new_q:.3f}")
    
    def record_order_completed(self, user_id: int, order_data: Dict) -> Dict:
        """
        Record successful order - HIGH REWARD signal
        """
        reward = 1.0  # Base reward for completion
        
        # Bonus rewards
        items_count = len(order_data.get('items', []))
        order_total = float(order_data.get('total', 0))
        
        # Reward based on order size
        if order_total > 500:
            reward += 0.5  # High-value order
        
        if items_count > 3:
            reward += 0.3  # Multiple items
        
        print(f"\nRL LEARNING - ORDER COMPLETED")
        
        # CRITICAL: Update Q-values for all items in order
        for item in order_data.get('items', []):
            item_id = item.get('item_id')
            quantity = item.get('quantity', 1)
            
            # Get old values for logging
            old_q = self.q_values.get((user_id, item_id), 0)
            old_pref = self.user_preferences[user_id].get(item_id, 0)
            
            # Strong positive reward for selected item
            self.q_values[(user_id, item_id)] += reward
            new_q = self.q_values[(user_id, item_id)]
            
            # Update popularity
            self.item_popularity[item_id] += quantity * 0.5
            
            # Update user preference
            self.user_preferences[user_id][item_id] += reward
            new_pref = self.user_preferences[user_id][item_id]
            
            # LOG EACH ITEM UPDATE
            print(f"   Item {item_id}:")
            print(f"      Q-value: {old_q:.3f} → {new_q:.3f}")
            print(f"      Preference: {old_pref:.3f} → {new_pref:.3f}")
        
        print(f"   Total Reward: {reward:.2f}")
        print(f"   Order Total: ₹{order_total}")
        print(f"   Items: {items_count}")
        
        return {
            'user_id': user_id,
            'reward': reward,
            'items_count': items_count,
            'order_total': order_total,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_personalized_recommendations(self, user_id: int, 
                                        available_items: List[Dict]) -> List[Dict]:
        """Get recommendations based on learned preferences"""
        import random
        
        user_prefs = self.user_preferences.get(user_id, {})
        
        scored_items = []
        for item in available_items:
            item_id = item.get('item_id')
            
            # Base score from Q-value
            q_score = self.q_values.get((user_id, item_id), 0)
            
            # Score from user preference
            pref_score = user_prefs.get(item_id, 0)
            
            # Score from popularity
            pop_score = self.item_popularity.get(item_id, 0) * 0.1
            
            # Combined score (exploitation)
            total_score = (q_score * 0.4) + (pref_score * 0.4) + (pop_score * 0.2)
            
            scored_items.append({
                **item,
                'rl_score': total_score,
                'q_value': q_score,
                'preference': pref_score
            })
        
        # Epsilon-greedy
        if random.random() < self.epsilon and len(scored_items) > 3:
            best_items = sorted(scored_items, key=lambda x: x['rl_score'], reverse=True)[:3]
            random_items = random.sample(scored_items, min(2, len(scored_items)))
            final_items = best_items + random_items
        else:
            final_items = sorted(scored_items, key=lambda x: x['rl_score'], reverse=True)
        
        return final_items[:5]
    
    def record_user_feedback(self, user_id: int, item_id: int, feedback_score: float) -> None:
        """Record explicit user feedback"""
        if feedback_score > 1:
            feedback_score = feedback_score / 5.0
        
        self.q_values[(user_id, item_id)] += (feedback_score * self.alpha)
        self.user_preferences[user_id][item_id] += feedback_score
        
        print(f"\nRL Feedback:")
        print(f"   User {user_id} rated item {item_id}: {feedback_score:.2f}/1.0")
    
    def get_state_summary(self, user_id: int) -> Dict:
        """Get learning summary for a user"""
        user_prefs = self.user_preferences.get(user_id, {})
        
        top_items = sorted(
            user_prefs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'user_id': user_id,
            'learned_items': len(user_prefs),
            'top_items': [
                {'item_id': item_id, 'preference_score': score}
                for item_id, score in top_items
            ],
            'total_interactions': len([
                h for h in self.state_action_history
                if h['user_id'] == user_id
            ])
        }
    
    def save_state(self, filepath: str = "rl_state.json") -> None:
    
        try:
            # FIX: Convert tuple keys to strings for JSON
            q_values_serialized = {}
            for (user_id, item_id), value in self.q_values.items():
                key = f"{user_id}_{item_id}"  # Convert tuple to string key
                q_values_serialized[key] = float(value)
            
            # FIX: Properly serialize nested dicts
            user_preferences_serialized = {}
            for user_id, prefs in self.user_preferences.items():
                user_key = str(user_id)
                user_preferences_serialized[user_key] = {
                    str(item_id): float(value)
                    for item_id, value in prefs.items()
                }
            
            item_popularity_serialized = {
                str(k): float(v) 
                for k, v in self.item_popularity.items()
            }
            
            state = {
                'q_values': q_values_serialized,
                'user_preferences': user_preferences_serialized,
                'item_popularity': item_popularity_serialized,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
            
            print(f" RL state saved to {filepath}")
            print(f"   Q-values: {len(q_values_serialized)}")
            print(f"   Users: {len(user_preferences_serialized)}")
            print(f"   Items: {len(item_popularity_serialized)}")
            
        except Exception as e:
            print(f" Failed to save RL state: {e}")
            import traceback
            traceback.print_exc()
    
    def load_state(self, filepath: str = "rl_state.json") -> None:
        """
         FIXED: Properly deserialize RL state from JSON
        """
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            print(f" Loading RL state from {filepath}...")
            
            # FIX: Restore Q-values from string keys
            self.q_values = defaultdict(float)
            for key, value in state.get('q_values', {}).items():
                try:
                    user_id, item_id = map(int, key.split('_'))
                    self.q_values[(user_id, item_id)] = float(value)
                except Exception as e:
                    print(f"   ⚠️ Error parsing Q-value key '{key}': {e}")
            
            # FIX: Restore user preferences
            self.user_preferences = defaultdict(lambda: defaultdict(float))
            for user_id_str, prefs in state.get('user_preferences', {}).items():
                try:
                    user_id = int(user_id_str)
                    for item_id_str, value in prefs.items():
                        item_id = int(item_id_str)
                        self.user_preferences[user_id][item_id] = float(value)
                except Exception as e:
                    print(f"   ⚠️ Error parsing preferences for user '{user_id_str}': {e}")
            
            # FIX: Restore item popularity
            self.item_popularity = defaultdict(float)
            for item_id_str, value in state.get('item_popularity', {}).items():
                try:
                    item_id = int(item_id_str)
                    self.item_popularity[item_id] = float(value)
                except Exception as e:
                    print(f"  Error parsing popularity for item '{item_id_str}': {e}")
            
            print(f" RL state loaded successfully!")
            print(f"   Q-values: {len(self.q_values)}")
            print(f"   Users: {len(self.user_preferences)}")
            print(f"   Items: {len(self.item_popularity)}")
            
        except FileNotFoundError:
            print(f"RL state file not found ({filepath}) - starting fresh")
        except json.JSONDecodeError as e:
            print(f"Failed to parse RL state JSON: {e}")
        except Exception as e:
            print(f"Failed to load RL state: {e}")
            import traceback
            traceback.print_exc()
