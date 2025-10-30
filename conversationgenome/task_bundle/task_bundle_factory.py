from __future__ import annotations

from typing import Annotated, Any, Dict, Optional, Union

from pydantic import Field, TypeAdapter, ValidationError

from conversationgenome.task_bundle.TaskBundle import TaskBundle

_TASK_BUNDLE_ADAPTER: Optional[TypeAdapter] = None


def _get_task_bundle_adapter() -> TypeAdapter:
    global _TASK_BUNDLE_ADAPTER
    if _TASK_BUNDLE_ADAPTER is not None:
        return _TASK_BUNDLE_ADAPTER

    # ------------- Hardcoded imports / union -------------
    from conversationgenome.task_bundle.ConversationTaggingTaskBundle import ConversationTaggingTaskBundle
    from conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle import WebpageMetadataGenerationTaskBundle
    from conversationgenome.task_bundle.SurveyTaggingTaskBundle import SurveyTaggingTaskBundle

    TaskBundleUnion = Annotated[
        Union[ConversationTaggingTaskBundle, WebpageMetadataGenerationTaskBundle, SurveyTaggingTaskBundle],
        Field(discriminator="type"),
    ]
    _TASK_BUNDLE_ADAPTER = TypeAdapter(TaskBundleUnion)
    return _TASK_BUNDLE_ADAPTER


def parse_task_bundle(payload: Dict[str, Any]):
    return _get_task_bundle_adapter().validate_python(payload)


def try_parse_task_bundle(payload: Dict[str, Any]) -> Optional[TaskBundle]:
    try:
        return parse_task_bundle(payload)
    except ValidationError as e:
        raise e
        print(f"Validation error: {e}")
        return None

