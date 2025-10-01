from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple

import bittensor as bt
from pydantic import BaseModel

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.task.Task import Task


class WebpageMarkdownTaskInputData(BaseModel):
    window: List[Tuple[int, str]]


class WebpageMarkdownTaskInput(BaseModel):
    guid: str
    input_type: Literal["webpage_markdown"]
    data: WebpageMarkdownTaskInputData


class WebpageMetadataGenerationTask(Task):
    type: Literal["webpage_metadata_generation"] = "webpage_metadata_generation"
    input: Optional[WebpageMarkdownTaskInput] = None

    async def mine(self) -> dict[str, list]:
        llml = LlmLib()

        try:
            conversation = Conversation(
                guid=self.input.guid,
                lines=self.input.data.window,
                miner_task_prompt=self.prompt_chain[0].prompt_template,
            )

            result = await llml.conversation_to_metadata(conversation=conversation, generateEmbeddings=False)
            output = {"tags": result.tags, "vectors": result.vectors}
        except Exception as e:
            bt.logging.error(f"Error during mining: {e}")
            raise e

        return output
