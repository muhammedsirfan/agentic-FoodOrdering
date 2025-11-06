"""
Cart Manager - Handle add to cart with database updates
"""

from database.db_manager import DatabaseManager
from typing import List, Dict, Optional

class CartManager:
    """Manages shopping cart operations"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.cart_items = []
        self.restaurant_id = None
    
    def add_item(self, item_id: int, quantity: int = 1) -> Dict:
        """
        Add item to cart
        
        Args:
            item_id: Menu item ID
            quantity: Quantity to add
        
        Returns:
            Cart state dict
        """
        
        # Get item from database
        query = """
            SELECT m.item_id, m.name, m.price, m.restaurant_id,
                   r.name as restaurant_name, r.minimum_order, r.delivery_fee
            FROM menu_items m
            JOIN restaurants r ON m.restaurant_id = r.restaurant_id
            WHERE m.item_id = %s AND m.availability = TRUE
        """
        
        results = self.db.execute_query(query, (item_id,))
        
        if not results:
            return {
                'success': False,
                'message': 'Item not found or unavailable'
            }
        
        item = results[0]
        
        # Check restaurant consistency
        if self.restaurant_id is None:
            self.restaurant_id = item['restaurant_id']
        elif self.restaurant_id != item['restaurant_id']:
            return {
                'success': False,
                'message': f"Cannot mix items from different restaurants. Current cart is from {self.get_restaurant_name()}",
                'cart': self.get_cart_state()
            }
        
        # Check if item already in cart
        existing_item = next((x for x in self.cart_items if x['item_id'] == item_id), None)
        
        if existing_item:
            existing_item['quantity'] += quantity
            existing_item['total_price'] = existing_item['quantity'] * existing_item['unit_price']
        else:
            self.cart_items.append({
                'item_id': item['item_id'],
                'item_name': item['name'],
                'restaurant_id': item['restaurant_id'],
                'restaurant_name': item['restaurant_name'],
                'quantity': quantity,
                'unit_price': float(item['price']),
                'total_price': float(item['price']) * quantity
            })
        
        cart_state = self.get_cart_state()
        
        return {
            'success': True,
            'message': f"Added {quantity}x {item['name']} to cart!",
            'cart': cart_state
        }
    
    def get_cart_state(self) -> Dict:
        """Get current cart state"""
        
        if not self.cart_items:
            return {
                'items': [],
                'subtotal': 0,
                'delivery_fee': 0,
                'total': 0,
                'restaurant_id': None,
                'restaurant_name': None,
                'minimum_order_met': False
            }
        
        # Get restaurant details
        restaurant = self.db.get_restaurant_by_id(self.restaurant_id)
        
        subtotal = sum(item['total_price'] for item in self.cart_items)
        delivery_fee = float(restaurant['delivery_fee']) if restaurant else 0
        minimum_order = float(restaurant['minimum_order']) if restaurant else 0
        
        return {
            'items': self.cart_items,
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'total': subtotal + delivery_fee,
            'restaurant_id': self.restaurant_id,
            'restaurant_name': restaurant['name'] if restaurant else None,
            'minimum_order': minimum_order,
            'minimum_order_met': subtotal >= minimum_order
        }
    
    def get_restaurant_name(self) -> str:
        """Get current restaurant name"""
        if self.restaurant_id:
            restaurant = self.db.get_restaurant_by_id(self.restaurant_id)
            return restaurant['name'] if restaurant else "Unknown"
        return "No items"
    
    def clear_cart(self):
        """Clear all items from cart"""
        self.cart_items = []
        self.restaurant_id = None
    
    def checkout(self, user_id: int, delivery_address: str, 
                 special_instructions: str = None) -> Dict:
        """
        Create order in database
        
        Returns:
            Order confirmation dict
        """
        cart_state = self.get_cart_state()
        
        if not cart_state['minimum_order_met']:
            return {
                'success': False,
                'message': f"Minimum order of ₹{cart_state['minimum_order']} not met"
            }
        
        # Create order in database
        order_id = self.db.create_order(
            user_id=user_id,
            restaurant_id=self.restaurant_id,
            order_items=self.cart_items,
            total_amount=cart_state['total'],
            delivery_address=delivery_address,
            special_instructions=special_instructions
        )
        
        if order_id:
            # Clear cart after successful order
            self.clear_cart()
            
            return {
                'success': True,
                'order_id': order_id,
                'total': cart_state['total'],
                'message': f"🎉 Order #{order_id} placed successfully! Total: ₹{cart_state['total']}"
            }
        else:
            return {
                'success': False,
                'message': 'Failed to create order. Please try again.'
            }