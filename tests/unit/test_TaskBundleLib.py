from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conversationgenome.api.ApiLib import ApiLib
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.task_bundle.TaskBundleLib import TaskBundleLib
from tests.mocks.DummyData import DummyData

hotkey = "hotkey123"
api_key = "apikey123secret"

override_env_variables = {"SYSTEM_MODE": "prod", "CGP_API_READ_HOST": "https://fake.api", "CGP_API_READ_PORT": "443", "HTTP_TIMEOUT": 10, "MAX_CONVO_LINES": 100}


@pytest.mark.asyncio
@patch("conversationgenome.api.ApiLib.requests.post")
@patch("conversationgenome.api.ApiLib.c.get")
@patch("conversationgenome.task_bundle.ConversationTaggingTaskBundle.LlmLib")
async def test_when_getting_task_bundle_then_max_lines_is_respected(mock_llm_lib, mock_config_get, mock_requests_post):
    mock_llm_instance = AsyncMock()
    mock_llm_instance.conversation_to_metadata.return_value = None
    mock_llm_lib.return_value = mock_llm_instance

    MAX_CONVO_LINES = 1

    def config_side_effect(section, key, default=None):
        overrides = override_env_variables
        overrides["MAX_CONVO_LINES"] = MAX_CONVO_LINES
        return overrides.get(key, default)

    mock_config_get.side_effect = config_side_effect

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = DummyData.conversation_tagging_task_bundle_json()
    mock_requests_post.return_value = mock_response

    tbl = TaskBundleLib()
    task_bundle: TaskBundle = await tbl.get_task_bundle(hotkey=hotkey, api_key=api_key)

    assert len(task_bundle.input.data.lines) == MAX_CONVO_LINES
    assert task_bundle.input.data.lines == DummyData.lines()[0:MAX_CONVO_LINES]
