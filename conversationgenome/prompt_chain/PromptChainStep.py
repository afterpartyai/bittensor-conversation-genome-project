from pydantic import BaseModel


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
