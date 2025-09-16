from unittest.mock import AsyncMock, patch

import pytest

from conversationgenome.task.ConversationTaggingTask import ConversationTaskInput, ConversationTaskInputData
from tests.mocks.DummyData import DummyData


@pytest.mark.asyncio
async def test_mine_returns_expected_tags_and_vectors():
    # Mock LlmLib and its conversation_to_metadata method
    with patch("conversationgenome.task.ConversationTaggingTask.LlmLib") as MockLlmLib:
        mock_llml = MockLlmLib.return_value
        mock_result = AsyncMock()
        mock_result.tags = ["greeting"]
        mock_result.vectors = [[0.1, 0.2]]
        mock_llml.conversation_to_metadata = AsyncMock(return_value=mock_result)

        task = DummyData.conversation_tagging_task()
        task.prompt_chain = [type("Prompt", (), {"prompt_template": "Tag the conversation."})()]

        result = await task.mine()

        assert result["tags"] == ["greeting"]
        assert result["vectors"] == [[0.1, 0.2]]
