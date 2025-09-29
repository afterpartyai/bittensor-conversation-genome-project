import shutil
import tempfile
from itertools import cycle
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import numpy as np
import pytest

from conversationgenome.base.miner import BaseMinerNeuron
from conversationgenome.base.validator import BaseValidatorNeuron
from conversationgenome.task.Task import Task
from conversationgenome.utils import uids as uids_mod
from neurons.miner import Miner
from tests.mocks.DummyAxon import DummyAxon
from tests.mocks.DummyResponse import DummyResponse
from tests.mocks.TestValidator import TestValidator

default_prompt_value = "Analyze conversation in terms of topic interests of the participants. Analyze the conversation (provided in structured XML format) where <p0> has the questions and <p1> has the answers. Return comma-delimited tags. Only return the tags without any English commentary."


@pytest.fixture
def validator_with_mock_metagraph():
    with patch("conversationgenome.base.neuron.MockMetagraph") as mock_metagraph_class, patch("bittensor.subtensor") as mock_subtensor_class, patch(
        "bittensor.wallet"
    ) as mock_wallet_class:

        # Wallet
        mock_wallet_instance = MagicMock()
        mock_wallet_instance.hotkey.ss58_address = "mock_hotkey"
        mock_wallet_class.return_value = mock_wallet_instance

        # Subtensor
        mock_subtensor_instance = MagicMock()
        mock_subtensor_instance.is_hotkey_registered.return_value = True
        mock_subtensor_class.return_value = mock_subtensor_instance

        # Metagraph
        mock_metagraph_instance = MagicMock()
        mock_metagraph_instance.hotkeys = ["miner1", "miner2", "miner3"]
        mock_metagraph_instance.axons = [
            DummyAxon("miner1", "miner1_id"),
            DummyAxon("miner2", "miner2_id"),
            DummyAxon("miner3", "miner3_id"),
        ]
        mock_metagraph_instance.n = np.array(3)
        mock_metagraph_instance.uids = np.array([0, 1, 2])
        mock_metagraph_instance.last_update = [50, 50, 50]
        mock_metagraph_class.return_value = mock_metagraph_instance

        config_miner = BaseMinerNeuron.config()
        config_miner.wallet = SimpleNamespace(name="mock_wallet", hotkey="mock_hotkey")

        miner = Miner(config=config_miner)

        # Validator config
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
        config.logging = SimpleNamespace(
            logging_dir=temp_log_dir,
            logging_file="bittensor.log",
            debug=True,
            trace=False,
            logging_level="info",
            record_log=False,
        )

        validator = TestValidator(config, block_override=100)
        validator.verbose = True
        validator.uid = 1
        validator.metagraph = mock_metagraph_instance
        validator.subtensor = mock_subtensor_instance
        validator.wallet = mock_wallet_instance

        yield validator, miner
        shutil.rmtree(temp_log_dir)


@pytest.mark.asyncio
async def test_forward_roundtrip_with_real_miner_and_minerlib(monkeypatch, validator_with_mock_metagraph):
    validator, miner = validator_with_mock_metagraph

    validator.scores = np.zeros(validator.metagraph.n, dtype=np.float32)
    validator.ema_scores = np.zeros(validator.metagraph.n, dtype=np.float32)

    miners = [
        {"hotkey": "miner1", "uuid": "miner1_id", "uid": 0},
        {"hotkey": "miner2", "uuid": "miner2_id", "uid": 1},
        {"hotkey": "miner3", "uuid": "miner3_id", "uid": 2},
    ]
    uids_to_return = [np.array([m["uid"]]) for m in miners]
    uids_cycle = cycle(uids_to_return)
    uids_mod.get_random_uids = lambda self, k: next(uids_cycle)

    async def forward_side_effect(*, axons=None, synapse=None, **_):
        syn_after = await miner.forward(synapse)
        ax = axons[0]
        return [DummyResponse(ax.hotkey, ax.uuid, 200, syn_after.cgp_output)]

    validator.dendrite.forward = AsyncMock(side_effect=forward_side_effect)

    result = await validator.forward(test_mode=True)
    responses_array = validator.responses

    assert result is True

    # Check that tasks were correctly formed when passed to miners
    for _, call in enumerate(validator.dendrite.forward.await_args_list):
        synapse = call.kwargs["synapse"]
        cgp_inputs = synapse.cgp_input

        for window in cgp_inputs:
            task: Task = window.get("task")
            assert isinstance(task, Task)

    # Required response keys
    required_keys = {
        'tags',
        'vectors',
        'original_tags',
    }

    for response in responses_array:
        cgp = response[0].cgp_output
        for item in cgp:
            # Check required keys exist
            assert required_keys.issubset(item.keys())

            # Check tags is a list of strings
            tags = item["tags"]
            assert isinstance(tags, list)
            assert all(isinstance(tag, str) for tag in tags)

            # Check vectors structure
            vectors = item["vectors"]
            assert isinstance(vectors, dict)
            for tag in tags:
                assert tag in vectors
                tag_vectors = vectors[tag]
                assert isinstance(tag_vectors, dict)
                assert "vectors" in tag_vectors
                vec = tag_vectors["vectors"]
                assert isinstance(vec, list)
                assert all(isinstance(v, float) or isinstance(v, np.floating) for v in vec)


@pytest.mark.asyncio
async def test_old_forward_roundtrip_with_real_miner_and_minerlib(monkeypatch, validator_with_mock_metagraph):
    validator, miner = validator_with_mock_metagraph

    validator.scores = np.zeros(validator.metagraph.n, dtype=np.float32)
    validator.ema_scores = np.zeros(validator.metagraph.n, dtype=np.float32)

    miners = [
        {"hotkey": "miner1", "uuid": "miner1_id", "uid": 0},
        {"hotkey": "miner2", "uuid": "miner2_id", "uid": 1},
        {"hotkey": "miner3", "uuid": "miner3_id", "uid": 2},
    ]
    uids_to_return = [np.array([m["uid"]]) for m in miners]
    uids_cycle = cycle(uids_to_return)
    uids_mod.get_random_uids = lambda self, k: next(uids_cycle)

    async def forward_side_effect(*, axons=None, synapse=None, **_):
        syn_after = await miner.forward(synapse)
        ax = axons[0]
        return [DummyResponse(ax.hotkey, ax.uuid, 200, syn_after.cgp_output)]

    validator.dendrite.forward = AsyncMock(side_effect=forward_side_effect)

    result = await validator.old_forward(test_mode=True)
    responses_array = validator.responses

    assert result is True

    required_keys = {
        'uid',
        'tags',
        'profiles',
        'convoChecksum',
        'vectors',
        'original_tags',
    }

    for response in responses_array:
        cgp = response[0].cgp_output
        for item in cgp:
            # Check required keys exist
            assert required_keys.issubset(item.keys())

            # Check tags is a list of strings
            tags = item["tags"]
            assert isinstance(tags, list)
            assert all(isinstance(tag, str) for tag in tags)

            # Check vectors structure
            vectors = item["vectors"]
            assert isinstance(vectors, dict)
            for tag in tags:
                assert tag in vectors
                tag_vectors = vectors[tag]
                assert isinstance(tag_vectors, dict)
                assert "vectors" in tag_vectors
                vec = tag_vectors["vectors"]
                assert isinstance(vec, list)
                assert all(isinstance(v, float) or isinstance(v, np.floating) for v in vec)

