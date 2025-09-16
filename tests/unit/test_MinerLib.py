import uuid
from asyncio import Task

import pytest
from pydantic import ValidationError

import conversationgenome.task.ConversationTaggingTask as ctt
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.miner.default_prompts import get_task_default_prompt
from conversationgenome.miner.MinerLib import MinerLib
from tests.mocks.DummyData import DummyData

lines = [(0, "hello"), (1, "world")]
prompt = "Analyze the convo and tag fruits only."
tags = ["apple", "banana"]
vectors = {"apple": {"vector": [0.1]}, "banana": {"vector": [0.2]}}


class FakeLlm:
    def __init__(self, sink):
        self.sink = sink

    async def conversation_to_metadata(self, *args, **kwargs):
        self.sink["calls"].append((args, kwargs))
        conversation = ConversationMetadata(tags=tags, vectors=vectors)
        return conversation


@pytest.mark.asyncio
async def test_given_proper_inputs_then_conversation_metadata_is_returned(monkeypatch):
    sink = {"calls": []}

    monkeypatch.setattr(ctt, "LlmLib", lambda: FakeLlm(sink))

    miner = MinerLib()

    out = await miner.do_mining(task=DummyData.conversation_tagging_task())

    assert out["tags"] == tags
    assert out["vectors"] == vectors

    assert len(sink["calls"]) == 1

    _, kwargs = sink["calls"][0]
    assert kwargs.get("generateEmbeddings") is False


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
