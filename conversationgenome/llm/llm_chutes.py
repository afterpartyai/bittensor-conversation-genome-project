import requests
from typing import List
from openai import OpenAI, NOT_GIVEN

from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib


class LlmChutes(LlmLib):
    def __init__(self):
        self.api_key = c.get('env', "CHUTES_API_KEY")
        if not self.api_key:
            raise ValueError("CHUTES_API_KEY environment variable not set. Please set it in the .env file or as an environment variable.")
        
        self.client = OpenAI(
            base_url="https://llm.chutes.ai/v1",
            api_key=self.api_key
        )
        self.model = c.get('env', "CHUTES_MODEL", "deepseek-ai/DeepSeek-V3")
        self.embedding_url = c.get('env', "CHUTES_EMBEDDING_URL", "https://chutes-qwen-qwen3-embedding-8b.chutes.ai/v1/embeddings")


    ###############################################################################################
    ################################## Abstract methods override ##################################
    ###############################################################################################
    def basic_prompt(self, prompt: str, response_format: str = "text") -> str|None:
        api_format = {"type": "json_object"} if response_format == "json" else NOT_GIVEN
        
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
        try:
            headers = {
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json"
            }
            
            body = {
                "input": tag,
                "model": None
            }

            response = requests.post(
                self.embedding_url,
                headers=headers,
                json=body
            )

            if response.status_code == 200:
                result = response.json()
                return result['data'][0]['embedding']
            else:
                print(f"Chutes Embedding Error: Status {response.status_code}")
                # print(response.text)
                return None
        except Exception as e:
            print(f"Chutes Embedding Error")
            # print(e)
            return None
