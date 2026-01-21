import json
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.task.Task import Task


class NamedEntitiesExtractionTaskInputData(BaseModel):
    window_idx: int = -1
    window: Optional[List[Tuple[int, str]]] = None
    participants: Optional[List[str]] = None


class NamedEntitiesExtractionTaskInput(BaseModel):
    guid: str
    input_type: Literal["document"]
    data: NamedEntitiesExtractionTaskInputData


class NamedEntitiesExtractionTask(Task):
    type: Literal["named_entities_extraction"] = "named_entities_extraction"
    input: Optional[NamedEntitiesExtractionTaskInput] = None

    async def mine(self) -> dict[str, list]:
        llml = get_llm_backend()

        if not len(self.input.data.window):
            bt.logging.warning('Received empty window in miner, returning no tags')
            return {"tags": []}
        
        try:
            transcript = self.input.data.window[0][1]
            if self.input.data.window[1:]:
                web_pages = [element[1] for element in self.input.data.window[1:]]
            else:
                # No enrichment provided
                web_pages = []

            tag_sets = []
            tag_sets.append(llml.raw_transcript_to_named_entities(transcript).tags)
            for page_contents in web_pages:
                tag_sets.append(llml.raw_webpage_to_named_entities(page_contents).tags)

            combined_tags = llml.combine_named_entities(tag_sets).tags

            output = {"tags": combined_tags}
        except Exception as e:
            bt.logging.error(f"Error during mining: {e}")
            raise e

        return output
