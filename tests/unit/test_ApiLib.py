from unittest.mock import MagicMock, patch

import pytest

from conversationgenome.api.ApiLib import ApiLib
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from tests.mocks.DummyData import DummyData

hotkey = "hotkey123"
api_key = "apikey123secret"

override_env_variables = {"SYSTEM_MODE": "prod", "CGP_API_READ_HOST": "https://fake.api", "CGP_API_READ_PORT": "443", "HTTP_TIMEOUT": 10, "MAX_CONVO_LINES": 100}


@pytest.mark.asyncio
@patch("conversationgenome.api.ApiLib.requests.post")
@patch("conversationgenome.api.ApiLib.c.get")
async def test_when_reserving_conversation_then_conversation_is_returned(mock_config_get, mock_requests_post):
    def config_side_effect(section, key, default=None):
        overrides = override_env_variables
        return overrides.get(key, default)

    mock_config_get.side_effect = config_side_effect

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = DummyData.conversation_tagging_task_bundle()
    mock_requests_post.return_value = mock_response

    api = ApiLib()
    task_bundle = await api.reserve_task_bundle(hotkey=hotkey, api_key=api_key)

    assert isinstance(task_bundle, TaskBundle)
    assert task_bundle.type == "conversation_tagging"


@pytest.mark.asyncio
@patch("conversationgenome.api.ApiLib.requests.post")
@patch("conversationgenome.api.ApiLib.c.get")
async def test_when_reserving_conversation_then_endpoint_is_called_properly(mock_config_get, mock_requests_post):
    def config_side_effect(section, key, default=None):
        overrides = override_env_variables
        return overrides.get(key, default)

    mock_config_get.side_effect = config_side_effect

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = DummyData.conversation_tagging_task_json()
    mock_requests_post.return_value = mock_response

    api = ApiLib()
    task_bundle = await api.reserve_task_bundle(hotkey=hotkey, api_key=api_key)

    args, kwargs = mock_requests_post.call_args
    assert "https://fake.api:443/api/v1/conversation/reserve" in args[0]
    assert kwargs["headers"]["Authorization"] == f"Bearer {api_key}"
