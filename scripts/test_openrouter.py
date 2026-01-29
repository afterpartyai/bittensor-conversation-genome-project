import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conversationgenome.llm.llm_openrouter import LlmOpenRouter

def main():
    load_dotenv()
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in .env")
        return

    print("--- Testing OpenRouter Implementation ---")
    try:
        llm = LlmOpenRouter()
        print(f"Model: {llm.model}")
        print(f"Provider Preference: {llm.provider_preference}")
        
        prompt = "Hello, tell me a short joke about AI."
        print(f"Prompt: {prompt}")
        
        response = llm.basic_prompt(prompt)
        print(f"Response: {response}")
        
        if response:
            print("SUCCESS: End-to-end connectivity verified!")
        else:
            print("FAILURE: Received empty response.")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
