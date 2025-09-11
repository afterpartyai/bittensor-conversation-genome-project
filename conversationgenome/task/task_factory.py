from __future__ import annotations

from typing import Annotated, Any, Dict, Optional, Union

from pydantic import Field, TypeAdapter, ValidationError

from conversationgenome.task.Task import Task

_TASK_ADAPTER: Optional[TypeAdapter] = None


def _get_adapter() -> TypeAdapter:
    global _TASK_ADAPTER
    if _TASK_ADAPTER is not None:
        return _TASK_ADAPTER

    # ------------- Hardcoded imports / union -------------
    from conversationgenome.task.ConversationTaggingTask import ConversationTaggingTask
    from conversationgenome.task.MarkdownMetadataGenerationTask import WebpageMetadataGenerationTask

    TaskUnion = Annotated[
        Union[ConversationTaggingTask, WebpageMetadataGenerationTask],
        Field(discriminator="job_type"),
    ]
    _TASK_ADAPTER = TypeAdapter(TaskUnion)
    return _TASK_ADAPTER


def parse_task(payload: Dict[str, Any]):
    return _get_adapter().validate_python(payload)


def try_parse_task(payload: Dict[str, Any]) -> Optional[Task]:
    try:
        return parse_task(payload)
    except ValidationError as e:
        print(f"Validation error: {e}")
        return None
