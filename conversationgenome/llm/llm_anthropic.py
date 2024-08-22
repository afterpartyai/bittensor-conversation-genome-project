import os
import json
import asyncio

from conversationgenome.utils.Utils import Utils
from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_openai import llm_openai


class llm_anthropic:
    verbose = False
    model = "claude-3-sonnet-20240229"
    direct_call = 0
    embeddings_model = "text-embedding-ada-002"
    client = None
    root_url = "https://api.anthropic.com"
    # Test endpoint
    #root_url = "http://127.0.0.1:8000"
    api_key = None

    def __init__(self):
        api_key = c.get('env', "ANTHROPIC_API_KEY")
        if Utils.empty(api_key):
            print("ERROR: Anthropic api_key not set. Set in .env file.")
            return

        model = c.get("env", "ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        if model:
            self.model = model

        embeddings_model = c.get("env", "ANTHROPIC_OPENAI_EMBEDDINGS_MODEL")
        if embeddings_model:
            self.embeddings_model = embeddings_model

        self.api_key = api_key

    def do_direct_call(self, data, url_path = "/v1/messages"):
        url = self.root_url + url_path
        headers = {
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key": self.api_key,
        }
        response = {"success":0}
        http_timeout = Utils._float(c.get('env', 'HTTP_TIMEOUT', 60))
        #print("URL", url, headers, data)
        try:
            response = Utils.post_url(url, jsonData=data, headers=headers, timeout=http_timeout)
        except Exception as e:
            print("Anthropic API Error", e)
            print("response", response)

        return response


    async def prompt_call_csv(self, convoXmlStr=None, participants=None):
        out = {"success":0}
        prompt_base = 'Analyze the following conversation in terms of topic interests of the participants where <p0> has the questions and <p1> has the answers. Response should be only comma-delimited tags in the CSV format.'
        prompt = f"\n\nHuman: {prompt_base}\n{convoXmlStr}\n\nAssistant:"
        try:
            data = {
                "model": self.model,
                "max_tokens": 1024,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            http_response = self.do_direct_call(data)
            #print("________CSV LLM completion", http_response)
            out['content'] = Utils.get(http_response, 'json.content.0.text')

        except Exception as e:
            print("ANTHROPIC API Error", e)

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
                tags = list(tag_dict.keys())
            else:
                print("Less that 2 tags returned. Aborting.")
                tags = []
        else:
            tags = []
        tags = Utils.clean_tags(tags)

        if len(tags) > 0:
            out['tags'] = tags
            out['vectors'] = {}
            if generateEmbeddings:
                if self.verbose:
                    print(f"------- Found tags: {tags}. Getting vectors for tags...")
                out['vectors'] = await self.get_vector_embeddings(tag)
            out['success'] = 1
        else:
            print("No tags returned by OpenAI for Anthropic", response)
        return out

    async def get_vector_embeddings(self,  tags):
        llm_embeddings = llm_openai()
        tag_logs = []
        tagVectors = {}
        for tag in tags:
            vectors = await llm_embeddings.get_vector_embeddings(tag)
            if not vectors:
                print(f"ERROR -- no vectors for tag: {tag} vector response: {vectors}")
            else:
                tag_logs.append(f"{tag}={len(vectors)}vs")
            tagVectors[tag] = {"vectors":vectors}
        if self.verbose:
            print("        Embeddings received: " + ", ".join(tag_logs))
            print("VECTORS", tag, vectors)
        return tagVectors


if __name__ == "__main__":
    print("Test Anthropic LLM class")
    llm = llm_groq()

    example_convo = {
        "lines": ["hello", "world"],
    }
    asyncio.run(llm.conversation_to_metadata(example_convo))

