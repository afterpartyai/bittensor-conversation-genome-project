# tests/conftest.py
import os
from unittest.mock import AsyncMock

import pytest
from dotenv import find_dotenv, load_dotenv

import neurons.validator as validator_module
from tests.mocks.DummyData import DummyData

load_dotenv(find_dotenv(usecwd=True), override=False)


@pytest.fixture(autouse=True)
def patch_random_and_config(monkeypatch):
    """Global defaults: deterministic random + sensible c.get map."""
    monkeypatch.setattr(validator_module.random, "sample", lambda seq, n: seq[:n])
    monkeypatch.setattr(validator_module.random, "shuffle", lambda seq: None)

    defaults = {
        ("validator", "miners_per_window"): 3,
        ("validator", "num_convos_per_buffer"): 10,
        ("validator", "num_windows_per_convo"): 5,
        ("convo_window", "min_lines"): 5,
        ("convo_window", "max_lines"): 10,
        ("convo_window", "overlap_lines"): 2,
    }

    def get(section, key, default=None):
        if section == "env":
            return os.getenv(key, default)
        return defaults.get((section, key), default)

    monkeypatch.setattr(validator_module.c, "get", get)


@pytest.fixture(autouse=True)
def patch_uids(monkeypatch):
    """Make miner selection deterministic."""
    import conversationgenome.utils.uids as uids

    assert validator_module.conversationgenome.utils.uids is uids
    monkeypatch.setattr(uids, "get_random_uids", lambda self, k: [0, 1, 2][:k])


@pytest.fixture
def fake_libs(monkeypatch):
    """
    Patch ValidatorLib, Evaluator, WandbLib, Utils.append_log.
    Return the created fake instances so tests can tweak behaviors.
    """

    class _FakeVL:
        def __init__(self):
            self.calls = {"reserve_conversation": 0, "put_convo": 0}

        async def reserve_conversation(self, *, batch_num=None, return_indexed_windows=True):
            self.calls["reserve_conversation"] += 1
            return DummyData.conversation()

        async def get_convo_metadata(self, *a, **k):
            return DummyData.metadata()

        async def validate_tag_set(self, tags):
            return DummyData.tags()

        async def get_vector_embeddings_set(self, tags):
            return DummyData.vectors()

        async def put_convo(self, *a, **k):
            self.calls["put_convo"] += 1
            return True

    vl_instance = _FakeVL()
    monkeypatch.setattr(validator_module, "ValidatorLib", lambda: vl_instance)

    class _FakeEval:
        def __init__(self):
            self.last_kwargs = None

        async def evaluate(self, **kwargs):
            self.last_kwargs = kwargs
            return ([], [])  # (final_scores, rank_scores)

    eval_instance = _FakeEval()
    monkeypatch.setattr(validator_module, "Evaluator", lambda: eval_instance)

    class _FakeWB:
        def __init__(self):
            self.logs = []

        def log(self, *a, **k):
            self.logs.append((a, k))

        def init_wandb(self, *_a, **_k): ...
        def end_log_wandb(self, *_a, **_k): ...

    wb_instance = _FakeWB()
    monkeypatch.setattr(validator_module, "WandbLib", lambda: wb_instance)

    monkeypatch.setattr(validator_module.Utils, "append_log", lambda *a, **k: None)

    import conversationgenome.utils.uids as uids

    class _FakeDendrite:
        forward = AsyncMock(return_value=[])

    return {
        "vl": vl_instance,
        "evaluator": eval_instance,
        "wandb": wb_instance,
        "uids": uids,
        "dendrite": _FakeDendrite(),
    }


@pytest.fixture
def bare_validator(monkeypatch):
    """
    Create a Validator without running BaseValidatorNeuron.__init__.
    Everything heavy is mocked. You can still override pieces per test.
    """
    monkeypatch.setattr(validator_module.BaseValidatorNeuron, "__init__", lambda self, config=None: None)

    v = validator_module.Validator.__new__(validator_module.Validator)
    v.config = type("C", (), {"netuid": 33, "neuron": type("N", (), {"sample_size": 3})()})()
    v.responses = []
    v.initial_status_codes = {}
    v.final_status_codes = {}

    v.axon = type("Ax", (), {"wallet": type("W", (), {"hotkey": type("H", (), {"ss58_address": "HK"})()})()})()
    v.metagraph = type(
        "MG",
        (),
        {
            "n": type("N", (), {"item": staticmethod(lambda: 3)})(),
            "axons": [type("A", (), {"hotkey": "hk0"})(), type("A", (), {"hotkey": "hk1"})(), type("A", (), {"hotkey": "hk2"})()],
            "hotkeys": ["hk0", "hk1", "hk2"],
        },
    )()

    v.dendrite = type("D", (), {"forward": AsyncMock(return_value=[])})()
    v.update_scores = lambda *a, **k: None
    v.load_state = lambda: None

    return v


@pytest.fixture
def config_override(monkeypatch):
    """
    Per-test override for c.get using a dict with tuple keys:
      {("section","key"): value, ...}
    """
    orig_get = validator_module.c.get

    def apply(pairs: dict):
        def wrapped(section, key, default=None, _orig=orig_get, _pairs=pairs):
            return _pairs.get((section, key), _orig(section, key, default))

        monkeypatch.setattr(validator_module.c, "get", wrapped)

    return apply
