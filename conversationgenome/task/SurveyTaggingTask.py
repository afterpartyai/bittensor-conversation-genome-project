from typing import Literal, Optional

import bittensor as bt
from pydantic import BaseModel
from conversationgenome.task.Task import Task
from conversationgenome.utils.constants import TaskType
from conversationgenome.llm.LlmLib import LlmLib


class SurveyTaggingTaskInput(BaseModel):
    guid: str
    input_type: Literal["survey"]
    # Main attributes
    survey_question: Optional[str] = None
    comment: Optional[str] = None

class SurveyTaggingTask(Task):
    type: Literal["survey_tagging"] = "survey_tagging"
    input: Optional[SurveyTaggingTaskInput] = None

    async def mine(self) -> dict[str, list]:
        try:
            llml = LlmLib()
            res = await llml.survey_to_metadata(self.input.survey_question, self.input.comment)
            return {"tags": res.tags, "vectors": res.vectors}
        
        except Exception as e:
            bt.logging.error(f"Error during mining: {e}")
            raise e
