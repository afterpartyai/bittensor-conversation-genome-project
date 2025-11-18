    
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.llm.prompt_manager import prompt_manager
from conversationgenome.utils import Utils

class LlmLib(ABC):
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
