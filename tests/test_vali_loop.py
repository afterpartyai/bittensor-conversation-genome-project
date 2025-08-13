import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from conversationgenome.base.validator import BaseValidatorNeuron
from conversationgenome.utils import uids
from tests.mocks.DummyAxon import DummyAxon
from tests.mocks.DummyResponse import DummyResponse
from tests.mocks.TestValidator import TestValidator
from itertools import cycle



@pytest.fixture
def validator_with_mock_metagraph():
    with patch("conversationgenome.base.neuron.MockMetagraph") as mock_metagraph_class, patch("bittensor.subtensor") as mock_subtensor_class, patch(
        "bittensor.wallet"
    ) as mock_wallet_class:

        # ---- Mock instances
        mock_wallet_instance = MagicMock()
        mock_wallet_instance.hotkey.ss58_address = "mock_hotkey"
        mock_wallet_class.return_value = mock_wallet_instance

        mock_subtensor_instance = MagicMock()
        mock_subtensor_instance.is_hotkey_registered.return_value = True
        mock_subtensor_class.return_value = mock_subtensor_instance

        mock_metagraph_instance = MagicMock()
        mock_metagraph_instance.hotkeys = ["miner1", "miner2", "miner3"]
        mock_metagraph_instance.axons = [DummyAxon("miner1", "miner1_id"), DummyAxon("miner2", "miner2_id"), DummyAxon("miner3", "miner3_id")]
        mock_metagraph_instance.n = np.array(3)
        mock_metagraph_instance.uids = np.array([0, 1, 2])
        mock_metagraph_instance.last_update = [50, 50, 50]
        mock_metagraph_class.return_value = mock_metagraph_instance

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
            num_concurrent_forwards=1,
        )

        temp_log_dir = tempfile.mkdtemp()
        config.logging = SimpleNamespace(logging_dir=temp_log_dir, logging_file="bittensor.log", debug=True, trace=False, logging_level="info", record_log=False)

        validator = TestValidator(config, block_override=100)
        validator.verbose = False
        validator.uid = 1
        validator.metagraph = mock_metagraph_instance
        validator.subtensor = mock_subtensor_instance
        validator.wallet = mock_wallet_instance

        yield validator
        shutil.rmtree(temp_log_dir)


@pytest.mark.asyncio
async def test_forward_with_successful_response(validator_with_mock_metagraph):
    validator = validator_with_mock_metagraph

    validator.scores = np.zeros(validator.metagraph.n, dtype=np.float32)
    validator.ema_scores = np.zeros(validator.metagraph.n, dtype=np.float32)

    tags = [
        "innovation",
        "resilience",
        "creativity",
        "strategy",
        "collaboration",
        "leadership",
        "efficiency",
        "growth",
        "optimization",
        "vision",
        "focus",
        "communication",
        "analytics",
        "productivity",
        "design",
        "scalability",
    ]

    DIM = 1536

    vectors = {tag: {"vectors": np.random.rand(DIM).tolist()} for tag in tags}

    miners = [{"hotkey": "miner1", "uuid": "miner1_id", "uid": 0}, {"hotkey": "miner2", "uuid": "miner2_id", "uid": 1}, {"hotkey": "miner3", "uuid": "miner3_id", "uid": 2}]

    responses = []
    uids_to_return = []

    for miner in miners:
        responses.append([DummyResponse(
            miner["hotkey"],
            miner["uuid"],
            200,
            [{
                "uid": miner["uid"],
                "tags": list(vectors.keys()),
                "vectors": vectors
            }]
        )])
        uids_to_return.append(np.array([miner["uid"]]))

    response_cycle = cycle(responses)
    uids_cycle = cycle(uids_to_return)

    # Patch them with infinite side_effects
    forward_mock = AsyncMock(side_effect=lambda *args, **kwargs: next(response_cycle))
    validator.dendrite.forward = forward_mock 

    uids.get_random_uids = lambda self, k: next(uids_cycle)

    result = await validator.forward(test_mode=True)

    for _, call in enumerate(forward_mock.await_args_list):
        cgp_inputs = call.kwargs["synapse"].cgp_input

        for cgp_input in cgp_inputs:
            assert "task_prompt" in cgp_input
            assert isinstance(cgp_input["task_prompt"], str)