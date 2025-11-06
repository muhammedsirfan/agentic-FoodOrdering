import ollama
import json
from prompts.conversation_prompt import CONVERSATION_AGENT_PROMPT

class ConversationAgent:
    def __init__(self, model_name="mistral:latest"):
        self.model_name = model_name
        self.conversation_history = []
    
    def process(self, user_input, user_preferences=None, conversation_history=None):
        """
        Process user input and classify intent
        
        Args:
            user_input: User's message
            user_preferences: Dict of user preferences (optional)
            conversation_history: List of previous messages (optional)
        
        Returns:
            dict: Structured response with intent and routing info
        """
        if user_preferences is None:
            user_preferences = {}
        if conversation_history is None:
            conversation_history = []
        
        # Format the prompt
        prompt = CONVERSATION_AGENT_PROMPT.format(
            user_input=user_input,
            conversation_history=json.dumps(conversation_history[-5:]),  # Last 5 messages
            user_preferences=json.dumps(user_preferences)
        )
        
        try:
            # Call Ollama
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.3,  # Lower temperature for consistent JSON
                    "top_p": 0.9,
                }
            )
            
            # Extract response text
            response_text = response['response']
            
            # Try to parse JSON
            try:
                # Find JSON in response (sometimes model adds extra text)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    result = json.loads(response_text)
                
                # Store in history
                self.conversation_history.append({
                    "user": user_input,
                    "agent": result.get("conversational_response", "")
                })
                
                return result
            
            except json.JSONDecodeError as e:
                print(f"JSON Parse Error: {e}")
                print(f"Response: {response_text}")
                # Return fallback
                return {
                    "intent": "error",
                    "user_query": user_input,
                    "error": "Failed to parse response",
                    "raw_response": response_text
                }
        
        except Exception as e:
            print(f"Error: {e}")
            return {
                "intent": "error",
                "user_query": user_input,
                "error": str(e)
            }
