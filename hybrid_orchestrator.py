"""
HYBRID ORCHESTRATOR - LangChain + Gemini Fallback System
============================================================================
Intelligently routes between LangChain (local Ollama) and Gemini (cloud).

ROUTING LOGIC:
- Complex queries → Gemini (better reasoning)
- Simple queries → Local Ollama (instant, free)
- User preference → Explicit selection
- Fallback chain on failure

BENEFITS:
- Cost efficient (local by default)
- Handles API failures gracefully
- Best-of-both approach
============================================================================
"""

import json
from typing import Dict, Optional, Literal
import os

from langchain_orchestrator import LangChainOrchestrator
try:
    from gemini_orchestrator import GeminiOrchestrator
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class HybridOrchestrator:
    """
    Intelligently routes between LangChain and Gemini orchestrators.
    """
    
    def __init__(
        self,
        user_id: int,
        mode: Literal["auto", "langchain", "gemini"] = "auto",
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize hybrid orchestrator.
        
        Args:
            user_id: User ID
            mode: "auto" (smart routing), "langchain" (force local), "gemini" (force cloud)
            gemini_api_key: Optional Gemini API key
        """
        print("\n" + "="*80)
        print("🔄 INITIALIZING HYBRID ORCHESTRATOR")
        print("="*80)
        
        self.user_id = user_id
        self.mode = mode
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")
        
        # Initialize primary orchestrator
        if mode == "langchain":
            print("📍 Mode: LangChain (Local Ollama)")
            self.primary_orchestrator = LangChainOrchestrator(user_id, use_local_only=True)
            self.secondary_orchestrator = None
        elif mode == "gemini":
            if not self.gemini_api_key or not GEMINI_AVAILABLE:
                print("⚠️ Ggememini unavailable, using LangChain fallback")
                self.primary_orchestrator = LangChainOrchestrator(user_id, use_local_only=True)
                self.secondary_orchestrator = None
            else:
                print("Mode: Gemini")
                self.primary_orchestrator = GeminiOrchestrator(user_id, self.gemini_api_key)
                self.secondary_orchestrator = None
        else:  # auto
            print("Mode: Auto-routing (Smart Selection)")
            self.primary_orchestrator = LangChainOrchestrator(user_id, use_local_only=True)
            
            if self.gemini_api_key and GEMINI_AVAILABLE:
                try:
                    self.secondary_orchestrator = GeminiOrchestrator(user_id, self.gemini_api_key)
                    print("Secondary Gemini available as backup")
                except Exception as e:
                    print(f"Gemini backup unavailable: {e}")
                    self.secondary_orchestrator = None
            else:
                self.secondary_orchestrator = None
        
        print("="*80 + "\n")
    
    def process_user_input(self, user_input: str, force_model: Optional[str] = None) -> Dict:
        """
        Process user input with intelligent routing.
        
        Args:
            user_input: User message
            force_model: Force specific model ("langchain" or "gemini")
        
        Returns:
            Response dict
        """
        if force_model == "gemini" and self.secondary_orchestrator:
            return self._process_with_gemini(user_input)
        elif force_model == "langchain" or self.mode == "langchain":
            return self._process_with_langchain(user_input)
        else:
            return self._auto_route(user_input)
    
    def _process_with_langchain(self, user_input: str) -> Dict:
        """Process using LangChain"""
        try:
            return self.primary_orchestrator.process_user_input(user_input)
        except Exception as e:
            print(f"LangChain error: {e}")
            if self.secondary_orchestrator:
                print("Falling back to Gemini...")
                return self._process_with_gemini(user_input)
            raise
    
    def _process_with_gemini(self, user_input: str) -> Dict:
        """Process using Gemini"""
        if not self.secondary_orchestrator:
            raise RuntimeError("Gemini not available")
        try:
            return self.secondary_orchestrator.process_user_input(user_input)
        except Exception as e:
            print(f"⚠️ Gemini error: {e}")
            print("Falling back to LangChain...")
            return self._process_with_langchain(user_input)
    
    def _auto_route(self, user_input: str) -> Dict:
        """Intelligently route based on query complexity"""
        complexity_indicators = {
            'simple': ['show', 'list', 'menu', 'cart', 'price', 'add', 'remove'],
            'complex': ['compare', 'recommend', 'suggest', 'best', 'similar', 'what', 'why', 'how']
        }
        
        is_complex = any(word in user_input.lower() for word in complexity_indicators['complex'])
        
        if is_complex and self.secondary_orchestrator:
            print("Complex query → Routing to Gemini")
            return self._process_with_gemini(user_input)
        else:
            print("Simple query → Using Local Ollama")
            return self._process_with_langchain(user_input)
    
    def cleanup(self):
        """Cleanup both orchestrators"""
        self.primary_orchestrator.cleanup()
        if self.secondary_orchestrator:
            self.secondary_orchestrator.cleanup()
        print("Hybrid orchestrator cleanup complete")
