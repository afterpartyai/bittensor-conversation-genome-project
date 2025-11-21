from typing import List

from groq import Groq

from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_openai import LlmOpenAI
from .LlmLib import LlmLib


class LlmGroq(LlmLib):
    def __init__(self):
        api_key = c.get('env', "GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set. Please set it in the .env file or as an environment variable.")
        self.client = Groq(api_key=api_key)
        self.model = c.get("env", "GROQ_MODEL", "llama3-8b-8192")

    ###############################################################################################
    ################################## Abstract methods override ##################################
    ###############################################################################################
    def basic_prompt(self, prompt: str, response_format: str = "text") -> str:
        # Groq supports the 'json_object' response format on specific models
        api_format = {"type": "json_object"} if response_format == "json" else None
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                response_format=api_format
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"Groq Completion Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None

    def get_vector_embeddings_set(self, tag: str) -> List[float]:
        # Groq currently does not support generating embeddings. We fallback to openAI for now.
        llml = LlmOpenAI()
        return llml.get_vector_embeddings(tag)
