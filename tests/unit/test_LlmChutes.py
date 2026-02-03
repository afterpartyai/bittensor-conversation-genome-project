import pytest
from unittest.mock import MagicMock, patch
from conversationgenome.llm.llm_chutes import LlmChutes
from conversationgenome.llm.llm_factory import get_llm_backend

@pytest.fixture
def mock_config():
    with patch('conversationgenome.llm.llm_chutes.c') as mock:
        mock.get.side_effect = lambda section, key, default=None: {
            'CHUTES_API_KEY': 'test_chutes_key',
            'CHUTES_MODEL': 'test_chutes_model',
            'CHUTES_EMBEDDING_MODEL': 'test_emb_model'
        }.get(key, default)
        yield mock

def test_llm_chutes_init(mock_config):
    with patch('conversationgenome.llm.llm_chutes.OpenAI') as mock_openai:
        llm = LlmChutes()
        assert llm.model == 'test_chutes_model'
        mock_openai.assert_called_once_with(
            base_url="https://llm.chutes.ai/v1",
            api_key='test_chutes_key'
        )

def test_llm_chutes_basic_prompt(mock_config):
    with patch('conversationgenome.llm.llm_chutes.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices[0].message.content = "test chutes response"
        
        llm = LlmChutes()
        response = llm.basic_prompt("test chutes prompt")
        
        assert response == "test chutes response"
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs['model'] == 'test_chutes_model'

def test_llm_factory_chutes_registration():
    with patch('conversationgenome.llm.llm_factory.c') as mock_c:
        mock_c.get.return_value = "chutes"
        with patch('conversationgenome.llm.llm_chutes.OpenAI'), \
             patch('conversationgenome.llm.llm_chutes.c'):
            llm = get_llm_backend()
            assert isinstance(llm, LlmChutes)
