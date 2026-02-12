from typing import List
from openai import OpenAI

from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib, model_override


class LlmOpenAI(LlmLib):
    def __init__(self):
        api_key = c.get('env', "OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set. Please set it in the .env file or as an environment variable.")
        self.client = OpenAI(api_key=api_key)
        self.model = c.get('env', "OPENAI_MODEL", "gpt-5.2")
        self.embedding_model = "text-embedding-3-small"


    ###############################################################################################
    ################################## Abstract methods override ##################################
    ###############################################################################################
    def basic_prompt(self, prompt: str, response_format: str = "text") -> str|None:
        api_format = {"type": "json_object"} if response_format == "json" else None
        
        completion_params = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": api_format,
        }

        try:
            response = self.client.chat.completions.create(**completion_params)
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"OpenAI Completion Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None

    def get_vector_embeddings(self, tag: str, dimensions=1536) -> List[float]|None:
        tag = tag.replace("\n", " ")
        embedding_model = self.embedding_model
        try:
            response = self.client.embeddings.create(
                input=tag,
                model=embedding_model,
                dimensions=dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenAI Embedding Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return None

    
    ###############################################################################################
    ################################## Concrete methods override ##################################
    ###############################################################################################
    @model_override('gpt-5-mini')
    def validate_conversation_quality(self, conversation):
        return super().validate_conversation_quality(conversation)

