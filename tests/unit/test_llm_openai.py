from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import conversationgenome.llm.llm_openai as mod
from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.raw_metadata import RawMetadata
from conversationgenome.llm.llm_openai import llm_openai
from conversationgenome.utils.Utils import Utils

lines = [(0, "this is the life of the little masquerader"), (1, "oh yeah. this story is pretty great if you ask me")]
prompt = "Analyze the convo and tag fruits only."
content = "whatever"

conversation = Conversation(guid="guid", lines=lines, miner_task_prompt=prompt)
(xml, participants) = Utils.generate_convo_xml(convo=conversation)

default_llm_prompt = "Analyze conversation in terms of topic interests of the participants. Analyze the conversation (provided in structured XML format) where <p0> has the questions and <p1> has the answers . Return comma-delimited tags.  Only return the tags without any English commentary."


@pytest.mark.asyncio
async def test_prompt_is_forwarded(monkeypatch):
    llm = llm_openai()

    # monkeypatch.setattr(llm, "call_llm_tag_function", AsyncMock(return_value=None))
    conversation = Conversation(guid="guid", lines=lines, miner_task_prompt=prompt)

    result = await llm.conversation_to_metadata(convo=conversation, generateEmbeddings=True)


@pytest.mark.asyncio
async def test_given_empty_responset_then_returns_none(monkeypatch):
    llm = llm_openai()

    monkeypatch.setattr(llm, "call_llm_tag_function", AsyncMock(return_value=None))
    conversation = Conversation(guid="guid", lines=lines, miner_task_prompt=prompt)

    result = await llm.conversation_to_metadata(convo=conversation, generateEmbeddings=True)

    assert result is None


@pytest.mark.asyncio
async def test_given_bad_content_then_returns_none(monkeypatch):
    llm = llm_openai()

    monkeypatch.setattr(llm, "call_llm_tag_function", AsyncMock(return_value={"success": True, "content": None}))
    conversation = Conversation(guid="guid", lines=lines, miner_task_prompt=prompt)

    result = await llm.conversation_to_metadata(convo=conversation, generateEmbeddings=True)

    assert result is None


@pytest.mark.asyncio
async def test_given_generate_embeddings_false_then_no_embeddings_returned():
    llm = llm_openai()

    conversation = Conversation(guid="guid", lines=lines, miner_task_prompt=prompt)

    result = await llm.conversation_to_metadata(convo=conversation, generateEmbeddings=False)

    assert result is not None
    assert result.vectors is None
    assert isinstance(result, RawMetadata)


@pytest.mark.asyncio
async def test_given_generate_embeddings_false_then_embeddings_returned():
    llm = llm_openai()

    conversation = Conversation(guid="guid", lines=lines, miner_task_prompt=prompt)

    result = await llm.conversation_to_metadata(convo=conversation, generateEmbeddings=True)

    assert result is not None
    assert result.vectors is not None
    assert isinstance(result, RawMetadata)


@pytest.mark.asyncio
async def test_given_specific_prompt_then_specific_prompt_is_passed(monkeypatch):
    llm = llm_openai()

    prompt_call_csv_mock = AsyncMock()
    monkeypatch.setattr(llm, "prompt_call_csv", prompt_call_csv_mock)

    await llm.call_llm_tag_function(convoXmlStr=xml, participants=participants, prompt=conversation.miner_task_prompt)

    prompt_call_csv_mock.assert_awaited_once()

    for _, call_args in prompt_call_csv_mock.await_args_list:
        assert "partial_prompt_override" in call_args
        assert call_args["partial_prompt_override"] == prompt


@pytest.mark.asyncio
async def test_given_override_prompt_then_specific_prompt_is_used(monkeypatch):
    monkeypatch.setattr(mod, "c", type("C", (), {"get": staticmethod(lambda sec, key, default=None: "0" if (sec, key) == ("env", "OPENAI_DIRECT_CALL") else "test")}))

    completion_mock = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    create_mock = AsyncMock(return_value=completion_mock)
    client_mock = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock)))
    monkeypatch.setattr(mod, "AsyncOpenAI", lambda: client_mock)

    llm = llm_openai()
    await llm.prompt_call_csv(convoXmlStr=xml, participants=participants, partial_prompt_override=prompt)

    create_mock.assert_awaited()

    for _, call_args in create_mock.await_args_list:
        used_prompt = call_args["messages"][0]["content"]

        assert used_prompt is not None
        assert isinstance(used_prompt, str)
        assert prompt in used_prompt
        assert xml in used_prompt


@pytest.mark.asyncio
async def test_given_no_override_prompt_then_default_prompt_is_used(monkeypatch):
    monkeypatch.setattr(mod, "c", type("C", (), {"get": staticmethod(lambda sec, key, default=None: "0" if (sec, key) == ("env", "OPENAI_DIRECT_CALL") else "test")}))

    completion_mock = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    create_mock = AsyncMock(return_value=completion_mock)
    client_mock = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock)))
    monkeypatch.setattr(mod, "AsyncOpenAI", lambda: client_mock)

    llm = llm_openai()
    await llm.prompt_call_csv(convoXmlStr=xml, participants=participants)

    create_mock.assert_awaited()

    for _, call_args in create_mock.await_args_list:
        used_prompt = call_args["messages"][0]["content"]

        assert used_prompt is not None
        assert isinstance(used_prompt, str)
        assert default_llm_prompt in used_prompt
        assert xml in used_prompt
