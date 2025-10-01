from abc import ABC
from abc import abstractmethod
from copy import deepcopy
from typing import Any
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from conversationgenome.prompt_chain.PromptChainStep import PromptChainStep
from conversationgenome.scoring_mechanism.example_output_union import ExampleOutputUnion
from conversationgenome.task.Task import Task
from conversationgenome.utils.constants import TaskType
from conversationgenome.utils.types import ForceStr


# ---------- Base task bundle ----------
class TaskBundle(BaseModel, ABC):
    mode: str
    api_version: float = 1.4
    guid: Optional[ForceStr] = None
    type: TaskType
    scoring_mechanism: Optional[str] = None
    input: Any = None
    prompt_chain: Optional[List[PromptChainStep]] = None
    example_output: Optional[ExampleOutputUnion] = None
    errors: List[Any] = Field(default_factory=list)
    warnings: List[Any] = Field(default_factory=list)

    @abstractmethod
    def is_ready(self) -> bool:
        """
        Returns True if the bundle is fully set up and ready for use.
        The condition for readiness should be implemented by each subclass.
        """
        pass

    @abstractmethod
    async def setup(self) -> None:
        pass

    @abstractmethod
    def to_mining_tasks(self, number_of_tasks_per_bundle: int) -> List[Task]:
        pass

    @abstractmethod
    def generate_result_logs(self, miner_result) -> str:
        pass

    @abstractmethod
    def format_results(self, miner_result) -> Any:
        pass

    @abstractmethod
    def evaluate(self, miner_responses):
        pass

    def mask_task_for_miner(self, task: Task) -> Task:
        masked_task = deepcopy(task)

        HIDDEN_GUID = "HIDDEN"
        masked_task.bundle_guid = HIDDEN_GUID
        masked_task.guid = HIDDEN_GUID
        masked_task.input.guid = HIDDEN_GUID

        return masked_task
