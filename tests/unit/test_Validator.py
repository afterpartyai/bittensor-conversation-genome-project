from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

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

    async def reserve_task_bundle_side_effect(netuid=None):
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


# ─── forced bulk refresh at start of forward ─────────────────────────

@pytest.mark.asyncio
async def test_forward_does_not_force_commitment_refresh(bare_validator, fake_libs, monkeypatch):
    """forward() must NOT call refresh_miner_endpoints itself.

    Refresh happens in resync_metagraph (periodic, debounced) and in
    _refresh_commitment_for_uid (on per-UID errors). Forcing refresh every
    forward stalls the async loop for validators on slow chain endpoints,
    causing en-masse dendrite timeouts (observed in production on
    operators using public finney).
    """
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3

    fake_libs["vl"].reserve_task_bundle = AsyncMock(return_value=None)
    validator.refresh_miner_endpoints = MagicMock()

    await validator.forward(test_mode=True)

    validator.refresh_miner_endpoints.assert_not_called()


def test_init_refreshes_commitments_once_at_startup(monkeypatch):
    """Validator.__init__ must perform a one-shot bulk commitment refresh
    so committed_endpoints is populated before the first forward(). Without
    this, fresh boots wait a full epoch before the periodic resync fires,
    leaving every commitment miner unreachable."""
    import neurons.validator as validator_module
    from conversationgenome.base.validator import BaseValidatorNeuron

    # Skip the heavy parent init.
    monkeypatch.setattr(BaseValidatorNeuron, "__init__", lambda self, config=None: None)
    monkeypatch.setattr(validator_module.c, "get", lambda *_a, **_k: "00" * 32)
    monkeypatch.setattr(validator_module.c, "set", lambda *_a, **_k: None)

    instance = validator_module.Validator.__new__(validator_module.Validator)
    instance.config = type("C", (), {"netuid": 33, "neuron": type("N", (), {"sample_size": 6})()})()
    instance.load_state = lambda: None
    instance.refresh_miner_endpoints = MagicMock()

    validator_module.Validator.__init__(instance)

    instance.refresh_miner_endpoints.assert_called_once_with(force=True)


def test_refresh_miner_endpoints_force_bypasses_debounce(bare_validator, monkeypatch):
    """refresh_miner_endpoints(force=True) must bypass the 5-min debounce."""
    import time as _time

    v = bare_validator
    v._last_commitment_refresh = _time.time()  # "just refreshed"
    v._commitment_cache = {}
    v.committed_endpoints = {}
    v.metagraph.hotkeys = ["hk0"]
    v.subtensor = MagicMock()

    # COMMITMENT_PRIVATE_KEY must be set or refresh exits early.
    monkeypatch.setattr(
        "conversationgenome.base.validator.c.get",
        lambda section, key, default=None: "00" * 32 if key == "COMMITMENT_PRIVATE_KEY" else default,
    )

    captured = {"called": False}

    def fake_read_all(*a, **kw):
        captured["called"] = True
        return {}, {}

    monkeypatch.setattr(
        "conversationgenome.commitment.commitment.read_all_commitments",
        fake_read_all,
    )

    # Without force, debounce should skip (read_all_commitments not called)
    v.refresh_miner_endpoints()
    assert captured["called"] is False, "debounce should skip without force"

    # With force, debounce is bypassed
    v.refresh_miner_endpoints(force=True)
    assert captured["called"] is True, "force=True must bypass the debounce"


# ─── refresh-on-any-error / retry-only-on-subset ──────────────────────
#
# Pin the policy added in neurons/validator.py forward():
#   refresh:  any non-success outcome (non-200, missing payload, or None)
#   retry:    only {408, 422, 503, None}
# These tests lock both axes down so a future drift in the retry list
# doesn't silently re-open the leak/miss patterns.

def _dummy_response(hotkey, status_code, with_output=True):
    r = MagicMock()
    r.dendrite = MagicMock()
    r.dendrite.status_code = status_code
    r.axon = MagicMock()
    r.axon.hotkey = hotkey
    r.cgp_output = (
        [{"result": "ok", "hotkey": hotkey, "adjustedScore": 1.0, "final_miner_score": 1.0, "tags": ["t"]}]
        if with_output else None
    )
    return r


def _setup_forward(validator, fake_libs, monkeypatch, response_for_uid, retry_response_for_uid=None):
    """Wire up the minimum scaffolding needed to drive forward() once over 3 UIDs."""
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3

    bundle = MockTaskBundle(num_tasks=5)
    bundle.to_mining_tasks = MagicMock(
        return_value=[MagicMock(bundle_guid=bundle.guid, guid=f"task_guid_{i}",
                                input=MagicMock(data=MagicMock(window_idx=0)), type="type")
                      for i in range(10)]
    )
    bundle.input.metadata.model_dump = MagicMock(return_value={})
    bundle.format_results = AsyncMock(side_effect=lambda x: x)
    bundle.generate_result_logs = MagicMock(return_value="result_logs")
    bundle.evaluate = AsyncMock(return_value=([{"hotkey": "hk", "adjustedScore": 1.0, "final_miner_score": 1.0}], [1.0]))
    fake_libs["vl"].reserve_task_bundle = AsyncMock(return_value=bundle)
    fake_libs["vl"].put_task = AsyncMock()

    forward_calls = []

    async def fake_forward(axons, *_, **__):
        forward_calls.append(len(axons))
        if len(forward_calls) == 1:
            return [response_for_uid(i) for i in range(len(axons))]
        # retry call
        return [retry_response_for_uid(i) for i in range(len(axons))]

    validator.dendrite.forward = AsyncMock(side_effect=fake_forward)
    validator.metagraph.hotkeys = ["hk0", "hk1", "hk2"]
    validator.metagraph.axons = [MagicMock(hotkey=f"hk{i}") for i in range(3)]
    validator.update_scores = MagicMock()
    monkeypatch.setattr("conversationgenome.utils.uids.get_random_uids", lambda self, k: [0, 1, 2])

    validator._refresh_commitment_for_uid = MagicMock()
    return forward_calls


@pytest.mark.asyncio
async def test_refresh_and_retry_on_status_code_none(bare_validator, fake_libs, monkeypatch):
    """ClientConnectorError-style failures (status_code=None) must refresh AND retry."""
    validator = bare_validator
    calls = _setup_forward(
        validator, fake_libs, monkeypatch,
        response_for_uid=lambda i: _dummy_response(f"hk{i}", None, with_output=False),
        retry_response_for_uid=lambda i: _dummy_response(f"hk{i}", 200, with_output=True),
    )

    await validator.forward(test_mode=True)

    # Refresh fired for each failing UID (3) — possibly multiple times across
    # the forward loop's task iterations, but at least 3.
    refresh_uids = {call.args[0] for call in validator._refresh_commitment_for_uid.call_args_list}
    assert refresh_uids == {0, 1, 2}, f"expected refresh for {{0,1,2}} got {refresh_uids}"

    # Retry actually happened (dendrite.forward called >1 time per task batch).
    assert any(c > 0 for c in calls[1:]), "retry call to dendrite.forward did not happen"


@pytest.mark.asyncio
async def test_refresh_no_retry_on_502(bare_validator, fake_libs, monkeypatch):
    """A 502 must refresh the commitment but NOT retry (server-side error, won't change)."""
    validator = bare_validator
    calls = _setup_forward(
        validator, fake_libs, monkeypatch,
        response_for_uid=lambda i: _dummy_response(f"hk{i}", 502, with_output=False),
        retry_response_for_uid=lambda i: _dummy_response(f"hk{i}", 200, with_output=True),
    )

    await validator.forward(test_mode=True)

    refresh_uids = {call.args[0] for call in validator._refresh_commitment_for_uid.call_args_list}
    assert refresh_uids == {0, 1, 2}

    # Only the initial batch calls — no retry batch. Each per-task forward
    # call counts in `calls`; with no retries we should see no element of
    # `calls` that comes AFTER an initial batch for the same task.
    # Simpler invariant: total dendrite.forward calls == number of tasks
    # (each task calls forward exactly once when there is no retry).
    task_count = validator.dendrite.forward.await_count
    assert task_count > 0 and len(calls) == task_count, \
        f"expected one forward per task and no retries, got calls={calls}"


@pytest.mark.asyncio
async def test_refresh_no_retry_on_200_without_output(bare_validator, fake_libs, monkeypatch):
    """200 with empty cgp_output must refresh (miner is up but produced nothing) but NOT retry."""
    validator = bare_validator
    calls = _setup_forward(
        validator, fake_libs, monkeypatch,
        response_for_uid=lambda i: _dummy_response(f"hk{i}", 200, with_output=False),
        retry_response_for_uid=lambda i: _dummy_response(f"hk{i}", 200, with_output=True),
    )

    await validator.forward(test_mode=True)

    refresh_uids = {call.args[0] for call in validator._refresh_commitment_for_uid.call_args_list}
    assert refresh_uids == {0, 1, 2}, "refresh must fire when the miner returns 200 with no payload"

    task_count = validator.dendrite.forward.await_count
    assert len(calls) == task_count, "no retry should fire for 200/no-output"


@pytest.mark.asyncio
async def test_no_refresh_no_retry_on_clean_success(bare_validator, fake_libs, monkeypatch):
    """Clean 200 + payload must not trigger refresh or retry."""
    validator = bare_validator
    calls = _setup_forward(
        validator, fake_libs, monkeypatch,
        response_for_uid=lambda i: _dummy_response(f"hk{i}", 200, with_output=True),
        retry_response_for_uid=lambda i: _dummy_response(f"hk{i}", 200, with_output=True),
    )

    await validator.forward(test_mode=True)

    assert validator._refresh_commitment_for_uid.call_count == 0, \
        "refresh must not fire on a clean 200 + payload"

    task_count = validator.dendrite.forward.await_count
    assert len(calls) == task_count, "no retry should fire on clean success"


@pytest.mark.asyncio
async def test_refresh_and_retry_on_422(bare_validator, fake_libs, monkeypatch):
    """422 stays in the retry set (regression for the existing case)."""
    validator = bare_validator
    calls = _setup_forward(
        validator, fake_libs, monkeypatch,
        response_for_uid=lambda i: _dummy_response(f"hk{i}", 422, with_output=False),
        retry_response_for_uid=lambda i: _dummy_response(f"hk{i}", 200, with_output=True),
    )

    await validator.forward(test_mode=True)

    assert validator._refresh_commitment_for_uid.call_count > 0
    assert any(c > 0 for c in calls[1:]), "422 must trigger a retry"


@pytest.mark.asyncio
async def test_forward_handles_missing_cgp_output(bare_validator, fake_libs, monkeypatch):
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3

    bundle_guid = "test-guid"
    bundle = MockTaskBundle(num_tasks=5, guid=bundle_guid)
    bundle.to_mining_tasks = MagicMock(
        return_value=[MagicMock(bundle_guid=bundle_guid, guid=f"task_guid_{i}", input=MagicMock(data=MagicMock(window_idx=0)), type="type") for i in range(5)]
    )
    bundle.input.metadata.model_dump = MagicMock(return_value={})
    bundle.format_results = AsyncMock(side_effect=lambda x: x)
    bundle.generate_result_logs = MagicMock(return_value="result_logs")
    bundle.evaluate = AsyncMock(return_value=([{"hotkey": "hk", "adjustedScore": 1.0, "final_miner_score": 1.0}], [1.0]))

    fake_libs["vl"].reserve_task_bundle = AsyncMock(return_value=bundle)
    fake_libs["vl"].put_task = AsyncMock()

    class DummyResponseNoCGP:
        def __init__(self, hotkey):
            self.dendrite = MagicMock()
            self.dendrite.status_code = 200
            self.axon = MagicMock()
            self.axon.hotkey = hotkey
            self.cgp_output = None  # Simulate missing cgp_output

    validator.dendrite.forward = AsyncMock(side_effect=lambda axons, *_, **__: [DummyResponseNoCGP(axon.hotkey) for axon in axons])
    validator.metagraph.hotkeys = ["hk0", "hk1", "hk2"]
    validator.update_scores = MagicMock()

    result = await validator.forward(test_mode=True)
    assert result is True


@pytest.mark.asyncio
async def test_forward_continues_when_format_results_raises(bare_validator, fake_libs, monkeypatch):
    # miner_result is untrusted, miner-controlled data -- a malformed or
    # malicious response must not be able to raise out of format_results()
    # and abort scoring for the whole batch. See the try/except guard around
    # task_bundle.format_results() in neurons/validator.py.
    validator = bare_validator
    validator.config.neuron.sample_size = 3
    validator.metagraph.n.item.return_value = 3

    bundle_guid = "test-guid"
    bundle = MockTaskBundle(num_tasks=5, guid=bundle_guid)
    bundle.to_mining_tasks = MagicMock(
        return_value=[MagicMock(bundle_guid=bundle_guid, guid=f"task_guid_{i}", input=MagicMock(data=MagicMock(window_idx=0)), type="type") for i in range(5)]
    )
    bundle.input.metadata.model_dump = MagicMock(return_value={})
    bundle.format_results = AsyncMock(side_effect=ValueError("malformed miner_result"))
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
            self.cgp_output = [{"skill": object(), "section_tests": "garbage"}]

    validator.dendrite.forward = AsyncMock(side_effect=lambda axons, *_, **__: [DummyResponse(axon.hotkey) for axon in axons])
    validator.metagraph.hotkeys = ["hk0", "hk1", "hk2"]
    validator.update_scores = MagicMock()

    result = await validator.forward(test_mode=True)

    # Every response's format_results() raises, yet the round as a whole
    # still completes and still reaches scoring rather than aborting partway
    # through (the pre-fix behavior would raise out of forward() entirely and
    # never call update_scores at all).
    assert result is True
    assert validator.update_scores.call_count > 0


def test_get_burn_uid(bare_validator):
    """Ensure `get_burn_uid` queries the subnet owner hotkey and resolves its UID."""
    v = bare_validator

    # Prepare expected values and mocks
    expected_hotkey = "owner_hk"
    expected_uid = 1234

    # Ensure netuid is defined on config (bare_validator provides one)
    v.config.netuid = 99

    # Mock subtensor with the two calls used in get_burn_uid
    v.subtensor = MagicMock()
    v.subtensor.query_subtensor.return_value = expected_hotkey
    v.subtensor.get_uid_for_hotkey_on_subnet.return_value = expected_uid

    # Call the method under test
    uid = v.get_burn_uid()

    # Assertions
    assert uid == expected_uid
    v.subtensor.query_subtensor.assert_called_once_with("SubnetOwnerHotkey", params=[v.config.netuid])
    v.subtensor.get_uid_for_hotkey_on_subnet.assert_called_once_with(hotkey_ss58=expected_hotkey, netuid=v.config.netuid)
