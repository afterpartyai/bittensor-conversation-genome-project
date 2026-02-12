from typing import List
import json
from openai import OpenAI

from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib, model_override


class LlmOpenRouter(LlmLib):
    def __init__(self):
        api_key = c.get('env', "OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set. Please set it in the .env file or as an environment variable.")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = c.get('env', "OPENROUTER_MODEL", "deepseek/deepseek-chat")
        self.provider_preference = c.get('env', "OPENROUTER_PROVIDER_PREFERENCE", "chutes")
        self.embedding_model = c.get('env', "OPENROUTER_EMBEDDING_MODEL", "text-embedding-3-small")


    ###############################################################################################
    ################################## Abstract methods override ##################################
    ###############################################################################################
    def basic_prompt(self, prompt: str, response_format: str = "text") -> str|None:
        api_format = {"type": "json_object"} if response_format == "json" else None
        
        extra_body = {}
        if self.provider_preference:
            extra_body["provider"] = {"order": [self.provider_preference]}

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=api_format,
                extra_body=extra_body
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"OpenRouter Completion Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None

    def get_vector_embeddings(self, tag: str, dimensions=1536) -> List[float]|None:
        tag = tag.replace("\n", " ")
        # Note: OpenRouter might not support embeddings for all models.
        # We use a default embedding model (likely OpenAI's) or a configured one.
        try:
            response = self.client.embeddings.create(
                input=tag,
                model=self.embedding_model,
                # dimensions=dimensions # Some models don't support dimensions param
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenRouter Embedding Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None
