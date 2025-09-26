from unittest.mock import AsyncMock

import pytest

from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.validator.ValidatorLib import ValidatorLib
from tests.mocks.DummyData import DummyData


@pytest.fixture
def validator():
    return ValidatorLib()


@pytest.mark.asyncio
async def test_when_reserving_then_task_bundle_returned(monkeypatch, validator):
    monkeypatch.setattr(validator, "get_task_bundle", AsyncMock(return_value=DummyData.conversation_tagging_task_bundle()))

    result = await validator.reserve_task_bundle()

    assert result is not None
    assert isinstance(result, TaskBundle)


@pytest.mark.asyncio
async def test_when_no_conversation_then_none_reserved(monkeypatch, validator):
    monkeypatch.setattr(validator, "get_task_bundle", AsyncMock(return_value=None))

    result = await validator.reserve_task_bundle()

    assert result is None
