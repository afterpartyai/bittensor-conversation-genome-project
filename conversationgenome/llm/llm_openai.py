from typing import List
from openai import OpenAI

from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib, model_override, reasoning_effort_override, service_tier_override

DEFAULT_MODEL = "gpt-5.2"


class LlmOpenAI(LlmLib):
    def __init__(self, ignore_model_override: bool = False):
        api_key = c.get('env', "OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set. Please set it in the .env file or as an environment variable.")
        self.client = OpenAI(api_key=api_key)
        self.model = DEFAULT_MODEL if ignore_model_override else c.get('env', "OPENAI_MODEL", DEFAULT_MODEL)
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
        # The installed openai SDK (1.30.3) predates first-class typed support
        # for reasoning_effort/service_tier and rejects them as unexpected
        # kwargs if passed directly -- extra_body merges them straight into
        # the request JSON, which the API accepts fine. Safe to pass both
        # directly once the SDK is upgraded.
        extra_body = {}
        if self.reasoning_effort:
            extra_body["reasoning_effort"] = self.reasoning_effort
        if self.service_tier:
            extra_body["service_tier"] = self.service_tier
        if extra_body:
            completion_params["extra_body"] = extra_body

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

    def get_vector_embeddings_batch(self, texts: List[str], dimensions=1536) -> List[List[float] | None]:
        if not texts:
            return []
        cleaned = [text.replace("\n", " ") for text in texts]
        try:
            response = self.client.embeddings.create(
                input=cleaned,
                model=self.embedding_model,
                dimensions=dimensions
            )
            # OpenAI returns embeddings in the same order as the input list.
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"OpenAI Batch Embedding Error")
            # Uncomment the line below for debugging purposes
            # print(e)
            return [None] * len(texts)


    ###############################################################################################
    ################################## Concrete methods override ##################################
    ###############################################################################################
    @model_override('gpt-5-mini')
    def validate_conversation_quality(self, conversation):
        return super().validate_conversation_quality(conversation)

    # The skill_coverage_evaluation prompt chain (section map, skill/TDD/test
    # generation, and the correctness judge) is slow on the default model, 
    # using overrides to speed up the prompt results
    @model_override('gpt-5.6-luna')
    @reasoning_effort_override('low')
    @service_tier_override('priority')
    def skill_request_to_section_map(self, seed):
        return super().skill_request_to_section_map(seed)

    @model_override('gpt-5.6-luna')
    @reasoning_effort_override('low')
    @service_tier_override('priority')
    def skill_request_to_skill(self, seed, section_map):
        return super().skill_request_to_skill(seed, section_map)

    @model_override('gpt-5.6-luna')
    @reasoning_effort_override('low')
    @service_tier_override('priority')
    def skill_request_to_skill_bundle(self, seed, section_map):
        return super().skill_request_to_skill_bundle(seed, section_map)

    @model_override('gpt-5.6-luna')
    @reasoning_effort_override('low')
    @service_tier_override('priority')
    def skill_to_tdd_plan(self, skill_markdown, section_map):
        return super().skill_to_tdd_plan(skill_markdown, section_map)

    @model_override('gpt-5.6-luna')
    @reasoning_effort_override('low')
    @service_tier_override('priority')
    def skill_to_section_tests(self, skill_markdown, tdd_plan, section_map):
        return super().skill_to_section_tests(skill_markdown, tdd_plan, section_map)

    @model_override('gpt-5.6-luna')
    def judge_section_tests(self, skill_markdown, section_map, section_tests):
        return super().judge_section_tests(skill_markdown, section_map, section_tests)

