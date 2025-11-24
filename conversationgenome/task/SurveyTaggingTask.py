from typing import Literal, Optional

import bittensor as bt
from pydantic import BaseModel
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.task.Task import Task


class SurveyTaggingTaskInputData(BaseModel):
    survey_question: Optional[str] = None
    comment: Optional[str] = None

class SurveyTaggingTaskInput(BaseModel):
    guid: str
    input_type: Literal["survey"]
    data: SurveyTaggingTaskInputData

class SurveyTaggingTask(Task):
    type: Literal["survey_tagging"] = "survey_tagging"
    input: Optional[SurveyTaggingTaskInput] = None

    async def mine(self) -> dict[str, list]:
        try:
            llml = get_llm_backend()
            res = llml.survey_to_metadata(self.input.data.survey_question, self.input.data.comment)
            return {"tags": res.tags, "vectors": res.vectors}
        
        except Exception as e:
            bt.logging.error(f"Error during mining: {e}")
            raise e
