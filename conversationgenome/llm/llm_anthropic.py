import os
import json
import asyncio

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationQualityMetadata
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.utils.Utils import Utils
from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_openai import llm_openai
from conversationgenome.llm.prompt_manager import prompt_manager


class llm_anthropic:
    verbose = False
    model = "claude-3-sonnet-20240229"
    direct_call = 0
    embeddings_model = "text-embedding-3-large"
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

        embeddings_model = c.get("env", "ANTHROPIC_OPENAI_EMBEDDINGS_MODEL_OVERRIDE")
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

        try:
            response = Utils.post_url(url, jsonData=data, headers=headers, timeout=http_timeout)
        except Exception as e:
            print("Anthropic API Error")

        return response


    async def prompt_call_csv(self, convoXmlStr=None, participants=None, override_prompt=None, partial_prompt_override=None):
        out = {"success":0}
        if override_prompt:
            prompt = override_prompt
        else:
            if partial_prompt_override:
                prompt_base = partial_prompt_override
            else:
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
            out['content'] = Utils.get(http_response, 'json.content.0.text')

        except Exception as e:
            print("ANTHROPIC API Error")

        out['success'] = 1
        return out


    async def call_llm_tag_function(self, prompt: str, convoXmlStr=None, participants=None, call_type="csv"):
        out = {}

        out = await self.prompt_call_csv(convoXmlStr=convoXmlStr, participants=participants, partial_prompt_override=prompt)

        return out

    async def conversation_to_metadata(self,  convo: Conversation, generateEmbeddings=False) -> RawMetadata | None:
        (xml, participants) = Utils.generate_convo_xml(convo)
        tags = None
        out = {"tags":{}, "success": False}

        response = await self.call_llm_tag_function(convoXmlStr=xml, prompt=convo.miner_task_prompt, participants=participants)
        if not response:
            print("No tagging response. Aborting")
            return None
        elif not response['success']:
            print(f"Tagging failed. Aborting")
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
            out['vectors'] = None
            if generateEmbeddings:
                if self.verbose:
                    print(f"------- Found tags: {tags}. Getting vectors for tags...")
                out['vectors'] = await self.get_vector_embeddings_set(tags)
            out['success'] = True
        else:
            print("No tags returned by OpenAI for Anthropic")

        return RawMetadata(
            tags=out["tags"],
            vectors=out["vectors"],
            success=out["success"]
        )

    async def basic_prompt(self, prompt: str, response_format=None) -> str:
        try:
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
            http_response = self.do_direct_call(data)
            return Utils.get(http_response, 'json.choices.0.message.content')
        except Exception as e:
            print("Error in LLM call")
            return None

    async def validate_conversation_quality(self, conversation: Conversation) -> ConversationQualityMetadata | None:
        conversation_xml, _ = Utils.generate_convo_xml(conversation)
        prompt = prompt_manager.conversation_quality_prompt(transcript_text=conversation_xml)
        response_content = await self.basic_prompt(prompt)
        try:
            return ConversationQualityMetadata(**json.loads(response_content))
        except json.JSONDecodeError as e:
            print("Error parsing LLM reply as ConversationQualityMetadata")
            return None
        
    async def survey_to_metadata(self, survey_question: str, comment:str) -> RawMetadata|None:
        prompt = prompt_manager.survey_tag_prompt(survey_question, comment)
        response_content = await self.basic_prompt(prompt)
        if not isinstance(response_content, str):
            print("Error: Unexpected response format. Content type:", type(response_content))
            return None
        try:
            tags = Utils.clean_tags(response_content.split(","))
            vectors = await self.get_vector_embeddings_set(tags)
        except Exception as e:
            print("Error: Error generating vectors")
            return None
        return RawMetadata(tags=tags, vectors=vectors, success=True)
    
    async def get_vector_embeddings_set(self,  tags):
        llm_embeddings = llm_openai()
        return await llm_embeddings.get_vector_embeddings_set(tags)
