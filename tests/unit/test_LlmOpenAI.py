from unittest.mock import patch

from conversationgenome.llm.llm_openai import DEFAULT_MODEL
from conversationgenome.llm.llm_openai import LlmOpenAI


def _c_get(overrides):
    def get(section, key, default=None):
        return overrides.get((section, key), default)
    return get


@patch("conversationgenome.llm.llm_openai.OpenAI")
@patch("conversationgenome.llm.llm_openai.c")
def test_model_override_honored_by_default(mock_c, mock_openai):
    mock_c.get.side_effect = _c_get({
        ("env", "OPENAI_API_KEY"): "test-key",
        ("env", "OPENAI_MODEL"): "gpt-custom",
    })

    llm = LlmOpenAI()

    assert llm.model == "gpt-custom"


@patch("conversationgenome.llm.llm_openai.OpenAI")
@patch("conversationgenome.llm.llm_openai.c")
def test_model_override_ignored_when_locked(mock_c, mock_openai):
    mock_c.get.side_effect = _c_get({
        ("env", "OPENAI_API_KEY"): "test-key",
        ("env", "OPENAI_MODEL"): "gpt-custom",
    })

    llm = LlmOpenAI(ignore_model_override=True)

    assert llm.model == DEFAULT_MODEL


@patch("conversationgenome.llm.llm_openai.OpenAI")
@patch("conversationgenome.llm.llm_openai.c")
def test_default_model_used_when_no_override_present(mock_c, mock_openai):
    mock_c.get.side_effect = _c_get({("env", "OPENAI_API_KEY"): "test-key"})

    llm = LlmOpenAI()

    assert llm.model == DEFAULT_MODEL
