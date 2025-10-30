from typing import Literal, Optional

from pydantic import BaseModel
from conversationgenome.task.Task import Task
from conversationgenome.utils.constants import TaskType


class SurveyTaggingTaskInput(BaseModel):
    guid: str
    input_type: Literal["survey_tagging"]
    # Main attributes
    survey_question: Optional[str] = None
    comment: Optional[str] = None

class SurveyTaggingTask(Task):
    type: TaskType = "survey_tagging"
    input: Optional[SurveyTaggingTaskInput] = None

    async def mine(self) -> dict[str, list]:
        raise NotImplementedError('Currently no miner for Survey task')
