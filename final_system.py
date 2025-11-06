import json
import uuid
import re
from agents.conversation_agent import ConversationAgent
from agents.recommendation_agent import RecommendationAgent
from agents.order_handler_agent import OrderHandlerAgent
from database.db_manager import DatabaseManager
from vector_store.chroma_manager import ChromaDBManager
from cart_manager import CartManager


class FinalAgenticSystem:
    """
    COMPLETE WORKING AGENTIC SYSTEM
    """

    def __init__(self, user_id: int):
        print("\n" + "="*80)
        print("🤖 INITIALIZING AGENTIC FOOD ORDERING SYSTEM")
        print("="*80)

        self.user_id = user_id
        self.db = DatabaseManager()
        self.chroma = ChromaDBManager()
        self.cart = CartManager(self.db)
        self.session_id = str(uuid.uuid4())

        self.conversation_agent = ConversationAgent()
        self.recommendation_agent = RecommendationAgent()
        self.order_handler_agent = OrderHandlerAgent()

        self.user_data = self._load_user_data()

        print(f"✅ System ready for {self.user_data.get('name', 'Guest')}")
        print(f"Session: {self.session_id[:8]}...")
        print("="*80 + "\n")

    def _load_user_data(self):
        """Load user from database"""
        user = self.db.get_user_by_id(self.user_id)

        if not user:
            return {
                'user_id': self.user_id,
                'name': 'Guest',
                'dietary_restrictions': [],
                'address': 'Unknown',
                'preferences': {}
            }

        prefs = json.loads(user['preferences']) if isinstance(user['preferences'], str) else user['preferences']
        dietary = json.loads(user['dietary_restrictions']) if isinstance(user['dietary_restrictions'], str) else user['dietary_restrictions']

        return {
            'user_id': self.user_id,
            'name': user['name'],
            'email': user.get('email', ''),
            'address': user.get('address', 'Unknown'),
            'preferences': prefs or {},
            'dietary_restrictions': dietary or []
        }

    def _intelligent_filter_by_query(self, user_query: str, all_items):
        """
        🟢 FIXED: Smart filtering that PRIORITIZES matching items
        """
        query_lower = user_query.lower()
        
        # Extract important keywords
        keywords = [w for w in query_lower.split() if len(w) > 2]
        
        # Score each item
        scored_items = []
        
        for item in all_items:
            score = 0
            item_name = item['name'].lower()
            item_cuisine = item.get('cuisine_type', '').lower()
            item_desc = item.get('description', '').lower()
            item_text = f"{item_name} {item_cuisine} {item_desc}"
            
            # 🟢 EXACT MATCH - HIGHEST PRIORITY
            if 'biryani' in query_lower and 'biryani' in item_name:
                score += 100  # BOOST BIRYANI!
            
            if 'paneer' in query_lower and 'paneer' in item_name:
                score += 100
                
            if 'butter' in query_lower and 'butter' in item_name:
                score += 100
                
            if 'naan' in query_lower and 'naan' in item_name:
                score += 100
            
            for keyword in keywords:
                if keyword in item_text:
                    score += 5
            
            if 'spicy' in query_lower and 'spicy' in item_text:
                score += 10
            
            if 'vegetarian' in query_lower and 'vegetarian' in item_text:
                score += 10
            
            if 'non-vegetarian' in query_lower and 'non-vegetarian' in item_text:
                score += 10
            
            scored_items.append((score, item))
        
        # Sort by score DESCENDING
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        # Return only high-scoring items first
        high_score_items = [item for score, item in scored_items if score > 0]
        
        if high_score_items:
            return high_score_items[:5]
        else:
            # Fallback: return top 5 anyway
            return [item for score, item in scored_items[:5]]

    def _extract_item_name_and_qty(self, user_input: str):
       
        text_lower = user_input.lower()
        
        # Remove "add" keyword
        text_clean = text_lower.replace('add', '').replace('to cart', '').strip()
        
        # Extract quantity if present
        quantity = 1
        qty_match = re.search(r'\d+', text_clean)
        if qty_match:
            quantity = int(qty_match.group())
            # Remove quantity from text
            text_clean = re.sub(r'\d+', '', text_clean).strip()
        
        # What remains is item name
        item_name = text_clean.strip()
        
        return item_name, quantity

    def _find_item_by_name(self, item_name: str):
        """
        🟢 FIXED: Find item in database by name (fuzzy matching)
        """
        if not item_name or len(item_name) < 2:
            return None
        
        try:
            query = """
            SELECT m.item_id, m.name, m.price, m.restaurant_id, r.name as restaurant_name
            FROM menu_items m
            JOIN restaurants r ON m.restaurant_id = r.restaurant_id
            WHERE m.availability = TRUE
            AND LOWER(m.name) LIKE %s
            LIMIT 1
            """
            
            # Try exact match first
            results = self.db.execute_query(query, (f"%{item_name}%",))
            
            if results:
                return results[0]
            
            return None
        except Exception as e:
            print(f"Search error: {e}")
            return None

    def process_message(self, user_input: str):
        """
        Main processing - ALL BUGS FIXED
        """
        print(f"\n{'-'*80}")
        print(f"YOU: {user_input}")
        print(f"{'-'*80}\n")

        # Retrieve conversation history
        print("🔍 [Context] Retrieving conversation history...")
        conversation_history = self.chroma.get_conversation_history(
            user_id=self.user_id,
            session_id=self.session_id,
            limit=5
        )

        if conversation_history:
            print(f"✓ Retrieved {len(conversation_history)} conversation turns from history")
        else:
            print("   No previous context (first message)")

        # 🟢 FIXED: Better intent detection
        print("🤖 [Agent 1] Understanding your request...")
        
        # Check if it's an add to cart request FIRST (before agent classification)
        user_input_lower = user_input.lower()
        if any(keyword in user_input_lower for keyword in ['add', 'add to cart', 'i want to add']):
            intent = 'order_placement'
            extracted = {}
        else:
            conv_result = self.conversation_agent.process(
                user_input=user_input,
                user_preferences=self.user_data.get('preferences', {}),
                conversation_history=conversation_history
            )
            intent = conv_result.get('intent', 'unknown')
            extracted = conv_result.get('extracted_info', {})

        print(f" Intent: {intent}")

        # ============================================
        # RECOMMENDATION REQUEST or MENU BROWSE
        # ============================================
        if intent in ['recommendation_request', 'menu_browse']:
            print("🍽️  [Agent 2] Finding menu items with SMART FILTERING...")

            try:
                all_items = self.db.search_menu_items(
                    search_term="",
                    cuisine_filter=None,
                    dietary_restrictions=[]
                )

                if all_items:
                    menu_items = self._intelligent_filter_by_query(user_input, all_items)
                else:
                    menu_items = []

                print(f" ✓ Retrieved {len(menu_items)} relevant items")

            except Exception as e:
                print(f"Database error: {e}")
                menu_items = []

            if not menu_items:
                print("No items found")
                return {
                    'status': 'error',
                    'message': '❌ No matching items found.',
                    'recommendations': [],
                    'intent': intent
                }

            # Format recommendations
            recommendations = []
            for idx, item in enumerate(menu_items[:5], 1):
                tags = json.loads(item['tags']) if isinstance(item['tags'], str) else item['tags']

                recommendations.append({
                    'rank': idx,
                    'item_id': item['item_id'],
                    'item_name': item['name'],
                    'restaurant_name': item.get('restaurant_name', 'Unknown'),
                    'restaurant_id': item.get('restaurant_id', 1),
                    'price': float(item['price']),
                    'cuisine_type': item.get('cuisine_type', 'Unknown'),
                    'description': item.get('description', ''),
                    'tags': tags or []
                })

            conv_result = self.conversation_agent.process(
                user_input=user_input,
                user_preferences=self.user_data.get('preferences', {}),
                conversation_history=conversation_history
            )
            conv_message = conv_result.get('conversational_response', '')

            try:
                self.chroma.store_conversation(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    user_message=user_input,
                    agent_response=conv_message,
                    intent=intent
                )
            except Exception as e:
                print(f"ChromaDB: {e}")

            return {
                'status': 'success',
                'message': conv_message,
                'recommendations': recommendations,
                'intent': intent
            }

        elif intent == 'order_placement':
            print("🛒 [Cart] Adding item...")

            item_name, quantity = self._extract_item_name_and_qty(user_input)
            
            print(f"   Extracted: item='{item_name}', qty={quantity}")

            if not item_name:
                return {
                    'status': 'error',
                    'message': f"Please specify an item to add. Example: 'add biryani rice' or 'add 2 paneer tikka'",
                    'intent': intent
                }

            item = self._find_item_by_name(item_name)

            if not item:
                return {
                    'status': 'error',
                    'message': f"Item '{item_name}' not found. Please choose from available menu.",
                    'intent': intent
                }

            print(f"   Found item: {item['name']}")
            
            cart_result = self.cart.add_item(item['item_id'], quantity)

            if cart_result['success']:
                cart_state = cart_result['cart']

                try:
                    self.chroma.store_conversation(
                        user_id=self.user_id,
                        session_id=self.session_id,
                        user_message=user_input,
                        agent_response=f"Added {quantity}x {item['name']} to cart",
                        intent=intent
                    )
                except Exception as e:
                    print(f"ChromaDB: {e}")

                return {
                    'status': 'success',
                    'message': f"Added {quantity}x {item['name']} to cart!",
                    'cart': cart_state,
                    'intent': intent
                }
            else:
                return {
                    'status': 'error',
                    'message': cart_result['message'],
                    'intent': intent
                }

        # ============================================
        # OTHER INTENTS
        # ============================================
        else:
            conv_result = self.conversation_agent.process(
                user_input=user_input,
                user_preferences=self.user_data.get('preferences', {}),
                conversation_history=conversation_history
            )
            
            try:
                self.chroma.store_conversation(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    user_message=user_input,
                    agent_response=conv_result.get('conversational_response', ''),
                    intent=intent
                )
            except Exception as e:
                print(f"ChromaDB: {e}")

            return {
                'status': 'success',
                'message': conv_result.get('conversational_response', 'How can I help?'),
                'intent': intent
            }

    def get_cart(self):
        """Get cart state"""
        return self.cart.get_cart_state()

    def checkout(self):
        """Place order"""
        print(f"\n[Checkout] Processing order...")

        cart_state = self.cart.get_cart_state()

        if not cart_state['items']:
            print(f"   Cart is empty")
            return {'success': False, 'message': 'Cart is empty'}

        if not cart_state['minimum_order_met']:
            print(f"   Minimum order not met")
            return {
                'success': False,
                'message': f"Minimum order ₹{cart_state['minimum_order']} not met"
            }

        print(f"   Items: {len(cart_state['items'])}")
        print(f"   Total: ₹{cart_state['total']}")

        delivery_address = self.db.get_user_address(self.user_id)

        order_items_with_names = []
        for item in cart_state['items']:
            order_items_with_names.append({
                'name': item.get('item_name', 'Unknown Item'),
                'quantity': item.get('quantity', 1),
                'price': float(item.get('price', 0)),
                'item_id': item.get('item_id')
            })

        order_id = self.db.create_order(
            user_id=self.user_id,
            restaurant_id=cart_state.get('restaurant_id', 1),
            order_items=order_items_with_names,
            total_amount=float(cart_state['total']),
            delivery_address=delivery_address
        )

        if order_id:
            print(f"   Order placed successfully!")

            try:
                self.chroma.store_conversation(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    user_message="Checkout completed",
                    agent_response=f"Order #{order_id} placed for ₹{float(cart_state['total'])}",
                    intent='checkout'
                )
            except Exception as e:
                print(f"ChromaDB: {e}")

            return {
                'success': True,
                'order_id': order_id,
                'total': float(cart_state['total']),
                'delivery_address': delivery_address,
                'message': f"🎉 Order placed successfully to {delivery_address}!"
            }

        else:
            print(f"   Checkout failed")
            return {
                'success': False,
                'message': 'Failed to create order. Check database logs.'
            }

    def cleanup(self):
        """Cleanup"""
        print("\n🧹 Cleaning up...")
        self.db.disconnect()
        print("Cleanup complete")
