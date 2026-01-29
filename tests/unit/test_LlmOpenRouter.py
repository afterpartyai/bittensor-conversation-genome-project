import pytest
from unittest.mock import MagicMock, patch
from conversationgenome.llm.llm_openrouter import LlmOpenRouter
from conversationgenome.llm.llm_factory import get_llm_backend

@pytest.fixture
def mock_config():
    with patch('conversationgenome.llm.llm_openrouter.c') as mock:
        mock.get.side_effect = lambda section, key, default=None: {
            'OPENROUTER_API_KEY': 'test_key',
            'OPENROUTER_MODEL': 'test_model',
            'OPENROUTER_PROVIDER_PREFERENCE': 'chutes',
            'OPENROUTER_EMBEDDING_MODEL': 'test_emb_model'
        }.get(key, default)
        yield mock

def test_llm_openrouter_init(mock_config):
    with patch('conversationgenome.llm.llm_openrouter.OpenAI') as mock_openai:
        llm = LlmOpenRouter()
        assert llm.model == 'test_model'
        assert llm.provider_preference == 'chutes'
        mock_openai.assert_called_once_with(
            base_url="https://openrouter.ai/api/v1",
            api_key='test_key'
        )

def test_llm_openrouter_basic_prompt(mock_config):
    with patch('conversationgenome.llm.llm_openrouter.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices[0].message.content = "test response"
        
        llm = LlmOpenRouter()
        response = llm.basic_prompt("test prompt")
        
        assert response == "test response"
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs['model'] == 'test_model'
        assert kwargs['extra_body']['provider']['order'] == ['chutes']

def test_llm_factory_registration():
    with patch('conversationgenome.llm.llm_factory.c') as mock_c:
        mock_c.get.return_value = "openrouter"
        with patch('conversationgenome.llm.llm_openrouter.OpenAI'), \
             patch('conversationgenome.llm.llm_openrouter.c'):
            llm = get_llm_backend()
            assert isinstance(llm, LlmOpenRouter)
