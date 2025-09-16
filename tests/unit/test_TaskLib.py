import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from conversationgenome.task.TaskLib import TaskLib

@pytest.mark.asyncio
@patch("conversationgenome.task.TaskLib.ApiLib")
@patch("conversationgenome.task.TaskLib.c")
@patch("conversationgenome.task.TaskLib.CGP_VERSION", "1.2.3")
async def test_put_task_basic(mock_c, mock_ApiLib):
    # Setup config mock
    mock_c.get.side_effect = lambda section, key: {
        ("env", "LLM_TYPE_OVERRIDE"): None,
        ("env", "OPENAI_MODEL"): "gpt-4",
        ("env", "SYSTEM_MODE"): "test",
        ("env", "MARKER_ID"): "marker123",
        ("env", "LLM_TYPE"): "openai",
        ("system", "scoring_version"): "v1",
        ("system", "netuid"): 42,
        ("env", "OPENAI_EMBEDDINGS_MODEL_OVERRIDE"): None,
    }[(section, key)]

    # Setup ApiLib mock
    mock_api_instance = MagicMock()
    mock_api_instance.put_task_data = AsyncMock(return_value={"status": "ok"})
    mock_ApiLib.return_value = mock_api_instance

    task_lib = TaskLib()
    result = await task_lib.put_task(
        hotkey="hk1",
        task_bundle_id="tbid1",
        task_id="tid1",
        neuron_type="typeA",
        batch_number=7,
        data={"foo": "bar"}
    )

    assert result == {"status": "ok"}
    mock_api_instance.put_task_data.assert_awaited_once()
    args, kwargs = mock_api_instance.put_task_data.call_args
    assert args[0] == "tbid1"
    output = args[1]
    assert output["hotkey"] == "hk1"
    assert output["task_id"] == "tid1"
    assert output["neuron_type"] == "typeA"
    assert output["batch_number"] == 7
    assert output["model"] == "gpt-4"
    assert output["embeddings_model"] == "text-embedding-3-large"
    assert output["cgp_version"] == "1.2.3"
    assert output["data"] == {"foo": "bar"}

@pytest.mark.asyncio
@patch("conversationgenome.task.TaskLib.ApiLib")
@patch("conversationgenome.task.TaskLib.c")
@patch("conversationgenome.task.TaskLib.CGP_VERSION", "2.0.0")
async def test_put_task_with_overrides(mock_c, mock_ApiLib):
    # Setup config mock with overrides
    mock_c.get.side_effect = lambda section, key: {
        ("env", "LLM_TYPE_OVERRIDE"): "anthropic",
        ("env", "ANTHROPIC_MODEL"): "claude-3",
        ("env", "SYSTEM_MODE"): "prod",
        ("env", "MARKER_ID"): "marker999",
        ("env", "LLM_TYPE"): "anthropic",
        ("system", "scoring_version"): "v2",
        ("system", "netuid"): 99,
        ("env", "OPENAI_EMBEDDINGS_MODEL_OVERRIDE"): "custom-embedder",
    }[(section, key)]

    mock_api_instance = MagicMock()
    mock_api_instance.put_task_data = AsyncMock(return_value={"status": "success"})
    mock_ApiLib.return_value = mock_api_instance

    task_lib = TaskLib()
    result = await task_lib.put_task(
        hotkey="hk2",
        task_bundle_id="tbid2",
        task_id="tid2",
        neuron_type="typeB",
        batch_number=3,
        data=[1, 2, 3]
    )

    assert result == {"status": "success"}
    args, kwargs = mock_api_instance.put_task_data.call_args
    output = args[1]
    assert output["model"] == "claude-3"
    assert output["embeddings_model"] == "custom-embedder"
    assert output["llm_type"] == "anthropic"
    assert output["cgp_version"] == "2.0.0"
    assert output["data"] == [1, 2, 3]