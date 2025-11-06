"""
RUN - FIXED TO USE RL ORCHESTRATORS
Properly integrates with LangChain or Gemini orchestrators

Key fixes:
- Uses gemini_orchestrator.py or langchain_orchestrator.py
- Calls orchestrator.checkout() which saves RL state
- Proper cart handling with RL learning
"""

import re
import sys
import os

# Import correct orchestrator based on system choice
def get_orchestrator(system_choice: str, user_id: int):
    """Get the correct orchestrator"""
    if system_choice.lower() == "gemini":
        try:
            from gemini_orchestrator import GeminiOrchestrator
            return GeminiOrchestrator(user_id=user_id)
        except Exception as e:
            print(f"Failed to load Gemini Orchestrator: {e}")
            return None
    elif system_choice.lower() == "langchain":
        try:
            from langchain_orchestrator import LangChainOrchestrator
            return LangChainOrchestrator(user_id=user_id)
        except Exception as e:
            print(f"Failed to load LangChain Orchestrator: {e}")
            return None
    else:
        print(f"Unknown system: {system_choice}")
        return None


def display_recommendations(recommendations, has_alternatives=False):
    """Helper function to display menu items - FIXED for RL"""
    if not recommendations:
        print("No items found.")
        return

    if has_alternatives:
        print("SUGGESTED ALTERNATIVES:\n")
    else:
        print("MENU RECOMMENDATIONS:\n")

    for idx, rec in enumerate(recommendations, 1):
        marker = "✨" if rec.get('is_alternative') else "✓"
        
        # ✅ Handle both 'rank' and 'rl_score' fields
        rank = rec.get('rank', idx)
        
        # ✅ Handle both 'item_name' and 'name' fields
        item_name = rec.get('item_name', rec.get('name', 'Unknown'))
        
        # ✅ Handle both 'price' and 'item_price' fields
        price = rec.get('price', rec.get('item_price', 0))
        
        # ✅ Handle restaurant_name field
        restaurant = rec.get('restaurant_name', rec.get('restaurant', 'Unknown'))
        
        # ✅ Handle cuisine_type field
        cuisine = rec.get('cuisine_type', rec.get('cuisine', 'Mixed'))
        
        print(f" {marker} [{rec['item_id']}] {rank}. {item_name} - ₹{price}")
        print(f" {restaurant} | {cuisine}")
        
        # Show RL score if available
        if 'rl_score' in rec:
            print(f" RL Score: {rec['rl_score']:.2f}")
        
        # Show tags if available
        if rec.get('tags'):
            tags_str = ", ".join(rec['tags'][:3])
            print(f" Tags: {tags_str}")
        
        print()


def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("AGENTIC FOOD ORDERING SYSTEM (WITH ORCHESTRATOR)")
    print("="*80)
    
    # Get system choice
    system_choice = input("\nWhich system? (langchain/gemini): ").strip() or "langchain"
    
    user_id = int(input(f"Enter your user ID (1-10): ") or "1")
    
    print(f"Using: {system_choice.capitalize()} Orchestrator")
    
    # ✅ Get the correct orchestrator with RL
    system = get_orchestrator(system_choice, user_id)
    
    if not system:
        print("\nFailed to initialize orchestrator")
        return

    print("\n" + "="*80)
    print("COMMANDS:")
    print(" Ask for food: 'I want spicy Chinese food'")
    print(" Show menu: 'show', 'menu', 'browse', 'what do you have?'")
    print(" Add to cart: 'add 2 butter chicken' or '15 2' or '[15] [2]'")
    print(" View cart: 'cart'")
    print(" Checkout: 'checkout'")
    print(" Quit: 'quit'")
    print("="*80 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nThanks for using our service!\n")
                break

            if not user_input:
                continue

            # ============================================
            # VIEW CART
            # ============================================
            if user_input.lower() == 'cart':
                cart = system.get_cart()
                print(f"\n{'='*80}")
                print("🛒 YOUR CART")
                print(f"{'='*80}")
                
                if not cart['items']:
                    print("Empty")
                else:
                    for item in cart['items']:
                        print(f" {item['quantity']}x {item['item_name']} - ₹{item['total_price']}")
                        print(f" {item['restaurant_name']}")

                print(f"\n{'-'*80}")
                print(f" Subtotal: ₹{cart['subtotal']}")
                print(f" Delivery: ₹{cart['delivery_fee']}")
                print(f" Total: ₹{cart['total']}")
                print(f"{'-'*80}")
                print(f" Min Order: ₹{cart['minimum_order']} {'✅' if cart['minimum_order_met'] else '❌'}")
                print(f"{'='*80}\n")
                continue

            # ============================================
            # CHECKOUT
            # ============================================
            if user_input.lower() == 'checkout':
                cart = system.get_cart()
                
                if not cart['items']:
                    print("\nCart is empty!\n")
                    continue

                if not cart['minimum_order_met']:
                    remaining = cart['minimum_order'] - cart['subtotal']
                    print(f"\nNeed ₹{remaining} more for minimum order\n")
                    continue

                print(f"\n{'='*80}")
                print("ORDER SUMMARY")
                print(f"{'='*80}")
                
                for item in cart['items']:
                    print(f" {item['quantity']}x {item['item_name']} - ₹{item['total_price']}")

                print(f"\n Total: ₹{cart['total']}")
                print(f"{'='*80}\n")

                confirm = input("Confirm order? (yes/no): ").strip().lower()
                
                if confirm in ['yes', 'y']:
                    # ✅ KEY: Call orchestrator.checkout() which saves RL state
                    result = system.checkout()
                    
                    if result['success']:
                        print(f"\n{'='*80}")
                        print("ORDER PLACED!")
                        print(f"{'='*80}")
                        print(f"Order ID: #{result['order_id']}")
                        print(f"Total: ₹{result['total']}")
                        print(f"Delivery Address: {result.get('delivery_address', 'Unknown')}")
                        
                        # Show RL reward if available
                        if 'rl_reward' in result:
                            print(f"RL Learning: +{result['rl_reward']:.2f} reward points")
                            print(f"RL State Saved!")
                        
                        print(f"{'='*80}\n")
                    else:
                        print(f"\n{result['message']}\n")
                else:
                    print("\nOrder cancelled\n")
                continue

            # ============================================
            # PROCESS MESSAGE
            # ============================================
            result = system.process_user_input(user_input)

            # Show result
            print(f"\n{'='*80}")
            print("RESULT")
            print(f"{'='*80}")
            
            if result['status'] == 'error':
                print("ERROR")
            else:
                print("SUCCESS")

            print(f"\n{result['message']}\n")

            # ============================================
            # SHOW RECOMMENDATIONS/MENU
            # ============================================
            if result.get('recommendations'):
                has_alternatives = result.get('has_alternatives', False)
                display_recommendations(result['recommendations'], has_alternatives)

                print(f"{'-'*80}")
                add_input = input("Quick add? Enter 'ID QTY' (e.g., '15 2') or 'Item Name' or press Enter: ").strip()

                if add_input:
                    try:
                        numbers = re.findall(r'\d+', add_input)
                        
                        if len(numbers) >= 2:
                            item_id = int(numbers[0])
                            qty = int(numbers[1])
                            item = next((r for r in result['recommendations'] if r['item_id'] == item_id), None)
                            
                            if item:
                                item_name = item.get('item_name', item.get('name', 'Unknown'))
                                add_result = system.process_user_input(f"add {qty} {item_name}")
                                print(f"\n{add_result['message']}")
                                
                                if add_result.get('cart'):
                                    cart_state = add_result['cart']
                                    print(f"\n🛒 Cart: {len(cart_state['items'])} items | Total: ₹{cart_state['total']}")
                            else:
                                print(f"\nItem ID {item_id} not found")
                        
                        elif len(numbers) == 1:
                            item_id = int(numbers[0])
                            qty = 1
                            item = next((r for r in result['recommendations'] if r['item_id'] == item_id), None)
                            
                            if item:
                                item_name = item.get('item_name', item.get('name', 'Unknown'))
                                add_result = system.process_user_input(f"add {qty} {item_name}")
                                print(f"\n{add_result['message']}")
                                
                                if add_result.get('cart'):
                                    cart_state = add_result['cart']
                                    print(f"\n🛒 Cart: {len(cart_state['items'])} items | Total: ₹{cart_state['total']}")
                            else:
                                print(f"\nItem ID {item_id} not found")
                        
                        else:
                            add_result = system.process_user_input(f"add {add_input}")
                            print(f"\n{add_result['message']}")
                            
                            if add_result.get('cart'):
                                cart_state = add_result['cart']
                                print(f"\n🛒 Cart: {len(cart_state['items'])} items | Total: ₹{cart_state['total']}")
                    
                    except (ValueError, IndexError) as e:
                        add_result = system.process_user_input(f"add {add_input}")
                        print(f"\n{add_result['message']}")
                        
                        if add_result.get('cart'):
                            cart_state = add_result['cart']
                            print(f"\n🛒 Cart: {len(cart_state['items'])} items | Total: ₹{cart_state['total']}")

            elif result.get('cart'):
                cart = result['cart']
                print(f"\n🛒 Cart: {len(cart['items'])} items | Total: ₹{cart['total']}")

            print(f"{'='*80}\n")

        except KeyboardInterrupt:
            print("\n\nInterrupted!\n")
            break

        except Exception as e:
            print(f"\nError: {e}\n")
            import traceback
            traceback.print_exc()

    system.cleanup()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFatal error: {e}\n")
        import traceback
        traceback.print_exc()
