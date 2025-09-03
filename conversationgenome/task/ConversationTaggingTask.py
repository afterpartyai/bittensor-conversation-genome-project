from typing import Any, List, Literal, Optional, Tuple

from pydantic import BaseModel

from conversationgenome.task.Task import Task
from conversationgenome.utils.types import ForceStr


class ConversationInputData(BaseModel):
    participants: List[str]
    lines: List[Tuple[int, str]]
    total: int
    min_convo_windows: int = 1
    indexed_windows: Optional[List[Tuple[int, List[Tuple[int, str]]]]] = None


class ConversationInput(BaseModel):
    input_type: Literal["conversation"]
    guid: ForceStr
    data: ConversationInputData

    def trim_input(self, max_lines: int) -> None:
        if max_lines and len(self.data.lines) > max_lines:
            self.data.lines = self.data.lines[:max_lines]
            self.data.total = len(self.data.lines)


class ConversationTaggingTask(Task):
    job_type: Literal["conversation_tagging"] = "conversation_tagging"
    input: Optional[ConversationInput] = None
