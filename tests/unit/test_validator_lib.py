import copy
from unittest.mock import AsyncMock, MagicMock

import pytest

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.validator.ValidatorLib import ValidatorLib

fake_conversation = Conversation(guid="test-guid", lines=[[0, "Hello"], [1, "Hi there"]], participants=["SPEAKER_00", "SPEAKER_01"])
fake_windows = [(0, "bye"), (1, "bye")]
fake_metadata = ConversationMetadata(participantProfiles=["SPEAKER_00", "SPEAKER_01"], tags=["risk", "security"], vectors={"risk": {"vectors": [0.1, 0.2, 0.3]}})


@pytest.fixture
def validator():
    return ValidatorLib()


@pytest.mark.asyncio
async def test_when_conversation_then_is_properly_reserved(monkeypatch, validator):
    monkeypatch.setattr(validator, "getConvo", AsyncMock(return_value=copy.deepcopy(fake_conversation)))
    monkeypatch.setattr(validator, "getConvoWindows", MagicMock(return_value=copy.deepcopy(fake_windows)))

    result = await validator.reserve_conversation()

    assert result is not None
    assert result.guid == fake_conversation.guid
    assert result.windows == fake_windows


@pytest.mark.asyncio
async def test_when_no_conversation_then_none_reserved(monkeypatch, validator):
    monkeypatch.setattr(validator, "getConvo", AsyncMock(return_value=None))

    get_convo_windows_mock = AsyncMock()
    monkeypatch.setattr(validator, "getConvoWindows", get_convo_windows_mock)

    result = await validator.reserve_conversation()

    assert result is None
    get_convo_windows_mock.assert_not_called()


@pytest.mark.asyncio
async def test_when_windows_less_than_minimum_then_no_conversation_reserved(monkeypatch, validator):
    monkeypatch.setattr(validator, "getConvo", AsyncMock(return_value=copy.deepcopy(fake_conversation)))
    monkeypatch.setattr(validator, "getConvoWindows", MagicMock(return_value=copy.deepcopy(fake_windows)))

    result = await validator.reserve_conversation(minConvWindows=1000)

    assert result is None


@pytest.mark.asyncio
async def test_when_return_indexed_windows_then_attribute_exists(monkeypatch, validator):
    monkeypatch.setattr(validator, "getConvo", AsyncMock(return_value=copy.deepcopy(fake_conversation)))
    monkeypatch.setattr(validator, "getConvoWindows", MagicMock(return_value=copy.deepcopy(fake_windows)))

    result: Conversation = await validator.reserve_conversation(return_indexed_windows=True)

    assert result is not None
    assert result.indexed_windows == fake_windows
    assert result.windows is None


@pytest.mark.asyncio
async def test_when_not_return_indexed_windows_then_attribute_doesnt_exist(monkeypatch, validator):
    monkeypatch.setattr(validator, "getConvo", AsyncMock(return_value=copy.deepcopy(fake_conversation)))
    monkeypatch.setattr(validator, "getConvoWindows", MagicMock(return_value=copy.deepcopy(fake_windows)))

    result: Conversation = await validator.reserve_conversation(return_indexed_windows=False)

    assert result is not None
    assert result.windows == fake_windows
    assert result.indexed_windows is None


@pytest.mark.asyncio
async def test_when_no_conversation_metadata_then_none_returned(monkeypatch, validator):
    monkeypatch.setattr(validator, "generate_full_convo_metadata", AsyncMock(return_value=None))

    put_convo_mock = AsyncMock()
    monkeypatch.setattr(validator, "put_convo", put_convo_mock)

    result = await validator.get_convo_metadata(conversation_guid=fake_conversation.guid, full_conversation=fake_conversation, batch_num=100000)

    assert result is None
    put_convo_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_when_conversation_metadata_then_properly_returned(monkeypatch, validator):
    monkeypatch.setattr(validator, "generate_full_convo_metadata", AsyncMock(return_value=fake_metadata))

    put_convo_mock = AsyncMock()
    monkeypatch.setattr(validator, "put_convo", put_convo_mock)

    result = await validator.get_convo_metadata(conversation_guid=fake_conversation.guid, full_conversation=fake_conversation, batch_num=100000)

    assert result == fake_metadata
    put_convo_mock.assert_not_awaited()
