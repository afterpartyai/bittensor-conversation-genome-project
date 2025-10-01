from typing import List

from pydantic import BaseModel
from typing_extensions import Literal


class TaggingExampleOutput(BaseModel):
    tags: List[str]
    type: Literal["List[str]"]
