import os
import json
import asyncio

from conversationgenome.utils.Utils import Utils
from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_openai import llm_openai


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

    async def prompt_call_csv(self, convoXmlStr=None, participants=None):
        out = {"success":0}
        prompt1 = 'Analyze the following conversation in terms of topic interests of the participants where <p0> has the questions and <p1> has the answers. Response should be only comma-delimited tags in the CSV format.'
        prompt = prompt1 + "\n\n\n"

        prompt += convoXmlStr


        try:
            completion = self.client.chat.completions.create(
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

        #raw_content = Utils.get(completion, "choices.0.message.content")
        raw_content = completion.choices[0].message.content
        out['content'] = raw_content
        out['success'] = 1
        return out


    async def call_llm_tag_function(self, convoXmlStr=None, participants=None, call_type="csv"):
        out = {}

        out = await self.prompt_call_csv(convoXmlStr=convoXmlStr, participants=participants)

        return out

    async def conversation_to_metadata(self,  convo):
        llm_embeddings = llm_openai()
        (xml, participants) = llm_embeddings.generate_convo_xml(convo)
        tags = None
        out = {"tags":{}}

        response = await self.call_llm_tag_function(convoXmlStr=xml, participants=participants)
        if not response:
            print("No tagging response. Aborting")
            return None
        elif not response['success']:
            print(f"Tagging failed: {response}. Aborting")
            return response

        content = Utils.get(response, 'content')
        if content:
            lines = content.split("\n")
            tag_dict = {}
            for line in lines:
                parts = line.split(",")
                if len(parts) > 3:
                    for part in parts:
                        tag = part.strip().lower()
                        tag_dict[tag] = True
            tags = list(tag_dict.keys())
        else:
            tags = ""
        tags = Utils.clean_tags(tags)

        if not Utils.empty(tags):
            if True or self.verbose:
                print(f"------- Found tags: {tags}. Getting vectors for tags...")
            out['tags'] = tags
            out['vectors'] = {}
            tag_logs = []
            for tag in tags:
                vectors = await llm_embeddings.get_vector_embeddings(tag)
                if not vectors:
                    print(f"ERROR -- no vectors for tag: {tag} vector response: {vectors}")
                else:
                    tag_logs.append(f"{tag}={len(vectors)}vs")
                out['vectors'][tag] = {"vectors":vectors}
            if self.verbose:
                print("        Embeddings received: " + ", ".join(tag_logs))
                print("VECTORS", tag, vectors)
            out['success'] = 1
        else:
            print("No tags returned by OpenAI", response)
        return out



if __name__ == "__main__":
    print("Test Groq LLM class")
    llm = llm_groq()
    #llm.call("Explain the importance of fast language models")

    example_convo = {
        "lines": ["hello", "world"],
    }
    asyncio.run(llm.conversation_to_metadata(example_convo))

