import ollama
import json
from prompts.order_handler_prompt import ORDER_EXPLANATION_AGENT_PROMPT

class OrderHandlerAgent:
    def __init__(self, model_name="llama3:latest"):
        self.model_name = model_name
    
    def process(self, request_type, request_data, current_cart=None, user_dietary_info=None):
        """
        Handle order processing or provide explanations
        
        Args:
            request_type: Type of request (order_processing, explanation, etc.)
            request_data: Data for the request
            current_cart: Current cart state
            user_dietary_info: User dietary information
        
        Returns:
            dict: Structured response
        """
        if current_cart is None:
            current_cart = []
        if user_dietary_info is None:
            user_dietary_info = {}
        
        # Format prompt
        prompt = ORDER_EXPLANATION_AGENT_PROMPT.format(
            request_type=request_type,
            request_data=json.dumps(request_data),
            current_cart=json.dumps(current_cart),
            user_dietary_info=json.dumps(user_dietary_info)
        )
        
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.3,
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
                    "action": "error",
                    "error": "Failed to parse response",
                    "raw_response": response_text
                }
        
        except Exception as e:
            print(f"Error: {e}")
            return {
                "action": "error",
                "error": str(e)
            }