import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.mocks.MockTaskBundle import MockTaskBundle


@pytest.mark.asyncio
async def test_forward_returns_false_if_not_enough_tasks(bare_validator, fake_libs, monkeypatch):
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3
    fake_libs["vl"].reserve_task_bundle = AsyncMock(return_value=None)
    result = await validator.forward()
    assert result is False


@pytest.mark.asyncio
@patch("conversationgenome.api.ApiLib.c.get")
async def test_forward_respects_max_convo_lines(mock_config_get, bare_validator, fake_libs):
    # Override config values via config mock
    override_config = {
        ("validator", "minimum_number_of_tasks"): 10,
        ("validator", "max_convo_lines"): 2,  # Added this key for max_convo_lines
    }

    def config_side_effect(section, key, default=None):
        return override_config.get((section, key), default)

    mock_config_get.side_effect = config_side_effect

    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3

    async def reserve_task_bundle_side_effect():
        bundle = MockTaskBundle(num_tasks=override_config[("validator", "max_convo_lines")])
        max_lines = override_config[("validator", "max_convo_lines")]
        bundle.input.data.lines = bundle.input.data.lines[:max_lines]
        return bundle

    fake_libs["vl"].reserve_task_bundle = AsyncMock(side_effect=reserve_task_bundle_side_effect)
    fake_libs["vl"].put_task = AsyncMock()

    class DummyResponse:
        def __init__(self, hotkey):
            self.dendrite = MagicMock()
            self.dendrite.status_code = 200
            self.axon = MagicMock()
            self.axon.hotkey = hotkey
            self.cgp_output = [
                {
                    "result": "ok",
                    "hotkey": hotkey,
                    "adjustedScore": 1.0,
                    "final_miner_score": 1.0,
                    "tags": ["tag1", "tag2"],
                }
            ]

    validator.dendrite.forward = AsyncMock(side_effect=lambda axons, *_, **__: [DummyResponse(axon.hotkey) for axon in axons])
    result = await validator.forward(test_mode=True)
    assert result is True


@pytest.mark.asyncio
async def test_forward_handles_exception(bare_validator, fake_libs, monkeypatch):
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3
    fake_libs["vl"].reserve_task_bundle = AsyncMock(side_effect=Exception("fail"))
    result = await validator.forward()
    assert result is False


@pytest.mark.asyncio
async def test_forward_returns_false_if_not_enough_tasks(bare_validator, fake_libs, monkeypatch):
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3
    fake_libs["vl"].reserve_task_bundle = AsyncMock(return_value=None)
    result = await validator.forward()
    assert result is False


@pytest.mark.asyncio
async def test_forward_returns_true_with_enough_tasks(bare_validator, fake_libs, monkeypatch):
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3

    task_bundle_guid = "guid"

    # Mock TaskBundle and its methods
    bundle = MockTaskBundle(num_tasks=5)
    bundle.to_mining_tasks = MagicMock(
        return_value=[MagicMock(bundle_guid=task_bundle_guid, guid="task_guid", input=MagicMock(data=MagicMock(window_idx=0)), type="type") for _ in range(10)]
    )
    bundle.input.metadata.model_dump = MagicMock(return_value={})
    bundle.format_results = AsyncMock(side_effect=lambda x: x)
    bundle.generate_result_logs = MagicMock(return_value="result_logs")
    bundle.evaluate = AsyncMock(return_value=([{"hotkey": "hk", "adjustedScore": 1.0, "final_miner_score": 1.0}], [1.0]))

    fake_libs["vl"].reserve_task_bundle = AsyncMock(return_value=bundle)
    fake_libs["vl"].put_task = AsyncMock()

    class DummyResponse:
        def __init__(self, hotkey):
            self.dendrite = MagicMock()
            self.dendrite.status_code = 200
            self.axon = MagicMock()
            self.axon.hotkey = hotkey
            self.cgp_output = [
                {
                    "result": "ok",
                    "hotkey": hotkey,
                    "adjustedScore": 1.0,
                    "final_miner_score": 1.0,
                    "tags": ["tag1", "tag2"],
                }
            ]

    validator.dendrite.forward = AsyncMock(side_effect=lambda axons, *_, **__: [DummyResponse(axon.hotkey) for axon in axons])
    validator.metagraph.hotkeys = ["hk"]
    validator.update_scores = MagicMock()

    result = await validator.forward(test_mode=True)
    assert result is True


@pytest.mark.asyncio
async def test_forward_handles_no_miners(bare_validator, fake_libs, monkeypatch):
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3

    task_bundle_guid = "guid"

    bundle = MockTaskBundle(guid=task_bundle_guid, num_tasks=5)
    bundle.to_mining_tasks = MagicMock(
        return_value=[MagicMock(bundle_guid=task_bundle_guid, guid="task_guid", input=MagicMock(data=MagicMock(window_idx=0)), type="type") for _ in range(10)]
    )
    bundle.input.metadata.model_dump = MagicMock(return_value={})
    bundle.format_results = AsyncMock(side_effect=lambda x: x)
    bundle.generate_result_logs = MagicMock(return_value="result_logs")
    bundle.evaluate = AsyncMock(return_value=([{"hotkey": "hk", "adjustedScore": 1.0, "final_miner_score": 1.0}], [1.0]))

    fake_libs["vl"].reserve_task_bundle = AsyncMock(return_value=bundle)
    fake_libs["vl"].put_task = AsyncMock()

    # Patch get_random_uids to return empty list
    monkeypatch.setattr("conversationgenome.utils.uids.get_random_uids", lambda *args, **kwargs: [])

    validator.dendrite.forward = AsyncMock()
    validator.metagraph.hotkeys = ["hk"]
    validator.update_scores = MagicMock()

    result = await validator.forward(test_mode=True)
    assert result is None


@pytest.mark.asyncio
async def test_forward_handles_exception(bare_validator, fake_libs, monkeypatch):
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3
    fake_libs["vl"].reserve_task_bundle = AsyncMock(side_effect=Exception("fail"))
    result = await validator.forward()
    assert result is False


@pytest.mark.asyncio
async def test_forward_retries_on_status_code(bare_validator, fake_libs, monkeypatch):
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3

    bundle = MockTaskBundle(num_tasks=5)
    bundle.to_mining_tasks = MagicMock(
        return_value=[MagicMock(bundle_guid="guid", guid="task_guid", input=MagicMock(data=MagicMock(window_idx=0)), type="type") for _ in range(10)]
    )
    bundle.input.metadata.model_dump = MagicMock(return_value={})
    bundle.format_results = AsyncMock(side_effect=lambda x: x)
    bundle.generate_result_logs = MagicMock(return_value="result_logs")
    bundle.evaluate = AsyncMock(return_value=([{"hotkey": "hk", "adjustedScore": 1.0, "final_miner_score": 1.0}], [1.0]))

    fake_libs["vl"].reserve_task_bundle = AsyncMock(return_value=bundle)
    fake_libs["vl"].put_task = AsyncMock()

    class DummyResponse:
        def __init__(self, hotkey, status_code):
            self.dendrite = MagicMock()
            self.dendrite.status_code = status_code
            self.axon = MagicMock()
            self.axon.hotkey = hotkey
            self.cgp_output = [
                {
                    "result": "ok",
                    "hotkey": hotkey,
                    "adjustedScore": 1.0,
                    "final_miner_score": 1.0,
                    "tags": ["tag1", "tag2"],
                }
            ]

    # First call returns status_code 408 (should trigger retry), second call returns 200
    responses = [DummyResponse("hk", 408), DummyResponse("hk", 200), DummyResponse("hk", 200)]
    retry_responses = [DummyResponse("hk", 200)]

    validator.dendrite.forward = AsyncMock(side_effect=[responses, retry_responses])
    validator.metagraph.hotkeys = ["hk"]
    validator.update_scores = MagicMock()

    monkeypatch.setattr("conversationgenome.utils.uids.get_random_uids", lambda self, k: [0, 1, 2])
    validator.metagraph.axons = [MagicMock(hotkey="hk") for _ in range(3)]

    result = await validator.forward(test_mode=True)
    assert result is True
