from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from conversationgenome.base.validator import BaseValidatorNeuron
from conversationgenome.utils import uids
from neurons.validator import Validator


# --------------------------
# Dummy Test Classes
# --------------------------

class DummyAxon:
    def __init__(self, hotkey):
        self.hotkey = hotkey


class DummyResponse:
    def __init__(self, hotkey, status_code, output=None):
        self.axon = DummyAxon(hotkey)
        self.dendrite = type("Dendrite", (), {"status_code": status_code})()
        self.cgp_output = output


class TestValidator(Validator):
    def __init__(self, config, *, block_override=None, skip_sync=True):
        self._skip_sync_flag = skip_sync
        self._block_override = block_override

        # Temporarily disable sync during init
        original_sync = self.sync
        if self._skip_sync_flag:
            self.sync = lambda: None

        super().__init__(config)

        if self._skip_sync_flag:
            self.sync = original_sync

    @property
    def block(self):
        if hasattr(self, "_block_override") and self._block_override is not None:
            return self._block_override
        return super().block


def setup():
    # --------------------------
    # Mocks: ValidatorLib
    # --------------------------
    vl_mock = MagicMock()
    vl_mock.reserve_conversation = AsyncMock(
        return_value={
            "guid": "test-guid",
            "lines": ["Hello", "Hi", "How are you?"],
            "participants": ["A", "B"],
            "indexed_windows": [(0, ["Hello", "Hi", "How are you?"])],
        }
    )
    vl_mock.get_convo_metadata = AsyncMock(
        return_value={"tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1], "tag2": [0.2]}}
    )
    vl_mock.put_convo = AsyncMock()
    vl_mock.validate_tag_set = AsyncMock(return_value=["tag1", "tag2"])
    vl_mock.get_vector_embeddings_set = AsyncMock(
        return_value={"tag1": [0.1], "tag2": [0.2]}
    )
    vl_mock.update_scores.return_value = (
        np.array([0.5, 0.5]),
        np.array([0.5, 0.5]),
    )

    # mock_validator_lib.return_value = vl_mock
    # mock_validator_lib2.return_value = vl_mock

    # --------------------------
    # Mocks: Evaluator
    # --------------------------
    el_mock = MagicMock()
    el_mock.evaluate = AsyncMock(
        return_value=(
            [
                {"uid": 0, "uuid": "uuid-0", "hotkey": "miner1", "adjustedScore": 1.0, "final_miner_score": 1.0},
                {"uid": 1, "uuid": "uuid-1", "hotkey": "miner2", "adjustedScore": 1.0, "final_miner_score": 1.0},
                {"uid": 2, "uuid": "uuid-1", "hotkey": "miner3", "adjustedScore": 1.0, "final_miner_score": 1.0},
            ],
            np.array([1.0, 1.0, 1.0], dtype=np.float32),
        )
    )
    # mock_evaluator.return_value = el_mock

    # --------------------------
    # Mocks: Wallet, Subtensor, Metagraph
    # --------------------------
    mock_wallet_instance = MagicMock()
    mock_wallet_instance.hotkey.ss58_address = "mock_hotkey"
    # mock_wallet.return_value = mock_wallet_instance

    mock_subtensor_instance = MagicMock()
    mock_subtensor_instance.is_hotkey_registered.return_value = True
    # mock_subtensor.return_value = mock_subtensor_instance

    mock_metagraph_instance = MagicMock()
    mock_metagraph_instance.hotkeys = ["miner1", "miner2", "miner3"]
    mock_metagraph_instance.axons = [DummyAxon("miner1"), DummyAxon("miner2"), DummyAxon("miner3")]
    mock_metagraph_instance.n.item.return_value = 2
    mock_metagraph_instance.last_update = [50, 50, 50]
    # mock_metagraph.return_value = mock_metagraph_instance

    # --------------------------
    # Config
    # --------------------------
    config = BaseValidatorNeuron.config()
    config.wallet = SimpleNamespace(name="mock_wallet", hotkey="mock_hotkey")
    config.netuid = 33
    config.neuron = SimpleNamespace(
        name="test-validator",
        epoch_length=10,
        disable_set_weights=True,
        dont_save_events=True,
        full_path="/tmp/validator_test",
        device="cpu",
        axon_off=True,
        sample_size=2,
        moving_average_alpha=0.1,
    )

    validator = TestValidator(config, block_override=100)
    validator.verbose = False
    validator.uid = 10
    validator.metagraph = mock_metagraph_instance
    validator.subtensor = mock_subtensor_instance
    validator.wallet = mock_wallet_instance
    validator.scores = np.zeros(len(validator.metagraph.hotkeys), dtype=np.float32)

    # Patch get_random_uids
    uids.get_random_uids = lambda self, k: np.array([0, 1, 2])

    return vl_mock, el_mock, mock_wallet_instance, mock_subtensor_instance, mock_metagraph_instance, validator

# --------------------------
# Main Test
# --------------------------

@pytest.mark.asyncio
@patch("neurons.validator.ValidatorLib", autospec=True)
@patch("conversationgenome.base.validator.ValidatorLib", autospec=True)
@patch("neurons.validator.Evaluator", autospec=True)
@patch("bittensor.wallet")
@patch("bittensor.subtensor")
@patch("bittensor.metagraph")
async def test_when_receiving_408_responses_then_retry_only_those_requests(
    mock_metagraph,
    mock_subtensor,
    mock_wallet,
    mock_evaluator,
    mock_validator_lib2,
    mock_validator_lib,
):
    vl_mock, el_mock, mock_wallet_instance, mock_subtensor_instance, mock_metagraph_instance, validator = setup()
    mock_metagraph.return_value = mock_metagraph_instance
    mock_subtensor.return_value = mock_subtensor_instance
    mock_wallet.return_value = mock_wallet_instance
    mock_evaluator.return_value = el_mock
    mock_validator_lib2.return_value = vl_mock
    mock_validator_lib.return_value = vl_mock

    # --------------------------
    # Responses & Side Effect
    # --------------------------
    miner1_408_response = DummyResponse("miner1", 408)
    miner1_200_response = DummyResponse("miner1", 200, [{"uid": 0, "tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1], "tag2": [0.2]}}])
    miner2_200_response = DummyResponse("miner2", 200, [{"uid": 1, "tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1], "tag2": [0.2]}}])
    miner3_200_response = DummyResponse("miner3", 200, [{"uid": 2, "tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1], "tag2": [0.2]}}])

    def forward_side_effect(*args, **kwargs):
        calls = getattr(forward_side_effect, "calls", 0)

        if calls == 0:
            result = [miner1_408_response, miner2_200_response, miner3_200_response]
        elif calls == 1:
            result = [miner1_200_response]
        else:
            result = [miner1_200_response, miner2_200_response, miner3_200_response]

        forward_side_effect.calls = calls + 1
        return result

    forward_side_effect.calls = 0
    validator.dendrite.forward = AsyncMock(side_effect=forward_side_effect)

    # --------------------------
    # Execute
    # --------------------------
    result = await validator.forward(test_mode=True)

    # --------------------------
    # Validate Retry Behavior
    # --------------------------
    # The second call has 1 axon because it retries only the 408 response
    all_calls = validator.dendrite.forward.await_args_list
    for idx, call in enumerate(all_calls):
        _, kwargs = call
        forwarded_axons = kwargs.get("axons", None)

        if idx == 1:
            assert len(forwarded_axons) == 1
            assert forwarded_axons[0].hotkey == "miner1"
        else:
            assert len(forwarded_axons) == 3
            for axon in forwarded_axons:
                assert axon.hotkey in {"miner1", "miner2", "miner3"}

    # --------------------------
    # Final Assertions
    # --------------------------
    # Forward has been called 11 times (10 initial + 1 retry)
    # Evaluate has been called 10 times, once for 10 loops
    assert result is True
    assert validator.dendrite.forward.call_count == 11
    assert mock_evaluator.return_value.evaluate.await_count == 10

@pytest.mark.asyncio
@patch("neurons.validator.ValidatorLib", autospec=True)
@patch("conversationgenome.base.validator.ValidatorLib", autospec=True)
@patch("neurons.validator.Evaluator", autospec=True)
@patch("bittensor.wallet")
@patch("bittensor.subtensor")
@patch("bittensor.metagraph")
async def test_when_no_408_then_retry_nothing(
    mock_metagraph,
    mock_subtensor,
    mock_wallet,
    mock_evaluator,
    mock_validator_lib2,
    mock_validator_lib,
):
    vl_mock, el_mock, mock_wallet_instance, mock_subtensor_instance, mock_metagraph_instance, validator = setup()
    mock_metagraph.return_value = mock_metagraph_instance
    mock_subtensor.return_value = mock_subtensor_instance
    mock_wallet.return_value = mock_wallet_instance
    mock_evaluator.return_value = el_mock
    mock_validator_lib2.return_value = vl_mock
    mock_validator_lib.return_value = vl_mock

    # --------------------------
    # Responses & Side Effect
    # --------------------------
    miner1_200_response = DummyResponse("miner1", 200, [{"uid": 0, "tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1], "tag2": [0.2]}}])
    miner2_200_response = DummyResponse("miner2", 200, [{"uid": 1, "tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1], "tag2": [0.2]}}])
    miner3_200_response = DummyResponse("miner3", 200, [{"uid": 2, "tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1], "tag2": [0.2]}}])

    def forward_side_effect(*args, **kwargs):
        return [miner1_200_response, miner2_200_response, miner3_200_response]

    validator.dendrite.forward = AsyncMock(side_effect=forward_side_effect)

    # --------------------------
    # Execute
    # --------------------------
    result = await validator.forward(test_mode=True)

    # --------------------------
    # Validate Axons
    # --------------------------
    all_calls = validator.dendrite.forward.await_args_list
    for _, call in enumerate(all_calls):
        _, kwargs = call
        forwarded_axons = kwargs.get("axons", None)

        assert len(forwarded_axons) == 3
        for axon in forwarded_axons:
            assert axon.hotkey in {"miner1", "miner2", "miner3"}

    # --------------------------
    # Final Assertions
    # --------------------------
    # Forward has been called 10 times meaning no retries
    # Evaluate has been called 10 times, once for 10 loops
    assert result is True
    assert validator.dendrite.forward.call_count == 10
    assert mock_evaluator.return_value.evaluate.await_count == 10

@pytest.mark.asyncio
@patch("neurons.validator.ValidatorLib", autospec=True)
@patch("conversationgenome.base.validator.ValidatorLib", autospec=True)
@patch("neurons.validator.Evaluator", autospec=True)
@patch("bittensor.wallet")
@patch("bittensor.subtensor")
@patch("bittensor.metagraph")
async def test_when_other_errors_than_408_then_retry_nothing(
    mock_metagraph,
    mock_subtensor,
    mock_wallet,
    mock_evaluator,
    mock_validator_lib2,
    mock_validator_lib,
):
    vl_mock, el_mock, mock_wallet_instance, mock_subtensor_instance, mock_metagraph_instance, validator = setup()
    mock_metagraph.return_value = mock_metagraph_instance
    mock_subtensor.return_value = mock_subtensor_instance
    mock_wallet.return_value = mock_wallet_instance
    mock_evaluator.return_value = el_mock
    mock_validator_lib2.return_value = vl_mock
    mock_validator_lib.return_value = vl_mock

    # --------------------------
    # Responses & Side Effect
    # --------------------------
    miner1_500_response = DummyResponse("miner1", 500)
    miner2_404_response = DummyResponse("miner2", 404)
    miner3_303_response = DummyResponse("miner3", 303)

    def forward_side_effect(*args, **kwargs):
        return [miner1_500_response, miner2_404_response, miner3_303_response]

    validator.dendrite.forward = AsyncMock(side_effect=forward_side_effect)

    # --------------------------
    # Execute
    # --------------------------
    result = await validator.forward(test_mode=True)

    # --------------------------
    # Validate Axons
    # --------------------------
    all_calls = validator.dendrite.forward.await_args_list
    for _, call in enumerate(all_calls):
        _, kwargs = call
        forwarded_axons = kwargs.get("axons", None)

        assert len(forwarded_axons) == 3
        for axon in forwarded_axons:
            assert axon.hotkey in {"miner1", "miner2", "miner3"}

    # --------------------------
    # Final Assertions
    # --------------------------
    # Forward has been called 10 times meaning no retries
    # Evaluate has been called 10 times, once for 10 loops
    assert result is True
    assert validator.dendrite.forward.call_count == 10
    assert mock_evaluator.return_value.evaluate.await_count == 10