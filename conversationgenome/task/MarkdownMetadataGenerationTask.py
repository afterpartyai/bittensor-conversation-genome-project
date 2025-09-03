from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel

from conversationgenome.task.Task import Task
from conversationgenome.utils.types import ForceStr


class WebpageMarkdownInputData(BaseModel):
    participants: List[str]
    lines: List[Tuple[int, str]]
    total: int
    min_convo_windows: int = 0
    indexed_windows: Optional[List[Tuple[int, List[Tuple[int, str]]]]] = None


class WebpageMarkdownInput(BaseModel):
    input_type: Literal["webpage_markdown"]
    guid: ForceStr
    data: WebpageMarkdownInputData

    def trim_input(self, max_lines: int) -> None:
        if max_lines and len(self.data.lines) > max_lines:
            self.data.lines = self.data.lines[:max_lines]
            self.data.total = len(self.data.lines)


class WebpageMetadataGenerationTask(Task):
    job_type: Literal["webpage_metadata_generation"] = "webpage_metadata_generation"
    input: Optional[WebpageMarkdownInput] = None