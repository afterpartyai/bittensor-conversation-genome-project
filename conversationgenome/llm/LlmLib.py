from abc import ABC, abstractmethod
import functools
import json
import random
from typing import List

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationMetadata, ConversationQualityMetadata
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.llm.prompt_manager import prompt_manager
from conversationgenome.utils.Utils import Utils

class LlmLib(ABC):
    client = None
    model = None
    embedding_model = None

    ###############################################################################################
    ###################################### Abstract methods #######################################
    ###############################################################################################
    @abstractmethod
    def basic_prompt(self, prompt: str, response_format: str = "text") -> str:
        """
        Sends a prompt to the LLM and returns the text response.
        response_format can be 'text' or 'json'.
        """
        pass

    @abstractmethod
    def get_vector_embeddings(self, tag: str) -> List[float]:
        """
        Takes a list of strings (tags) and returns a list of vector embeddings.
        """
        pass

    ###############################################################################################
    ###################################### Concrete methods #######################################
    ###############################################################################################
    def get_vector_embeddings_set(self, tags: List[str]) -> List[List[float]]:
        """
        Takes a list of strings (tags) and returns a list of vector embeddings.
        """
        originalTags = tags
        tags = Utils.get_clean_tag_set(originalTags)
        tagVectorDict = {}
        for tag in tags:
            vectors = self.get_vector_embeddings(tag)
            if not vectors:
                tagVectorDict[tag] = {"vectors": []}
                print(f"ERROR -- no vectors for tag: {tag} vector response: {vectors}")
            else:
                tagVectorDict[tag] = {"vectors": vectors}
        return tagVectorDict

    ###############################################################################################
    ########################################## Prompts ############################################
    ###############################################################################################
    def conversation_to_metadata(self, conversation: Conversation, generateEmbeddings=False) -> RawMetadata|None:
        convo_xml, participants = Utils.generate_convo_xml(conversation)
        prompt = prompt_manager.conversation_to_metadata_prompt(convo_xml)
        response_content = self.basic_prompt(prompt)

        if not isinstance(response_content, str):
            print("Error: Unexpected response format. Content type:", type(response_content))
            return None
        
        tags = Utils.clean_tags(response_content.split(","))
        if Utils.empty(tags):
            print("No tags returned by OpenAI")
            return None
        
        vectors = None
        if generateEmbeddings:
            vectors = self.get_vector_embeddings_set(tags)

        return RawMetadata(tags=tags, vectors=vectors, success=True)

    def survey_to_metadata(self, survey_question: str, comment:str) -> RawMetadata|None:
        prompt = prompt_manager.survey_tag_prompt(survey_question, comment)
        response_content = self.basic_prompt(prompt)
        if not isinstance(response_content, str):
            print("Error: Unexpected response format. Content type:", type(response_content))
            return None
        try:
            tags = Utils.clean_tags(response_content.split(","))
            vectors = self.get_vector_embeddings_set(tags)
        except Exception as e:
            print("Error: Error generating vectors")
            return None
        return RawMetadata(tags=tags, vectors=vectors, success=True)

    def validate_conversation_quality(self, conversation: Conversation) -> ConversationQualityMetadata | None:
        conversation_xml, _ = Utils.generate_convo_xml(conversation)
        prompt = prompt_manager.conversation_quality_prompt(transcript_text=conversation_xml)
        response_content = self.basic_prompt(prompt, response_format="json")
        try:
            return ConversationQualityMetadata(**json.loads(response_content))
        except json.JSONDecodeError as e:
            print("Error parsing LLM reply as ConversationQualityMetadata")
            return None
        
    def validate_tag_set(self, tags: List[str]) -> List[str] | None:
        clean_tag_list = Utils.get_clean_tag_set(tags)
        if len(clean_tag_list) >= 20:
            random_indices = random.sample(range(len(clean_tag_list)), 20)
            clean_tag_list = [clean_tag_list[i] for i in random_indices]
        clean_tag_list = [tag[:50] for tag in clean_tag_list]
        prompt = prompt_manager.validate_tags_prompt(clean_tag_list)
        response_content = self.basic_prompt(prompt)
        if len(response_content) == 0:
            print(f"EMPTY RESPONSE -- no valid tags: {response_content}")
            return None
        
        content_str = response_content.lower()
        malformed_pos = content_str.find("malformed")
        good_keywords_str = content_str[0:malformed_pos].replace("good english keywords:", "").replace("***", "").replace("\n", "").strip()
        valid_tags = good_keywords_str.split(",")
        valid_tags = Utils.get_clean_tag_set(valid_tags)
        return [element for element in valid_tags if element in tags]
        

###############################################################################################
##################################### Override decorators #####################################
###############################################################################################
# Used to override default model/embedding-model for specific prompts/functions
# Takes a model name as an argument and sets it temporarily
def model_override(model_name: str):
    def decorator_model_override(func):
        @functools.wraps(func)
        def wrapper(self: LlmLib, *args, **kwargs):
            default_model = self.model
            self.model = model_name
            try:
                res = func(self, *args, **kwargs)
            finally:
                self.model = default_model
            return res
        return wrapper
    return decorator_model_override

def embedding_model_override(embedding_model_name: str):
    def decorator_model_override(func):
        @functools.wraps(func)
        def wrapper(self: LlmLib, *args, **kwargs):
            default_model = self.embedding_model
            self.embedding_model = embedding_model_name
            try:
                res = func(self, *args, **kwargs)
            finally:
                self.model = default_model
            return res
        return wrapper
    return decorator_model_override
