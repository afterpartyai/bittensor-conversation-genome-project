from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.task.Task import Task


class ConversationTaskInputData(BaseModel):
    participants: List[str]
    window_idx: int = -1
    window: Optional[List[Tuple[int, str]]] = None


class ConversationTaskInput(BaseModel):
    guid: str
    input_type: Literal["conversation"]
    data: ConversationTaskInputData


class ConversationTaggingTask(Task):
    type: Literal["conversation_tagging"] = "conversation_tagging"
    input: Optional[ConversationTaskInput] = None

    async def mine(self) -> dict[str, list]:
        llml = LlmLib()

        try:
            conversation = Conversation(
                guid=self.input.guid,
                lines=self.input.data.window,
                participants=self.input.data.participants,
                miner_task_prompt=self.prompt_chain[0].prompt_template,
            )

            result = await llml.conversation_to_metadata(conversation=conversation, generateEmbeddings=False)
            output = {"tags": result.tags, "vectors": result.vectors}
        except Exception as e:
            bt.logging.error(f"Error during mining: {e}")
            raise e

        return output
