import pytest
from pydantic import ValidationError

import conversationgenome.miner.MinerLib as miner_mod
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.miner.MinerLib import MinerLib

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

    monkeypatch.setattr(miner_mod, "LlmLib", lambda: FakeLlm(sink))

    miner = MinerLib()

    out = await miner.do_mining(
        conversation_guid="g1",
        window_idx=0,
        conversation_window=lines,
        minerUid=42,
        task_prompt=prompt,
        dryrun=False,
    )

    assert out["tags"] == tags
    assert out["vectors"] == vectors

    assert len(sink["calls"]) == 1

    _, kwargs = sink["calls"][0]
    assert kwargs.get("generateEmbeddings") is False


@pytest.mark.asyncio
async def test_given_bad_lines_inputs_then_throw_validation_error():
    miner = MinerLib()
    with pytest.raises(ValidationError):
        await miner.do_mining(
            conversation_guid="g1",
            window_idx=0,
            conversation_window=None,  # not a proper list of tuples
            minerUid=1,
            task_prompt="prompt",
            dryrun=False,
        )


@pytest.mark.asyncio
async def test_given_bad_prompt_inputs_then_throw_validation_error():
    miner = MinerLib()
    with pytest.raises(ValidationError):
        await miner.do_mining(
            conversation_guid="g1",
            window_idx=0,
            conversation_window=lines,
            minerUid=1,
            task_prompt=123456,
            dryrun=False,
        )
