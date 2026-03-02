from unittest.mock import AsyncMock, MagicMock, Mock, call
from unittest.mock import patch

import pytest

from conversationgenome.task.NamedEntitiesExtrationTask import NamedEntitiesExtractionTask, NamedEntitiesExtractionTaskInput, NamedEntitiesExtractionTaskInputData
from tests.mocks.DummyData import DummyData


@pytest.mark.asyncio
async def test_mine_returns_expected_tags():
    # Create a mock task with test data
    task = NamedEntitiesExtractionTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="named_entities_extraction",
        input=NamedEntitiesExtractionTaskInput(
            guid="input-guid",
            input_type="document",
            data=NamedEntitiesExtractionTaskInputData(
                window_idx=0,
                window=[(0, "John Smith works at Apple Inc."), (1, "He lives in New York.")],
                participants=["SPEAKER_1"]
            )
        )
    )

    # Mock the LLM backend
    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = ["John Smith", "Apple Inc", "New York"]
    mock_llml.raw_transcript_to_named_entities = Mock(return_value=mock_result)
    mock_llml.enrichment_to_NER = Mock(return_value=mock_result)
    mock_llml.combine_named_entities = Mock(return_value=mock_result)

    with patch("conversationgenome.task.NamedEntitiesExtrationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == ["John Smith", "Apple Inc", "New York"]
        # Verify the transcript was constructed correctly
        mock_llml.raw_transcript_to_named_entities.assert_called_once_with("John Smith works at Apple Inc.", generateEmbeddings=False)
        mock_llml.enrichment_to_NER.assert_called_once_with("He lives in New York.", generateEmbeddings=False)
        mock_llml.combine_named_entities.assert_called_once()

@pytest.mark.asyncio
async def test_mine_handles_empty_tags():
    task = NamedEntitiesExtractionTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="named_entities_extraction",
        input=NamedEntitiesExtractionTaskInput(
            guid="input-guid",
            input_type="document",
            data=NamedEntitiesExtractionTaskInputData(
                window_idx=0,
                window=[(0, "This is a simple sentence."), (1, "No named entities here.")],
                participants=["SPEAKER_1"]
            )
        )
    )

    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = []
    mock_llml.raw_transcript_to_named_entities = Mock(return_value=mock_result)
    mock_llml.enrichment_to_NER = Mock(return_value=mock_result)
    mock_llml.combine_named_entities = Mock(return_value=mock_result)

    with patch("conversationgenome.task.NamedEntitiesExtrationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == []


@pytest.mark.asyncio
async def test_mine_handles_none_result():
    task = NamedEntitiesExtractionTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="named_entities_extraction",
        input=NamedEntitiesExtractionTaskInput(
            guid="input-guid",
            input_type="document",
            data=NamedEntitiesExtractionTaskInputData(
                window_idx=0,
                window=[(0, "Test content")],
                participants=["SPEAKER_1"]
            )
        )
    )

    mock_llml = MagicMock()
    mock_llml.raw_transcript_to_named_entities = Mock(return_value=None)

    with patch("conversationgenome.task.NamedEntitiesExtrationTask.get_llm_backend", return_value=mock_llml):
        await task.mine()


@pytest.mark.asyncio
async def test_mine_handles_exception_from_llm():
    task = NamedEntitiesExtractionTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="named_entities_extraction",
        input=NamedEntitiesExtractionTaskInput(
            guid="input-guid",
            input_type="document",
            data=NamedEntitiesExtractionTaskInputData(
                window_idx=0,
                window=[(0, "Test content")],
                participants=["SPEAKER_1"]
            )
        )
    )

    mock_llml = MagicMock()
    mock_llml.raw_transcript_to_named_entities = Mock(side_effect=Exception("LLM Error"))

    with patch("conversationgenome.task.NamedEntitiesExtrationTask.get_llm_backend", return_value=mock_llml):
        with pytest.raises(Exception, match="LLM Error"):
            await task.mine()


@pytest.mark.asyncio
async def test_mine_handles_empty_window():
    task = NamedEntitiesExtractionTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="named_entities_extraction",
        input=NamedEntitiesExtractionTaskInput(
            guid="input-guid",
            input_type="document",
            data=NamedEntitiesExtractionTaskInputData(
                window_idx=0,
                window=[],
                participants=["SPEAKER_1"]
            )
        )
    )

    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = []
    mock_llml.raw_transcript_to_named_entities = Mock(return_value=mock_result)
    mock_llml.enrichment_to_NER = Mock(return_value=mock_result)
    mock_llml.combine_named_entities = Mock(return_value=mock_result)

    with patch("conversationgenome.task.NamedEntitiesExtrationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()
        assert result["tags"] == []


@pytest.mark.asyncio
async def test_mine_constructs_transcript_correctly():
    task = NamedEntitiesExtractionTask(
        mode="local",
        api_version=1.4,
        guid="test-guid",
        bundle_guid="bundle-guid",
        type="named_entities_extraction",
        input=NamedEntitiesExtractionTaskInput(
            guid="input-guid",
            input_type="document",
            data=NamedEntitiesExtractionTaskInputData(
                window_idx=0,
                window=[
                    (0, "First line of text."),
                    (0, "Second line with entities."),
                    (0, "Third line here.")
                ],
                participants=["SPEAKER_1"]
            )
        )
    )

    mock_llml = MagicMock()
    mock_result = Mock()
    mock_result.tags = ["entity1", "entity2"]
    mock_llml.raw_transcript_to_named_entities = Mock(return_value=mock_result)
    mock_llml.enrichment_to_NER = Mock(return_value=mock_result)
    mock_llml.combine_named_entities = Mock(return_value=mock_result)

    with patch("conversationgenome.task.NamedEntitiesExtrationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == ["entity1", "entity2"]
        # Verify the transcript is joined with '/n' separator
        expected_transcript = "First line of text."
        expected_webpages = [call("Second line with entities.", generateEmbeddings=False), call("Third line here.", generateEmbeddings=False)]
        mock_llml.raw_transcript_to_named_entities.assert_called_once_with(expected_transcript, generateEmbeddings=False)
        mock_llml.enrichment_to_NER.assert_has_calls(expected_webpages)
        mock_llml.combine_named_entities.assert_called_once()