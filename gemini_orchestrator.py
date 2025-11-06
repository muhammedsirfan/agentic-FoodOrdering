"""
GEMINI ORCHESTRATOR - WITH REINFORCEMENT LEARNING
Same RL integration as LangChain version
"""

import json
import uuid
import re
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

sys.path.insert(0, '.')

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from agents.conversation_agent import ConversationAgent
from agents.recommendation_agent import RecommendationAgent
from agents.order_handler_agent import OrderHandlerAgent
from database.db_manager import DatabaseManager
from vector_store.chroma_manager import ChromaDBManager
from cart_manager import CartManager
from rl_learning_loop import SimpleRLLoop  # ✅ NEW: RL module


class GeminiOrchestrator:
    """
    Gemini orchestrator with RL-enhanced recommendations
    
    RL Features:
    - Learns user preferences from selections
    - High reward signal on order completion
    - Personalized recommendations
    - Explores new items strategically
    """
    
    def __init__(self, user_id: int, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        """Initialize orchestrator with agents AND RL loop"""
        print("\n" + "="*80)
        print("🌟 INITIALIZING GEMINI ORCHESTRATOR WITH RL")
        print("="*80)
        
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai not installed")
        
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.model_name = model
        
        # ✅ Initialize RL Loop
        self.rl_loop = SimpleRLLoop()
        self.rl_loop.load_state()
        
        # Configure Gemini
        api_key = "YOUR API KEY HERE"  # Replace with your actual API key
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found")
        
        genai.configure(api_key=api_key)
        print(f"✓ Gemini API configured")
        
        # Initialize database components
        try:
            self.db = DatabaseManager()
            self.chroma = ChromaDBManager()
            self.cart = CartManager(self.db)
            print("✓ Database components initialized")
        except Exception as e:
            print(f"⚠️ Database warning: {e}")
            self.db = None
            self.chroma = None
            self.cart = None
        
        # Load user data
        self.user_data = self._load_user_data()
        
        # Initialize agents
        print("📍 Initializing agents...")
        self.conversation_agent = ConversationAgent(model_name="mistral:latest")
        self.recommendation_agent = RecommendationAgent(model_name="qwen2.5:latest")
        self.order_handler_agent = OrderHandlerAgent(model_name="llama3:latest")
        print("✓ Agents loaded")
        
        # Gemini model
        self.gemini_model = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "max_output_tokens": 1024,
            }
        )
        
        # Conversation history
        self.conversation_history = []
        self.current_state_id = None  # ✅ Track current RL state
        
        print(f"\n✅ Orchestrator Ready (with RL)")
        print(f"   User: {self.user_data.get('name', 'Guest')}")
        print(f"   Session: {self.session_id[:8]}...")
        print("="*80 + "\n")
    
    def _load_user_data(self) -> Dict:
        """Load user profile"""
        try:
            if not self.db:
                return self._default_user()
            
            user = self.db.get_user_by_id(self.user_id)
            if not user:
                return self._default_user()
            
            prefs = json.loads(user['preferences']) if isinstance(user['preferences'], str) else user['preferences']
            dietary = json.loads(user['dietary_restrictions']) if isinstance(user['dietary_restrictions'], str) else user['dietary_restrictions']
            
            return {
                'user_id': self.user_id,
                'name': user.get('name', 'Guest'),
                'email': user.get('email', ''),
                'address': user.get('address', 'Unknown'),
                'preferences': prefs or {},
                'dietary_restrictions': dietary or []
            }
        except:
            return self._default_user()
    
    def _default_user(self) -> Dict:
        return {
            'user_id': self.user_id,
            'name': 'Guest',
            'email': '',
            'address': 'Unknown',
            'preferences': {},
            'dietary_restrictions': []
        }
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """Process with RL-enhanced recommendations"""
        print(f"\n{'▶'*80}")
        print(f"USER: {user_input}")
        print(f"{'▶'*80}\n")
        
        try:
            # Step 1: Intent
            print("Step 1: Classifying intent...")
            intent_result = self.conversation_agent.process(
                user_input=user_input,
                user_preferences=self.user_data.get('preferences', {}),
                conversation_history=self.conversation_history
            )
            
            intent = intent_result.get('intent', 'general')
            conversational_response = intent_result.get('conversational_response', '')
            print(f"   Intent: {intent}")
            
            final_response = conversational_response
            recommendations = []
            
            # Step 2: RL-ENHANCED recommendations
            if intent in ['recommendation_request', 'browse_menu', 'search_items']:
                print("\nStep 2: Getting RL-optimized recommendations...")
                
                if self.db:
                    all_items = self.db.search_menu_items("", None)
                    
                    # Use RL to personalize
                    rl_recommendations = self.rl_loop.get_personalized_recommendations(
                        self.user_id,
                        all_items
                    )
                    recommendations = rl_recommendations
                    
                    print(f"   Found {len(recommendations)} RL-optimized items")
                    
                    # Record state
                    self.current_state_id = self.rl_loop.record_recommendation_shown(
                        self.user_id,
                        recommendations
                    )
                    
                    rec_text = "\n".join([
                        f"• {r.get('name', 'Unknown')} - ₹{r.get('price', 0)}"
                        for r in recommendations[:5]
                    ])
                    final_response = f"{conversational_response}\n\n{rec_text}"
            
            # Step 3: Process orders
            elif intent in ['order_placement', 'add_to_cart']:
                print("\nStep 3: Processing order...")
                
                item_info = self._parse_order_request(user_input)
                
                if item_info['item_name']:
                    item_id = self._find_item_id(item_info['item_name'])
                    if item_id:
                        # Record with RL
                        self.rl_loop.record_item_selected(self.user_id, item_id, self.current_state_id)
                        
                        cart_result = self.cart.add_item(item_id, item_info['quantity'])
                        if cart_result['success']:
                            cart_state = cart_result['cart']
                            final_response = f"✓ {cart_result['message']}\n\nCart Total: ₹{cart_state['total']}"
                        else:
                            final_response = f"{cart_result['message']}"
                    else:
                        final_response = f"Item not found"
                else:
                    final_response = conversational_response
            
            # Store in history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": final_response})
            
            return {
                "status": "success",
                "message": final_response,
                "recommendations": recommendations,
                "intent": intent,
                "session_id": self.session_id,
                "cart": self.cart.get_cart_state() if self.cart else {}
            }
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Error: {str(e)}",
                "error": str(e)
            }
    
    def _parse_order_request(self, user_input: str) -> Dict[str, Any]:
        """Parse item name and quantity"""
        numbers = re.findall(r'\d+', user_input)
        quantity = int(numbers[0]) if numbers else 1
        
        item_name = user_input.lower()
        for num in numbers:
            item_name = item_name.replace(num, '').strip()
        
        for prefix in ['add', 'i want', 'get me']:
            if item_name.startswith(prefix):
                item_name = item_name[len(prefix):].strip()
        
        return {
            'item_name': item_name.strip() if item_name else None,
            'quantity': quantity
        }
    
    def _find_item_id(self, item_name: str) -> Optional[int]:
        """Find item ID"""
        try:
            if not self.db:
                return None
            items = self.db.search_menu_items(search_term=item_name)
            if items:
                return items[0]['item_id']
        except:
            pass
        
        return None
    
    def _get_past_orders(self) -> List[Dict]:
        """Get past orders"""
        try:
            if not self.db:
                return []
            orders = self.db.get_user_orders(self.user_id, limit=5)
            return [{"order_id": o.get('order_id'), "items": o.get('items', [])} for o in orders] if orders else []
        except:
            return []
    
    def get_cart(self) -> Dict:
        """Get cart state"""
        try:
            if not self.cart:
                return {"error": "Cart not available", "items": [], "total": 0}
            return self.cart.get_cart_state()
        except Exception as e:
            return {"error": str(e), "items": [], "total": 0}
    
    def checkout(self) -> Dict:
        """Checkout with RL reward signal"""
        try:
            if not self.cart or not self.db:
                return {'success': False, 'message': 'Service not available'}
            
            cart_state = self.cart.get_cart_state()
            
            if not cart_state.get('items'):
                return {'success': False, 'message': 'Cart is empty!'}
            
            if not cart_state.get('minimum_order_met'):
                remaining = cart_state.get('minimum_order', 0) - cart_state.get('subtotal', 0)
                return {'success': False, 'message': f'Need ₹{remaining} more'}
            
            delivery_address = self.db.get_user_address(self.user_id)
            
            formatted_items = []
            for item in cart_state.get('items', []):
                formatted_items.append({
                    'item_id': item.get('item_id'),
                    'name': item.get('item_name'),
                    'quantity': item.get('quantity'),
                    'price': item.get('unit_price'),
                    'total_price': item.get('total_price')
                })
            
            order_id = self.db.create_order(
                user_id=self.user_id,
                restaurant_id=cart_state.get('restaurant_id'),
                order_items=formatted_items,
                total_amount=float(cart_state.get('total', 0)),
                delivery_address=delivery_address,
                special_instructions=None
            )
            
            if order_id:
                order_data = {
                    'items': formatted_items,
                    'total': cart_state.get('total', 0)
                }
                reward_info = self.rl_loop.record_order_completed(self.user_id, order_data)
                
                # Save RL state
                self.rl_loop.save_state()
                print("entered rl save")
                
                self.cart.clear_cart()
                
                print(f"\nOrder processed with RL learning!")
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'total': float(cart_state.get('total', 0)),
                    'delivery_address': delivery_address,
                    'rl_reward': reward_info['reward'],
                    'message': f"Order #{order_id} placed!\nRL Learning applied ✓"
                }
            else:
                return {'success': False, 'message': 'Failed to create order'}
                
        except Exception as e:
            print(f"Checkout error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_rl_summary(self) -> Dict:
        """Get RL summary"""
        return self.rl_loop.get_state_summary(self.user_id)
    
    def cleanup(self):
        """Cleanup - save RL state"""
        try:
            self.rl_loop.save_state()  
            if self.db:
                self.db.disconnect()
            print("\nCleanup complete (RL state saved)")
        except Exception as e:
            print(f"Cleanup error: {e}")
