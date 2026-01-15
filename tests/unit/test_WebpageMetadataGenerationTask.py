from unittest.mock import AsyncMock, MagicMock, Mock
from unittest.mock import patch

import pytest

from conversationgenome.prompt_chain.PromptChainStep import PromptChainStep
from conversationgenome.task.WebpageMetadataGenerationTask import WebpageMetadataGenerationTask, WebpageMarkdownTaskInput, WebpageMarkdownTaskInputData
from tests.mocks.DummyData import DummyData


@pytest.mark.asyncio
async def test_mine_returns_expected_tags_and_vectors():
    # Create a mock task with test data
    task = WebpageMetadataGenerationTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="webpage_metadata_generation",
        input=WebpageMarkdownTaskInput(
            guid="input-guid",
            input_type="webpage_markdown",
            data=WebpageMarkdownTaskInputData(
                window=[(0, "This is webpage content."), (1, "It contains metadata.")],
                participants=["SPEAKER_1"]
            )
        ),
        prompt_chain=[PromptChainStep(
            step=0,
            id="test-id",
            crc=12345,
            title="Extract metadata",
            name="extract_metadata",
            description="Extract metadata from webpage",
            type="inference",
            input_path="conversation",
            prompt_template="Extract metadata from webpage",
            output_variable="metadata",
            output_type="dict"
        )]
    )

    # Mock the LLM backend
    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = ["webpage", "metadata", "content"]
    mock_result.vectors = {"webpage": [0.1, 0.2], "metadata": [0.3, 0.4], "content": [0.5, 0.6]}
    mock_llml.conversation_to_metadata = Mock(return_value=mock_result)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == ["webpage", "metadata", "content"]
        assert result["vectors"] == {"webpage": [0.1, 0.2], "metadata": [0.3, 0.4], "content": [0.5, 0.6]}
        # Verify the conversation was constructed correctly
        mock_llml.conversation_to_metadata.assert_called_once()
        call_args = mock_llml.conversation_to_metadata.call_args
        conversation = call_args[1]['conversation']
        assert conversation.guid == "input-guid"
        assert conversation.lines == [(0, "This is webpage content."), (1, "It contains metadata.")]
        assert conversation.miner_task_prompt == "Extract metadata from webpage"
        assert call_args[1]['generateEmbeddings'] is False


@pytest.mark.asyncio
async def test_mine_handles_empty_tags_and_vectors():
    task = WebpageMetadataGenerationTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="webpage_metadata_generation",
        input=WebpageMarkdownTaskInput(
            guid="input-guid",
            input_type="webpage_markdown",
            data=WebpageMarkdownTaskInputData(
                window=[(0, "Empty content")],
                participants=["SPEAKER_1"]
            )
        ),
        prompt_chain=[PromptChainStep(
            step=0,
            id="test-id",
            crc=12345,
            title="Extract metadata",
            name="extract_metadata",
            description="Extract metadata from webpage",
            type="inference",
            input_path="conversation",
            prompt_template="Extract metadata",
            output_variable="metadata",
            output_type="dict"
        )]
    )

    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = []
    mock_result.vectors = {}
    mock_llml.conversation_to_metadata = Mock(return_value=mock_result)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == []
        assert result["vectors"] == {}


@pytest.mark.asyncio
async def test_mine_handles_none_result():
    task = WebpageMetadataGenerationTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="webpage_metadata_generation",
        input=WebpageMarkdownTaskInput(
            guid="input-guid",
            input_type="webpage_markdown",
            data=WebpageMarkdownTaskInputData(
                window=[(0, "Test content")],
                participants=["SPEAKER_1"]
            )
        ),
        prompt_chain=[PromptChainStep(
            step=0,
            id="test-id",
            crc=12345,
            title="Extract metadata",
            name="extract_metadata",
            description="Extract metadata from webpage",
            type="inference",
            input_path="conversation",
            prompt_template="Extract metadata",
            output_variable="metadata",
            output_type="dict"
        )]
    )

    mock_llml = MagicMock()
    mock_llml.conversation_to_metadata = Mock(return_value=None)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        # The current implementation doesn't handle None result and will raise AttributeError
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'tags'"):
            await task.mine()


@pytest.mark.asyncio
async def test_mine_handles_exception_from_llm():
    task = WebpageMetadataGenerationTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="webpage_metadata_generation",
        input=WebpageMarkdownTaskInput(
            guid="input-guid",
            input_type="webpage_markdown",
            data=WebpageMarkdownTaskInputData(
                window=[(0, "Test content")],
                participants=["SPEAKER_1"]
            )
        ),
        prompt_chain=[PromptChainStep(
            step=0,
            id="test-id",
            crc=12345,
            title="Extract metadata",
            name="extract_metadata",
            description="Extract metadata from webpage",
            type="inference",
            input_path="conversation",
            prompt_template="Extract metadata",
            output_variable="metadata",
            output_type="dict"
        )]
    )

    mock_llml = MagicMock()
    mock_llml.conversation_to_metadata = Mock(side_effect=Exception("LLM Error"))

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        with pytest.raises(Exception, match="LLM Error"):
            await task.mine()


@pytest.mark.asyncio
async def test_mine_handles_empty_window():
    task = WebpageMetadataGenerationTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="webpage_metadata_generation",
        input=WebpageMarkdownTaskInput(
            guid="input-guid",
            input_type="webpage_markdown",
            data=WebpageMarkdownTaskInputData(
                window=[],
                participants=["SPEAKER_1"]
            )
        ),
        prompt_chain=[PromptChainStep(
            step=0,
            id="test-id",
            crc=12345,
            title="Extract metadata",
            name="extract_metadata",
            description="Extract metadata from webpage",
            type="inference",
            input_path="conversation",
            prompt_template="Extract metadata",
            output_variable="metadata",
            output_type="dict"
        )]
    )

    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = []
    mock_result.vectors = {}
    mock_llml.conversation_to_metadata = Mock(return_value=mock_result)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == []
        assert result["vectors"] == {}
        # Verify empty window was passed
        call_args = mock_llml.conversation_to_metadata.call_args
        conversation = call_args[1]['conversation']
        assert conversation.lines == []


@pytest.mark.asyncio
async def test_mine_constructs_conversation_correctly():
    task = WebpageMetadataGenerationTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="webpage_metadata_generation",
        input=WebpageMarkdownTaskInput(
            guid="input-guid",
            input_type="webpage_markdown",
            data=WebpageMarkdownTaskInputData(
                window=[
                    (0, "First line of webpage."),
                    (1, "Second line with content."),
                    (2, "Third line here.")
                ],
                participants=["SPEAKER_1"]
            )
        ),
        prompt_chain=[PromptChainStep(
            step=0,
            id="test-id",
            crc=12345,
            title="Extract metadata",
            name="extract_metadata",
            description="Extract metadata from webpage",
            type="inference",
            input_path="conversation",
            prompt_template="Custom prompt for metadata extraction",
            output_variable="metadata",
            output_type="dict"
        )]
    )

    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = ["webpage", "content"]
    mock_result.vectors = {"webpage": [0.1], "content": [0.2]}
    mock_llml.conversation_to_metadata = Mock(return_value=mock_result)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == ["webpage", "content"]
        assert result["vectors"] == {"webpage": [0.1], "content": [0.2]}
        # Verify the conversation was constructed correctly
        call_args = mock_llml.conversation_to_metadata.call_args
        conversation = call_args[1]['conversation']
        assert conversation.guid == "input-guid"
        assert conversation.lines == [
            (0, "First line of webpage."),
            (1, "Second line with content."),
            (2, "Third line here.")
        ]
        assert conversation.miner_task_prompt == "Custom prompt for metadata extraction"
        assert call_args[1]['generateEmbeddings'] is False