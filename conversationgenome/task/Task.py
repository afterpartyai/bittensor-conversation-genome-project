from abc import ABC, abstractmethod
from typing import Any, List, Optional

from pydantic import BaseModel

from conversationgenome.prompt_chain.PromptChainStep import PromptChainStep
from conversationgenome.scoring_mechanism.example_output_union import ExampleOutputUnion
from conversationgenome.utils.constants import TaskType
from conversationgenome.utils.types import ForceStr


# ---------- Base task ----------
class Task(BaseModel, ABC):
    mode: str
    api_version: float = 1.4
    guid: Optional[ForceStr] = None
    bundle_guid: Optional[ForceStr] = None
    type: TaskType
    scoring_mechanism: Optional[str] = None
    input: Any = None
    prompt_chain: Optional[List[PromptChainStep]] = None
    example_output: Optional[ExampleOutputUnion] = None

    @abstractmethod
    async def mine(self) -> dict[str, list]:
        pass
