from __future__ import annotations

from typing import Annotated
from typing import Any
from typing import Dict
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import TypeAdapter
from pydantic import ValidationError

from conversationgenome.task.Task import Task

_TASK_ADAPTER: Optional[TypeAdapter] = None


def _get_task_adapter() -> TypeAdapter:
    global _TASK_ADAPTER
    if _TASK_ADAPTER is not None:
        return _TASK_ADAPTER

    # ------------- Hardcoded imports / union -------------
    from conversationgenome.task.ConversationTaggingTask import ConversationTaggingTask
    from conversationgenome.task.WebpageMetadataGenerationTask import WebpageMetadataGenerationTask
    from conversationgenome.task.SurveyTaggingTask import SurveyTaggingTask

    

    TaskUnion = Annotated[
        Union[ConversationTaggingTask, WebpageMetadataGenerationTask, SurveyTaggingTask],
        Field(discriminator="type"),
    ]
    _TASK_ADAPTER = TypeAdapter(TaskUnion)
    return _TASK_ADAPTER


def parse_task(payload: Dict[str, Any]):
    return _get_task_adapter().validate_python(payload)


def try_parse_task(payload: Dict[str, Any]) -> Optional[Task]:
    try:
        return parse_task(payload)
    except ValidationError as e:
        print(f"Validation error: {e}")
        return None
