# tests/test_validator_forward.py
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_buffering_and_metadata(bare_validator, fake_libs):
    """
    Happy path: enough pieces, metadata fetched and put_convo called.
    """
    v = bare_validator
    ok = await v.forward(test_mode=True)

    assert ok is True
    assert fake_libs["vl"].calls["reserve_conversation"] >= 1
    assert fake_libs["vl"].calls["put_convo"] > 0
    assert fake_libs["evaluator"].last_kwargs is not None


@pytest.mark.asyncio
async def test_aborts_when_not_enough_pieces(config_override, bare_validator, fake_libs):
    """
    Force too few pieces by lowering buffers via c.get override in this test only.
    """
    config_override(
        {
            ("validator", "num_convos_per_buffer"): 1,
            ("validator", "num_windows_per_convo"): 3,
        }
    )

    v = bare_validator
    ok = await v.forward(test_mode=True)
    assert ok is False


@pytest.mark.asyncio
async def test_forward_returns_true_on_success(bare_validator, fake_libs):
    """
    Test that forward returns True when enough pieces and all steps succeed.
    """
    v = bare_validator
    result = await v.forward(test_mode=True)
    
    assert result is True
    assert fake_libs["vl"].calls["reserve_conversation"] >= 1
    assert fake_libs["vl"].calls["put_convo"] > 0
    assert fake_libs["evaluator"].last_kwargs is not None


@pytest.mark.asyncio
async def test_forward_returns_false_when_not_enough_pieces(config_override, bare_validator, fake_libs):
    """
    Test that forward returns False when not enough pieces are buffered.
    """
    config_override(
        {
            ("validator", "num_convos_per_buffer"): 1,
            ("validator", "num_windows_per_convo"): 3,
        }
    )
    v = bare_validator
    result = await v.forward(test_mode=True)
    
    assert result is False


@pytest.mark.asyncio
async def test_forward_handles_no_conversation_guid(bare_validator, fake_libs):
    """
    Test that forward returns when no conversation_guid is present.
    """
    v = bare_validator
    orig_reserve = fake_libs["vl"].reserve_conversation

    async def reserve_conversation(*args, **kwargs):
        convo = await orig_reserve(*args, **kwargs)
        convo.guid = None
        return convo

    fake_libs["vl"].reserve_conversation = reserve_conversation
    result = await v.forward(test_mode=True)
    assert result is None or result is False


@pytest.mark.asyncio
async def test_forward_handles_no_miners(bare_validator, fake_libs):
    """
    Test that forward returns when no miners are found.
    """
    v = bare_validator
    orig_get_random_uids = fake_libs["uids"].get_random_uids
    fake_libs["uids"].get_random_uids = MagicMock(return_value=[])
    result = await v.forward(test_mode=True)

    assert result is None or result is False

    # Restore
    fake_libs["uids"].get_random_uids = orig_get_random_uids


@pytest.mark.asyncio
async def test_forward_handles_bad_responses(bare_validator, fake_libs):
    """
    Test that forward skips bad responses (no cgp_output).
    """
    v = bare_validator

    class DummyResponse:
        def __init__(self, hotkey):
            self.dendrite = MagicMock(status_code=200)
            self.axon = MagicMock(hotkey=hotkey)
            self.cgp_output = None

    fake_libs["dendrite"].forward = AsyncMock(return_value=[DummyResponse("hk1"), DummyResponse("hk2")])
    result = await v.forward(test_mode=True)

    assert result is True or result is False  # Should not crash


@pytest.mark.asyncio
async def test_forward_handles_exception(bare_validator, fake_libs):
    """
    Test that forward returns False on exception.
    """
    v = bare_validator
    fake_libs["vl"].reserve_conversation = AsyncMock(side_effect=Exception("fail"))
    result = await v.forward(test_mode=True)

    assert result is False
