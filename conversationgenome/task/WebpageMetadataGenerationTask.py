from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.task.Task import Task


class WebpageMarkdownTaskInputData(BaseModel):
    min_convo_windows: int = 0
    participants: List[str]
    prompt: str
    window: List[Tuple[int, str]]


class WebpageMarkdownTaskInput(BaseModel):
    input_type: Literal["webpage_markdown"]
    data: WebpageMarkdownTaskInputData


class WebpageMetadataGenerationTask(Task):
    type: Literal["webpage_metadata_generation"] = "webpage_metadata_generation"
    input: Optional[WebpageMarkdownTaskInput] = None

    async def mine(self) -> dict[str, list]:
        llml = LlmLib()

        conversation = Conversation(
            guid="HIDDEN",
            lines=self.input.data.window,
            participants=["UNKNOWN_SPEAKER"],
            miner_task_prompt=self.prompt_chain[0].prompt_template,
        )

        result = await llml.conversation_to_metadata(conversation=conversation, generateEmbeddings=False)

        return {"tags": result.tags, "vectors": result.vectors}
