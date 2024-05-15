import os
import json

from conversationgenome.utils.Utils import Utils
from conversationgenome.ConfigLib import c


Groq = None
try:
    from groq import Groq
except:
    print("No groq package installed. pip install groq")

class llm_groq:
    verbose = False
    model = "llama3-8b-8192"
    embeddings_model = "text-embedding-ada-002"

    def __init__(self):
        if not Groq:
            print("ERROR: Groq module not found")
            return
        api_key = c.get('env', "GROQ_API_KEY")
        if Utils.empty(api_key):
            print("ERROR: Groq api_key not set. Set in .env file.")
            return
        model = c.get("env", "GROQ_MODEL")
        if model:
            self.model = model

        embeddings_model = c.get("env", "GROQ_OPENAI_EMBEDDINGS_MODEL")
        if embeddings_model:
            self.embeddings_model = embeddings_model

        client = Groq(api_key=api_key)
        self.client = client

    def call(self, prompt):
        response = {"success":0}
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
            )
        except Exception as e:
            print("GROQ API Error", e)

        print(chat_completion.choices[0].message.content)

if __name__ == "__main__":
    print("Test Groq LLM class")
    llm = llm_groq()
    llm.call("Explain the importance of fast language models")
