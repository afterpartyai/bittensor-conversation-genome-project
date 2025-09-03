from abc import ABC
from typing import Any, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field

from conversationgenome.utils.types import ForceStr



class PromptChainStep(BaseModel):
    step: int
    id: str
    crc: int
    title: str
    name: str
    description: str
    type: str
    input_path: str
    prompt_template: str
    output_variable: str
    output_type: str


class TaggingExampleOutput(BaseModel):
    tags: List[str]
    type: Literal["List[str]"]


ExampleOutputUnion = Union[TaggingExampleOutput]


# ---------- Base task + specializations ----------
class Task(BaseModel, ABC):
    mode: str
    api_version: float = 1.4
    job_type: str
    scoring_mechanism: Optional[str] = None
    input: Any = None
    prompt_chain: Optional[List[PromptChainStep]] = None
    example_output: Optional[ExampleOutputUnion] = None
    errors: List[Any] = Field(default_factory=list)
    warnings: List[Any] = Field(default_factory=list)

    # Until the migration to Tasks is done. We keep the legacy fields
    guid: ForceStr
    total: int
    participants: List[str]
    lines: List[Tuple[int, str]]
    min_convo_windows: int = 1

    def trim(self, max_lines: int) -> None:
        if self.input and hasattr(self.input, "trim_input"):
            self.input.trim_input(max_lines)
