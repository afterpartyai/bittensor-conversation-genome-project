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
            all_tags = []
            # Process each line in the window
            for idx, (line_idx, content) in enumerate(self.input.data.window):
                if idx == 0:
                    # First line is always the main transcript content
                    result = llml.raw_transcript_to_named_entities(content, generateEmbeddings=False)
                else:
                    # Subsequent lines are enrichment content
                    result = llml.enrichment_to_NER(content, generateEmbeddings=False)

                if result and result.tags:
                    all_tags.append(result.tags)

            # Combine all tags from transcript and enrichment content
            if all_tags:
                combined_result = llml.combine_named_entities(all_tags, generateEmbeddings=False)
                output = {"tags": combined_result.tags if combined_result else [], "vectors": combined_result.vectors if combined_result else None}
            else:
                output = {"tags": [], "vectors": None}

        except Exception as e:
            bt.logging.error(f"Error during mining: {e}")
            raise e

        return output
