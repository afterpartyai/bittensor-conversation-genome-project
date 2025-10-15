from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel
import bittensor as bt

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.task.Task import Task
from conversationgenome.utils.constants import TaskType


class SurveyTaggingTaskInputData(BaseModel):
    window: List[Tuple[int, str]]
    participants: Optional[List[str]] = None

class SurveyTaggingTaskInput(BaseModel):
    guid: str
    input_type: Literal["survey_tagging"]
    data: SurveyTaggingTaskInputData

# TODO Jordan - This is currently identical to ConversationTaggingTask. Consider merging or differentiating.
class SurveyTaggingTask(Task):
    type: TaskType = "survey_tagging"
    input: Optional[SurveyTaggingTaskInput] = None

    async def mine(self) -> dict[str, list]:
        llml = LlmLib()
        try:
            assert self.prompt_chain is not None, "Prompt chain must be defined"
            assert self.input is not None, "Input must be provided"

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
