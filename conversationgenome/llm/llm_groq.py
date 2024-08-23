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
    if not Utils._int(c.get('env', "GROQ_DIRECT_CALL"), 0):
        print("No groq package installed. pip install groq")

class llm_groq:
    verbose = False
    model = "llama3-8b-8192"
    direct_call = 0
    embeddings_model = "text-embedding-ada-002"
    client = None
    root_url = "https://api.groq.com/openai"
    # Test endpoint
    #root_url = "http://127.0.0.1:8000"
    api_key = None

    def __init__(self):
        self.direct_call = Utils._int(c.get('env', "GROQ_DIRECT_CALL"), 0)
        api_key = c.get('env', "GROQ_API_KEY")
        if Utils.empty(api_key):
            print("ERROR: Groq api_key not set. Set in .env file.")
            return
        if not self.direct_call and not Groq:
            print("ERROR: Groq module not found")
            return
        model = c.get("env", "GROQ_MODEL")
        if model:
            self.model = model

        embeddings_model = c.get("env", "GROQ_OPENAI_EMBEDDINGS_MODEL")
        if embeddings_model:
            self.embeddings_model = embeddings_model

        if not self.direct_call:
            client = Groq(api_key=api_key)
            self.client = client
        else:
            if self.verbose:
                print("GROQ DIRECT CALL")
            self.api_key = api_key

    # Groq Python library dependencies can conflict with other packages. Allow
    # direct call to API to bypass issues.
    def do_direct_call(self, data, url_path = "/v1/chat/completions"):
        url = self.root_url + url_path
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % (self.api_key),
        }
        response = {"success":0}
        http_timeout = Utils._float(c.get('env', 'HTTP_TIMEOUT', 60))
        try:
            response = Utils.post_url(url, jsonData=data, headers=headers, timeout=http_timeout)
        except Exception as e:
            print("Groq API Error", e)
            print("response", response)

        return response


    async def prompt_call_csv(self, convoXmlStr=None, participants=None):
        out = {"success":0}
        prompt1 = 'Analyze the following conversation in terms of topic interests of the participants where <p0> has the questions and <p1> has the answers. Response should be only comma-delimited tags in the CSV format.'
        prompt = prompt1 + "\n\n\n"

        prompt += convoXmlStr


        try:
            if not self.direct_call:
                completion = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    model=self.model,
                )
                raw_content = completion.choices[0].message.content
                out['content'] = raw_content
            else:
                data = {
                  "model": self.model,
                  "messages": [{"role": "user", "content": prompt}],
                }
                http_response = self.do_direct_call(data)
                #print("________CSV LLM completion", completion)
                out['content'] = Utils.get(http_response, 'json.choices.0.message.content')

        except Exception as e:
            print("GROQ API Error", e)

        #raw_content = Utils.get(completion, "choices.0.message.content")
        out['success'] = 1
        return out


    async def call_llm_tag_function(self, convoXmlStr=None, participants=None, call_type="csv"):
        out = {}

        out = await self.prompt_call_csv(convoXmlStr=convoXmlStr, participants=participants)

        return out

    async def conversation_to_metadata(self,  convo, generateEmbeddings=False):
        (xml, participants) = Utils.generate_convo_xml(convo)
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
            lines = content.replace("\n",",")
            tag_dict = {}
            parts = lines.split(",")
            if len(parts) > 1:
                for part in parts:
                    tag = part.strip().lower()
                    if tag[0:1] == "<":
                        continue
                    tag_dict[tag] = True
            else:
                print("Less that 2 tags returned. Aborting.")
                tags = []
            tags = list(tag_dict.keys())
        else:
            tags = []
        tags = Utils.clean_tags(tags)

        if len(tags) > 0:
            out['tags'] = tags
            out['vectors'] = {}
            if generateEmbeddings:
                if self.verbose:
                    print(f"------- Found tags: {tags}. Getting vectors for tags...")
                out['vectors'] = await self.get_vector_embeddings_set(tags)
            out['success'] = 1
        else:
            print("No tags returned by OpenAI for Groq", response)
        return out

    async def get_vector_embeddings_set(self,  tags):
        llm_embeddings = llm_openai()
        return await llm_embeddings.get_vector_embeddings_set(tags)


if __name__ == "__main__":
    print("Test Groq LLM class")
    llm = llm_groq()

    example_convo = {
        "lines": ["hello", "world"],
    }
    asyncio.run(llm.conversation_to_metadata(example_convo))

