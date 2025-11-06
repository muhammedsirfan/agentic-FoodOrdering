"""
Flask Backend for Agentic Food Ordering System

This backend integrates with your existing orchestrators (LangChain/Gemini)
and provides REST API endpoints for the web frontend.

Installation:
pip install flask flask-cors

Usage:
python backend_server.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import sys
import traceback

# Import your existing orchestrators
try:
    from gemini_orchestrator import GeminiOrchestrator
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Gemini orchestrator not available")

try:
    from langchain_orchestrator import LangChainOrchestrator
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️ LangChain orchestrator not available")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Session storage (in production, use Redis or database)
sessions = {}

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_orchestrator(orchestrator_type: str, user_id: int):
    """Create orchestrator instance"""
    if orchestrator_type.lower() == "gemini" and GEMINI_AVAILABLE:
        return GeminiOrchestrator(user_id=user_id)
    elif orchestrator_type.lower() == "langchain" and LANGCHAIN_AVAILABLE:
        return LangChainOrchestrator(user_id=user_id)
    else:
        raise ValueError(f"Orchestrator type '{orchestrator_type}' not available")

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'gemini_available': GEMINI_AVAILABLE,
        'langchain_available': LANGCHAIN_AVAILABLE
    })

@app.route('/api/init', methods=['POST'])
def initialize_session():
    """Initialize a new session"""
    try:
        data = request.json
        user_id = data.get('user_id', 3)
        orchestrator_type = data.get('orchestrator_type', 'langchain')

        print(f"\n{'='*80}")
        print(f"Initializing session for user {user_id} with {orchestrator_type}")
        print(f"{'='*80}")

        # Create orchestrator
        orchestrator = get_orchestrator(orchestrator_type, user_id)

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Store session
        sessions[session_id] = {
            'orchestrator': orchestrator,
            'user_id': user_id,
            'orchestrator_type': orchestrator_type
        }

        # Get user data
        user_data = orchestrator.user_data

        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'user_data': {
                'name': user_data.get('name', 'Guest'),
                'address': user_data.get('address', 'Unknown'),
                'user_id': user_id
            },
            'orchestrator_type': orchestrator_type,
            'message': f"Welcome {user_data.get('name', 'Guest')}! I'm your AI food assistant. What would you like to eat today?"
        })

    except Exception as e:
        print(f"Error initializing session: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process user message"""
    try:
        data = request.json
        session_id = data.get('session_id')
        message = data.get('message')

        if not session_id or session_id not in sessions:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired session'
            }), 400

        # Get orchestrator from session
        orchestrator = sessions[session_id]['orchestrator']

        print(f"\n{'='*80}")
        print(f"USER MESSAGE: {message}")
        print(f"{'='*80}")

        # Process message
        result = orchestrator.process_user_input(message)

        # Format response
        response = {
            'status': result.get('status', 'success'),
            'message': result.get('message', ''),
            'intent': result.get('intent', 'general'),
            'recommendations': result.get('recommendations', []),
            'cart': result.get('cart', {}),
            'session_id': session_id
        }

        return jsonify(response)

    except Exception as e:
        print(f"Error processing chat: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/cart', methods=['GET'])
def get_cart():
    """Get current cart state"""
    try:
        session_id = request.args.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired session'
            }), 400

        # Get orchestrator from session
        orchestrator = sessions[session_id]['orchestrator']

        # Get cart
        cart = orchestrator.get_cart()

        return jsonify({
            'status': 'success',
            'cart': cart
        })

    except Exception as e:
        print(f"Error getting cart: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/checkout', methods=['POST'])
def checkout():
    """Process checkout"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired session'
            }), 400

        # Get orchestrator from session
        orchestrator = sessions[session_id]['orchestrator']

        print(f"\n{'='*80}")
        print(f"PROCESSING CHECKOUT")
        print(f"{'='*80}")

        # Process checkout
        result = orchestrator.checkout()

        return jsonify(result)

    except Exception as e:
        print(f"Error during checkout: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/add_to_cart', methods=['POST'])
def add_to_cart():
    """Quick add item to cart"""
    try:
        data = request.json
        session_id = data.get('session_id')
        item_name = data.get('item_name')
        quantity = data.get('quantity', 1)

        if not session_id or session_id not in sessions:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired session'
            }), 400

        # Get orchestrator from session
        orchestrator = sessions[session_id]['orchestrator']

        # Add item using natural language
        message = f"add {quantity} {item_name}"
        result = orchestrator.process_user_input(message)

        return jsonify({
            'status': result.get('status', 'success'),
            'message': result.get('message', ''),
            'cart': result.get('cart', {})
        })

    except Exception as e:
        print(f"Error adding to cart: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 AGENTIC FOOD ORDERING BACKEND SERVER")
    print("="*80)
    print(f"Gemini Available: {GEMINI_AVAILABLE}")
    print(f"LangChain Available: {LANGCHAIN_AVAILABLE}")
    print("="*80)
    print("\nServer starting on http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  GET  /api/health")
    print("  POST /api/init")
    print("  POST /api/chat")
    print("  GET  /api/cart")
    print("  POST /api/checkout")
    print("  POST /api/add_to_cart")
    print("="*80 + "\n")

    app.run(debug=True, port=5000, host='0.0.0.0')
