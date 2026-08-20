from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from conversationgenome.llm.llm_factory import _present_llm_override_vars
from conversationgenome.llm.llm_factory import configure_llm_override_lockdown
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.llm.llm_openai import LlmOpenAI


def _c_get(overrides):
    def get(section, key, default=None):
        return overrides.get((section, key), default)
    return get


@patch("conversationgenome.llm.llm_factory.c")
def test_present_llm_override_vars_none_set(mock_c):
    mock_c.get.side_effect = _c_get({})
    assert _present_llm_override_vars() == []


@patch("conversationgenome.llm.llm_factory.c")
def test_present_llm_override_vars_each_detected(mock_c):
    for var in ["LLM_TYPE_OVERRIDE", "OPENAI_MODEL", "OPENAI_EMBEDDINGS_MODEL_OVERRIDE"]:
        mock_c.get.side_effect = _c_get({("env", var): "some-value"})
        assert _present_llm_override_vars() == [var]


@patch("conversationgenome.llm.llm_factory.bt")
@patch("conversationgenome.llm.llm_factory.c")
def test_configure_lockdown_mainnet_no_override(mock_c, mock_bt):
    mock_c.get.side_effect = _c_get({("network", "mainnet"): 33})
    mock_c.set = MagicMock()

    result = configure_llm_override_lockdown(33)

    assert result is True
    mock_c.set.assert_called_once_with("system", "llm_overrides_locked", True)
    mock_bt.logging.warning.assert_not_called()


@patch("conversationgenome.llm.llm_factory.bt")
@patch("conversationgenome.llm.llm_factory.c")
def test_configure_lockdown_mainnet_with_override_warns_and_locks(mock_c, mock_bt):
    mock_c.get.side_effect = _c_get({
        ("network", "mainnet"): 33,
        ("env", "LLM_TYPE_OVERRIDE"): "anthropic",
    })
    mock_c.set = MagicMock()

    result = configure_llm_override_lockdown(33)

    assert result is True
    mock_c.set.assert_called_once_with("system", "llm_overrides_locked", True)
    mock_bt.logging.warning.assert_called_once()
    assert "ignored" in mock_bt.logging.warning.call_args[0][0]


@patch("conversationgenome.llm.llm_factory.bt")
@patch("conversationgenome.llm.llm_factory.c")
def test_configure_lockdown_testnet_with_override_warns_but_allows(mock_c, mock_bt):
    mock_c.get.side_effect = _c_get({
        ("network", "mainnet"): 33,
        ("env", "OPENAI_MODEL"): "gpt-custom",
    })
    mock_c.set = MagicMock()

    result = configure_llm_override_lockdown(138)

    assert result is False
    mock_c.set.assert_called_once_with("system", "llm_overrides_locked", False)
    mock_bt.logging.warning.assert_called_once()
    assert "Honoring" in mock_bt.logging.warning.call_args[0][0]


@patch("conversationgenome.llm.llm_factory.bt")
@patch("conversationgenome.llm.llm_factory.c")
def test_configure_lockdown_testnet_no_override_no_warning(mock_c, mock_bt):
    mock_c.get.side_effect = _c_get({("network", "mainnet"): 33})
    mock_c.set = MagicMock()

    result = configure_llm_override_lockdown(138)

    assert result is False
    mock_bt.logging.warning.assert_not_called()


@patch("conversationgenome.llm.llm_openai.OpenAI")
@patch("conversationgenome.llm.llm_openai.c")
@patch("conversationgenome.llm.llm_factory.c")
def test_get_llm_backend_locked_forces_openai_ignoring_explicit_override(mock_factory_c, mock_openai_c, mock_openai_client):
    mock_factory_c.get.side_effect = _c_get({("system", "llm_overrides_locked"): True})
    mock_openai_c.get.side_effect = _c_get({("env", "OPENAI_API_KEY"): "test-key"})

    llm = get_llm_backend(llm_type_override="anthropic")

    assert isinstance(llm, LlmOpenAI)
    assert llm.model == "gpt-5.2"


@patch("conversationgenome.llm.llm_openai.OpenAI")
@patch("conversationgenome.llm.llm_openai.c")
@patch("conversationgenome.llm.llm_factory.c")
def test_get_llm_backend_unlocked_honors_override(mock_factory_c, mock_openai_c, mock_openai_client):
    mock_factory_c.get.side_effect = _c_get({
        ("system", "llm_overrides_locked"): False,
        ("env", "LLM_TYPE_OVERRIDE"): None,
    })

    llm = get_llm_backend(llm_type_override=None)

    assert isinstance(llm, LlmOpenAI)


@patch("conversationgenome.llm.llm_factory.c")
def test_get_llm_backend_never_locked_for_miner_process(mock_c):
    """Miners never call configure_llm_override_lockdown, so the flag defaults to False
    and get_llm_backend() honors overrides exactly as before."""
    with patch("conversationgenome.llm.llm_openrouter.c") as mock_openrouter_c, \
         patch("conversationgenome.llm.llm_openrouter.OpenAI"):
        mock_c.get.side_effect = _c_get({
            ("system", "llm_overrides_locked"): False,
            ("env", "LLM_TYPE_OVERRIDE"): "openrouter",
        })
        mock_openrouter_c.get.side_effect = _c_get({
            ("env", "OPENROUTER_API_KEY"): "test-key",
            ("env", "OPENROUTER_MODEL"): "test-model",
        })

        from conversationgenome.llm.llm_openrouter import LlmOpenRouter

        llm = get_llm_backend()

        assert isinstance(llm, LlmOpenRouter)
