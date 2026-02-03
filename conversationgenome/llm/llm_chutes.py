from typing import List
from openai import OpenAI

from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib


class LlmChutes(LlmLib):
    def __init__(self):
        api_key = c.get('env', "CHUTES_API_KEY")
        if not api_key:
            raise ValueError("CHUTES_API_KEY environment variable not set. Please set it in the .env file or as an environment variable.")
        
        self.client = OpenAI(
            base_url="https://llm.chutes.ai/v1",
            api_key=api_key
        )
        self.model = c.get('env', "CHUTES_MODEL", "deepseek-ai/DeepSeek-V3")
        self.embedding_model = c.get('env', "CHUTES_EMBEDDING_MODEL", "text-embedding-3-small")


    ###############################################################################################
    ################################## Abstract methods override ##################################
    ###############################################################################################
    def basic_prompt(self, prompt: str, response_format: str = "text") -> str|None:
        api_format = {"type": "json_object"} if response_format == "json" else None
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=api_format,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"Chutes Completion Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None

    def get_vector_embeddings(self, tag: str, dimensions=1536) -> List[float]|None:
        tag = tag.replace("\n", " ")
        # Note: Chutes might not support embeddings for all models via the direct API.
        # We use a default embedding model (likely requiring OpenAI key if not local) or a configured one.
        try:
            response = self.client.embeddings.create(
                input=tag,
                model=self.embedding_model,
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Chutes Embedding Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None
