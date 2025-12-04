from unittest.mock import AsyncMock, MagicMock, Mock
from unittest.mock import patch

import pytest

from tests.mocks.DummyData import DummyData


@pytest.mark.asyncio
async def test_mine_returns_expected_tags_and_vectors():
    task = DummyData.survey_tagging_task()
    # Mock LlmLib and its conversation_to_metadata method
    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = ["greeting"]
    mock_result.vectors = [[0.1, 0.2]]
    mock_llml.survey_to_metadata = Mock(return_value=mock_result)
    with patch("conversationgenome.task.SurveyTaggingTask.get_llm_backend", return_value = mock_llml):
        result = await task.mine()
        assert result["tags"] == ["greeting"]
        assert result["vectors"] == [[0.1, 0.2]]


@pytest.mark.asyncio
async def test_mine_handles_empty_tags_and_vectors():
    # Mock LlmLib and its conversation_to_metadata method to return empty tags and vectors
    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = []
    mock_result.vectors = []
    mock_llml.survey_to_metadata = Mock(return_value=mock_result)
    with patch("conversationgenome.task.SurveyTaggingTask.get_llm_backend", return_value = mock_llml):

        task = DummyData.survey_tagging_task()
        task.prompt_chain = [type("Prompt", (), {"prompt_template": "Tag the Survey."})()]

        result = await task.mine()

        assert result["tags"] == []
        assert result["vectors"] == []


@pytest.mark.asyncio
async def test_mine_handles_none_tags_and_vectors():
    # Mock LlmLib and its conversation_to_metadata method to return None for tags and vectors
    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = None
    mock_result.vectors = None
    mock_llml.survey_to_metadata = Mock(return_value=mock_result)
    with patch("conversationgenome.task.SurveyTaggingTask.get_llm_backend", return_value = mock_llml):

        task = DummyData.survey_tagging_task()
        task.prompt_chain = [type("Prompt", (), {"prompt_template": "Tag the Survey."})()]

        result = await task.mine()

        assert result["tags"] is None
        assert result["vectors"] is None


@pytest.mark.asyncio
async def test_mine_handles_exception_from_llmlib_raises_error():
    # Mock LlmLib to raise an exception
    mock_llml = MagicMock()
    mock_llml.survey_to_metadata = Mock(side_effect=Exception("Mining failed"))
    with patch("conversationgenome.task.SurveyTaggingTask.get_llm_backend", return_value = mock_llml):
        task = DummyData.survey_tagging_task()
        task.prompt_chain = [type("Prompt", (), {"prompt_template": "Tag the Survey."})()]

        with pytest.raises(Exception, match="Mining failed"):
            await task.mine()
