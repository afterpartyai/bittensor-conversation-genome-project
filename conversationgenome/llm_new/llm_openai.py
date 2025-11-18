from typing import List

from openai import OpenAI

from conversationgenome.ConfigLib import c
from conversationgenome.llm_new import LlmLib


class LlmOpenAI(LlmLib):
    def __init__(self, model_override: str = None, embedding_model_override: str = None):
        api_key = c.get('env', "OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set. Please set it in the .env file or as an environment variable.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model_override or "gpt-4o"
        self.embedding_model = embedding_model_override or "text-embedding-3-small"

    def basic_prompt(self, prompt: str, response_format: str = "text") -> str|None:
        api_format = {"type": "json_object"} if response_format == "json" else {"type": "text"}
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=api_format
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"OpenAI Completion Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None

    def get_vector_embeddings(self, tag: str, dimensions=1536) -> List[float]|None:
        tag = tag.replace("\n", " ")
        try:
            response = self.client.embeddings.create(
                input=tag,
                model=self.embedding_model,
                dimensions=dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenAI Embedding Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None
