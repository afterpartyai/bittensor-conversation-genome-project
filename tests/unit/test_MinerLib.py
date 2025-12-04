from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest
from pydantic import ValidationError

import conversationgenome.task.ConversationTaggingTask as ctt
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.miner.MinerLib import MinerLib
from tests.mocks.DummyData import DummyData

lines = [(0, "hello"), (1, "world")]
prompt = "Analyze the convo and tag fruits only."
tags = ["apple", "banana"]
vectors = {"apple": {"vector": [0.1]}, "banana": {"vector": [0.2]}}



@pytest.mark.asyncio
async def test_given_proper_inputs_then_conversation_metadata_is_returned():
    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = tags
    mock_result.vectors = vectors
    mock_llml.conversation_to_metadata = Mock(return_value=mock_result)
    with patch("conversationgenome.task.ConversationTaggingTask.get_llm_backend", return_value=mock_llml):
        miner = MinerLib()
        task = DummyData.conversation_tagging_task()
        task.prompt_chain = [type("Prompt", (), {"prompt_template": "Tag the conversation."})()]
        out = await miner.do_mining(task=task)

        assert out["tags"] == tags
        assert out["vectors"] == vectors


@pytest.mark.asyncio
async def test_given_empty_task_then_throw_validation_error():
    miner = MinerLib()
    with pytest.raises(ValidationError):
        await miner.do_mining(task=ctt.ConversationTaggingTask())


@pytest.mark.asyncio
async def test_given_task_with_missing_fields_then_throw_validation_error():
    miner = MinerLib()
    # Only provide 'conversation', omit other required fields
    with pytest.raises(ValidationError):
        await miner.do_mining(task=ctt.ConversationTaggingTask(conversation=lines))


@pytest.mark.asyncio
async def test_given_task_with_invalid_types_then_throw_validation_error():
    miner = MinerLib()
    # Provide invalid types for fields
    with pytest.raises(ValidationError):
        await miner.do_mining(task=ctt.ConversationTaggingTask(conversation="not_a_list", prompt=123))
