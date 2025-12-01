from typing import List

from anthropic import Anthropic
from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_openai import LlmOpenAI

from .LlmLib import LlmLib

class LlmAnthropic(LlmLib):
    def __init__(self):
        api_key = c.get('env', "ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set. Please set it in the .env file or as an environment variable.")

        self.client = Anthropic(api_key=api_key)
        self.model = c.get("env", "ANTHROPIC_MODEL", "claude-3-sonnet-20240229")

    def basic_prompt(self, prompt: str, response_format: str = "text") -> str:
        # Anthropic does not currently support "response_format"        
        try:
            message = self.client.messages.create(
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )
            return message.content[0].text
        except Exception as e:
            print(f"Anthropic Messages Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None

    def get_vector_embeddings_set(self, tag: str) -> List[float]:
        # Anthropic currently does not support generating embeddings. We fallback to openAI for now.
        llml = LlmOpenAI()
        return llml.get_vector_embeddings(tag)
