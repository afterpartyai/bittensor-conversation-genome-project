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

        try:
            conversation = Conversation(
                guid=self.input.guid,
                lines=self.input.data.window,
                miner_task_prompt=self.prompt_chain[0].prompt_template,
            )

            result = llml.conversation_to_metadata(conversation=conversation, generateEmbeddings=False)
            output = {"tags": result.tags, "vectors": result.vectors}
        except Exception as e:
            bt.logging.error(f"Error during mining: {e}")
            raise e

        return output
