"""
DB Manager - ENHANCED FOR DELIVERY ADDRESS & ITEM NAMES
Manages PostgreSQL database connections with pooling

NEW FEATURES:
- Fetch user address from database
- Store order items by name instead of item_id
- Enhanced order creation with item names
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
import json
from config import DB_CONFIG


class DatabaseManager:
    """
    Manages PostgreSQL database connections with pooling
    ENHANCED: Now supports getting user address and storing item names
    """

    # Connection pool (shared across instances)
    _connection_pool = None

    def __init__(self):
        """Initialize database connection from pool"""
        self.connection = None
        self._init_pool()
        self.get_connection()

    @classmethod
    def _init_pool(cls):
        """Initialize connection pool (once)"""
        if cls._connection_pool is None:
            try:
                cls._connection_pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    **DB_CONFIG
                )
                print("✓ Connection pool initialized")
            except Exception as e:
                print(f"✗ Failed to initialize connection pool: {e}")
                raise

    def get_connection(self):
        """Get connection from pool with auto-reconnect"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.connection is None or self.connection.closed:
                    self.connection = self._connection_pool.getconn()
                    print("✓ Got connection from pool")
                return
            except Exception as e:
                print(f"⚠️ Connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT query"""
        try:
            self.get_connection()
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results if results else []
        except Exception as e:
            print(f"❌ Query error: {e}")
            return []

    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute INSERT/UPDATE/DELETE"""
        try:
            self.get_connection()
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"❌ Update error: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    # ============================================
    # USER METHODS
    # ============================================

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE user_id = %s"
        results = self.execute_query(query, (user_id,))
        return results[0] if results else None

    # 🟢 NEW METHOD: Get user address for delivery
    def get_user_address(self, user_id: int) -> str:
        """
        Get user delivery address from database
        
        NEW FEATURE: Extract address from user profile
        """
        try:
            query = "SELECT name, address FROM users WHERE user_id = %s"
            results = self.execute_query(query, (user_id,))
            
            if results:
                user = results[0]
                name = user.get('name', 'User')
                address = user.get('address', 'Unknown Address')
                
                # Format: "Name, Address"
                delivery_address = f"{name}, {address}"
                print(f"📍 Delivery Address: {delivery_address}")
                return delivery_address
            else:
                print(f"⚠️ User {user_id} not found")
                return "Unknown Address"
                
        except Exception as e:
            print(f"❌ Error fetching address: {e}")
            return "Unknown Address"

    # ============================================
    # MENU METHODS
    # ============================================

    def search_menu_items(self, search_term: str = "", cuisine_filter: str = None,
                         dietary_restrictions: List[str] = None) -> List[Dict]:
        """Search menu items"""
        query = """
        SELECT m.item_id, m.name, m.price, m.category, m.cuisine_type,
               m.tags, m.availability, m.description, m.restaurant_id,
               r.name as restaurant_name
        FROM menu_items m
        JOIN restaurants r ON m.restaurant_id = r.restaurant_id
        WHERE m.availability = TRUE
        """

        params = []

        if search_term:
            query += " AND LOWER(m.name) LIKE %s"
            params.append(f"%{search_term.lower()}%")

        if cuisine_filter:
            query += " AND m.cuisine_type = %s"
            params.append(cuisine_filter)

        query += " LIMIT 20"

        return self.execute_query(query, tuple(params) if params else None)

    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Get menu item by ID - ENHANCED to return item name"""
        query = """
        SELECT item_id, name, price, restaurant_id
        FROM menu_items
        WHERE item_id = %s AND availability = TRUE
        """
        results = self.execute_query(query, (item_id,))
        return results[0] if results else None

    # ============================================
    # ORDER METHODS - ENHANCED
    # ============================================

    def create_order(self, user_id: int, restaurant_id: int, order_items: List[Dict],
                    total_amount: float, delivery_address: str = None,
                    special_instructions: str = None) -> Optional[int]:
        """
        Create order with ITEM NAMES instead of item_id
        
        ENHANCED FEATURES:
        - Stores item names in order_items
        - Uses delivery_address if provided
        - Returns order_id on success
        """
        try:
            self.get_connection()
            cursor = self.connection.cursor()

            # 🟢 NEW: Format order items with names for storage
            formatted_items = []
            for item in order_items:
                # Item should have: name, quantity, price
                formatted_item = {
                    "name": item.get('name', f"Item {item.get('item_id')}"),
                    "quantity": item.get('quantity', 1),
                    "price": item.get('price', 0),
                    "item_id": item.get('item_id')
                }
                formatted_items.append(formatted_item)

            # Convert to JSON
            order_items_json = json.dumps(formatted_items)

            # Insert order
            query = """
            INSERT INTO orders (user_id, restaurant_id, order_items, total_amount,
                              delivery_address, special_instructions, order_status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING order_id
            """

            cursor.execute(query, (
                user_id,
                restaurant_id,
                order_items_json,
                total_amount,
                delivery_address or "Not specified",
                special_instructions or "",
                "pending"
            ))

            order_id = cursor.fetchone()[0]
            self.connection.commit()
            cursor.close()

            print(f"✓ Created order ID: {order_id}")
            return order_id

        except Exception as e:
            print(f"❌ Order creation failed: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get order details"""
        query = """
        SELECT o.*, u.name, u.address, r.name as restaurant_name
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        JOIN restaurants r ON o.restaurant_id = r.restaurant_id
        WHERE o.order_id = %s
        """
        results = self.execute_query(query, (order_id,))
        return results[0] if results else None

    def get_user_orders(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's order history"""
        query = """
        SELECT * FROM orders
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        return self.execute_query(query, (user_id, limit))

    # ============================================
    # RESTAURANT METHODS
    # ============================================

    def get_restaurant_by_id(self, restaurant_id: int) -> Optional[Dict]:
        """Get restaurant details"""
        query = "SELECT * FROM restaurants WHERE restaurant_id = %s"
        results = self.execute_query(query, (restaurant_id,))
        return results[0] if results else None

    # ============================================
    # INTERACTION LOGGING
    # ============================================

    def log_user_interaction(self, user_id: int, session_id: str, interaction_type: str,
                            query_text: str, intent: str = None):
        """Log user interaction for learning"""
        query = """
        INSERT INTO user_interactions (user_id, session_id, interaction_type, query_text, intent, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        """
        self.execute_update(query, (user_id, session_id, interaction_type, query_text, intent))

    # ============================================
    # CLEANUP
    # ============================================

    def disconnect(self):
        """Close connection and return to pool"""
        try:
            if self.connection and not self.connection.closed:
                self._connection_pool.putconn(self.connection)
                print("✓ Connection returned to pool")
        except Exception as e:
            print(f"⚠️ Disconnect error: {e}")