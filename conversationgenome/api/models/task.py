from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, ValidationError


class ConversationInputData(BaseModel):
    participants: List[str]
    lines: List[Tuple[int, str]]
    total: int


class WebpageMarkdownInputData(BaseModel):
    markdown: List[Tuple[int, str]]


class ConversationInput(BaseModel):
    input_type: Literal["conversation"]
    guid: int
    data: ConversationInputData


class WebpageMarkdownInput(BaseModel):
    input_type: Literal["webpage_markdown"]
    guid: int
    data: WebpageMarkdownInputData


InputUnion = Union[ConversationInput, WebpageMarkdownInput]  # Extend with more types as needed


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


ExampleOutputUnion = Union[TaggingExampleOutput]  # Extend with more types as needed


class Task(BaseModel):
    mode: str
    api_version: float = 1.4
    job_type: Optional[str] = None
    scoring_mechanism: Optional[str] = None
    input: Optional[InputUnion] = None
    prompt_chain: Optional[List[PromptChainStep]] = None
    example_output: Optional[ExampleOutputUnion] = None
    errors: List[Any]
    warnings: List[Any]

    total: int = 0
    guid: int = 0
    participants: List[str] = []
    lines: List[Tuple[int, str]] = []
    prompts: Dict[str, Any] = {}
    data_type: int = 1
    
    @classmethod
    def from_api(cls, payload: Dict[str, Any]) -> Optional["Task"]:
        try:
            task = cls.model_validate(payload)
        except ValidationError as e:
            print(f"Task payload validation failed: {e}\nPayload: {payload}")
            return None

        return task