import ollama
import json
from prompts.recommendation_prompt import RECOMMENDATION_AGENT_PROMPT

class RecommendationAgent:
    def __init__(self, model_name="qwen2.5:latest"):
        self.model_name = model_name
    
    def recommend(self, user_request, user_preferences=None, dietary_restrictions=None, 
                  past_orders=None, spice_level="", price_range=""):
        """
        Generate personalized recommendations
        
        Args:
            user_request: User's request/query
            user_preferences: Dict of preferences
            dietary_restrictions: List of restrictions
            past_orders: List of past orders
            spice_level: Desired spice level
            price_range: Budget preference
        
        Returns:
            dict: Structured recommendations
        """
        if user_preferences is None:
            user_preferences = {}
        if dietary_restrictions is None:
            dietary_restrictions = []
        if past_orders is None:
            past_orders = []
        
        # Format prompt
        prompt = RECOMMENDATION_AGENT_PROMPT.format(
            user_request=user_request,
            user_preferences=json.dumps(user_preferences),
            dietary_restrictions=json.dumps(dietary_restrictions),
            past_orders=json.dumps(past_orders),
            spice_level=spice_level,
            price_range=price_range
        )
        
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.5,
                    "top_p": 0.9,
                }
            )
            
            response_text = response['response']
            
            # Parse JSON
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    result = json.loads(response_text)
                
                return result
            
            except json.JSONDecodeError as e:
                print(f"JSON Parse Error: {e}")
                print(f"Response: {response_text}")
                return {
                    "recommendations": [],
                    "error": "Failed to parse recommendations",
                    "raw_response": response_text
                }
        
        except Exception as e:
            print(f"Error: {e}")
            return {
                "recommendations": [],
                "error": str(e)
            }