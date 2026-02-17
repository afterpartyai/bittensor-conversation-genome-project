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
                window=[(0, "This is webpage content."), (1, "Enrichment content here.")],
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
    
    # Mock website_to_metadata for main content
    website_result = Mock()
    website_result.tags = ["webpage", "content"]
    mock_llml.website_to_metadata = Mock(return_value=website_result)
    
    # Mock enrichment_to_metadata for enrichment content
    enrichment_result = Mock()
    enrichment_result.tags = ["enrichment", "metadata"]
    mock_llml.enrichment_to_metadata = Mock(return_value=enrichment_result)
    
    # Mock combine_metadata_tags
    combined_result = Mock()
    combined_result.tags = ["webpage", "content", "enrichment", "metadata"]
    combined_result.vectors = {"webpage": [0.1, 0.2], "content": [0.3, 0.4], "enrichment": [0.5, 0.6], "metadata": [0.7, 0.8]}
    mock_llml.combine_metadata_tags = Mock(return_value=combined_result)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == ["webpage", "content", "enrichment", "metadata"]
        assert result["vectors"] == {"webpage": [0.1, 0.2], "content": [0.3, 0.4], "enrichment": [0.5, 0.6], "metadata": [0.7, 0.8]}
        
        # Verify website_to_metadata was called for main content
        mock_llml.website_to_metadata.assert_called_once_with("This is webpage content.", generateEmbeddings=False)
        
        # Verify enrichment_to_metadata was called for enrichment content
        mock_llml.enrichment_to_metadata.assert_called_once_with("Enrichment content here.", generateEmbeddings=False)
        
        # Verify combine_metadata_tags was called with both tag sets
        mock_llml.combine_metadata_tags.assert_called_once_with([["webpage", "content"], ["enrichment", "metadata"]], generateEmbeddings=False)


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
    mock_llml.website_to_metadata = Mock(return_value=mock_result)
    mock_llml.combine_metadata_tags = Mock(return_value=None)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == []
        assert result["vectors"] is None


@pytest.mark.asyncio
async def test_mine_processes_only_webpage_content():
    """Test mining with only webpage content (no enrichment)"""
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
                window=[(0, "This is webpage content about AI.")],
                participants=[]
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
            input_path="webpage_markdown",
            prompt_template="Extract metadata from webpage",
            output_variable="metadata",
            output_type="dict"
        )]
    )

    mock_llml = MagicMock()
    
    # Mock website_to_metadata
    website_result = Mock()
    website_result.tags = ["artificial", "intelligence", "webpage"]
    mock_llml.website_to_metadata = Mock(return_value=website_result)
    
    # Mock combine_metadata_tags
    combined_result = Mock()
    combined_result.tags = ["artificial", "intelligence", "webpage"]
    combined_result.vectors = {"artificial": [0.1], "intelligence": [0.2], "webpage": [0.3]}
    mock_llml.combine_metadata_tags = Mock(return_value=combined_result)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == ["artificial", "intelligence", "webpage"]
        assert result["vectors"] == {"artificial": [0.1], "intelligence": [0.2], "webpage": [0.3]}
        
        # Verify only website_to_metadata was called
        mock_llml.website_to_metadata.assert_called_once_with("This is webpage content about AI.", generateEmbeddings=False)
        mock_llml.enrichment_to_metadata.assert_not_called()
        mock_llml.combine_metadata_tags.assert_called_once_with([["artificial", "intelligence", "webpage"]], generateEmbeddings=False)


@pytest.mark.asyncio
async def test_mine_processes_webpage_and_enrichment():
    """Test mining with both webpage content and enrichment"""
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
                    (0, "Main webpage about machine learning."),
                    (1, "AI Research Breakthrough\nNew developments in ML research."),
                    (2, "Tech News Update\nLatest AI advancements announced.")
                ],
                participants=[]
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
            input_path="webpage_markdown",
            prompt_template="Extract metadata from webpage",
            output_variable="metadata",
            output_type="dict"
        )]
    )

    mock_llml = MagicMock()
    
    # Mock website_to_metadata for main content
    website_result = Mock()
    website_result.tags = ["machine", "learning"]
    mock_llml.website_to_metadata = Mock(return_value=website_result)
    
    # Mock enrichment_to_metadata for both enrichment items
    enrichment_result1 = Mock()
    enrichment_result1.tags = ["ai", "research"]
    enrichment_result2 = Mock()
    enrichment_result2.tags = ["tech", "news"]
    mock_llml.enrichment_to_metadata = Mock(side_effect=[enrichment_result1, enrichment_result2])
    
    # Mock combine_metadata_tags
    combined_result = Mock()
    combined_result.tags = ["machine", "learning", "ai", "research", "tech", "news"]
    combined_result.vectors = {"machine": [0.1], "learning": [0.2], "ai": [0.3], "research": [0.4], "tech": [0.5], "news": [0.6]}
    mock_llml.combine_metadata_tags = Mock(return_value=combined_result)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == ["machine", "learning", "ai", "research", "tech", "news"]
        assert result["vectors"] == {"machine": [0.1], "learning": [0.2], "ai": [0.3], "research": [0.4], "tech": [0.5], "news": [0.6]}
        
        # Verify website_to_metadata was called once for main content
        mock_llml.website_to_metadata.assert_called_once_with("Main webpage about machine learning.", generateEmbeddings=False)
        
        # Verify enrichment_to_metadata was called twice
        assert mock_llml.enrichment_to_metadata.call_count == 2
        mock_llml.enrichment_to_metadata.assert_any_call("AI Research Breakthrough\nNew developments in ML research.", generateEmbeddings=False)
        mock_llml.enrichment_to_metadata.assert_any_call("Tech News Update\nLatest AI advancements announced.", generateEmbeddings=False)
        
        # Verify combine_metadata_tags was called with all tag sets
        expected_tag_sets = [["machine", "learning"], ["ai", "research"], ["tech", "news"]]
        mock_llml.combine_metadata_tags.assert_called_once_with(expected_tag_sets, generateEmbeddings=False)


@pytest.mark.asyncio
async def test_mine_handles_llm_method_failures():
    """Test mining when LLM methods return None or fail"""
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
                    (0, "Main webpage content."),
                    (1, "Enrichment content.")
                ],
                participants=[]
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
            input_path="webpage_markdown",
            prompt_template="Extract metadata from webpage",
            output_variable="metadata",
            output_type="dict"
        )]
    )

    mock_llml = MagicMock()
    
    # Mock website_to_metadata to return None (failure)
    mock_llml.website_to_metadata = Mock(return_value=None)
    
    # Mock enrichment_to_metadata to return a result
    enrichment_result = Mock()
    enrichment_result.tags = ["enrichment", "tags"]
    mock_llml.enrichment_to_metadata = Mock(return_value=enrichment_result)
    
    # Mock combine_metadata_tags
    combined_result = Mock()
    combined_result.tags = ["enrichment", "tags"]
    combined_result.vectors = {"enrichment": [0.1], "tags": [0.2]}
    mock_llml.combine_metadata_tags = Mock(return_value=combined_result)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        # Should still return results from enrichment even if main webpage fails
        assert result["tags"] == ["enrichment", "tags"]
        assert result["vectors"] == {"enrichment": [0.1], "tags": [0.2]}
        
        # Verify methods were called
        mock_llml.website_to_metadata.assert_called_once()
        mock_llml.enrichment_to_metadata.assert_called_once()
        mock_llml.combine_metadata_tags.assert_called_once_with([["enrichment", "tags"]], generateEmbeddings=False)


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
    mock_llml.website_to_metadata = Mock(return_value=None)
    mock_llml.combine_metadata_tags = Mock(return_value=None)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()
        # Should return empty results when all LLM calls fail
        assert result["tags"] == []
        assert result["vectors"] is None


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
    mock_llml.website_to_metadata = Mock(side_effect=Exception("LLM Error"))

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

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == []
        assert result["vectors"] is None
        # Empty window should not call any LLM methods
        mock_llml.website_to_metadata.assert_not_called()
        mock_llml.enrichment_to_metadata.assert_not_called()
        mock_llml.combine_metadata_tags.assert_not_called()


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
    
    # Mock website_to_metadata for first line
    website_result = Mock()
    website_result.tags = ["webpage"]
    mock_llml.website_to_metadata = Mock(return_value=website_result)
    
    # Mock enrichment_to_metadata for second and third lines
    enrichment_result = Mock()
    enrichment_result.tags = ["content"]
    mock_llml.enrichment_to_metadata = Mock(return_value=enrichment_result)
    
    # Mock combine_metadata_tags
    combined_result = Mock()
    combined_result.tags = ["webpage", "content"]
    combined_result.vectors = {"webpage": [0.1], "content": [0.2]}
    mock_llml.combine_metadata_tags = Mock(return_value=combined_result)

    with patch("conversationgenome.task.WebpageMetadataGenerationTask.get_llm_backend", return_value=mock_llml):
        result = await task.mine()

        assert result["tags"] == ["webpage", "content"]
        assert result["vectors"] == {"webpage": [0.1], "content": [0.2]}
        
        # Verify website_to_metadata was called with the first line
        mock_llml.website_to_metadata.assert_called_once_with("First line of webpage.", generateEmbeddings=False)
        
        # Verify enrichment_to_metadata was called for the other two lines
        assert mock_llml.enrichment_to_metadata.call_count == 2
        mock_llml.enrichment_to_metadata.assert_any_call("Second line with content.", generateEmbeddings=False)
        mock_llml.enrichment_to_metadata.assert_any_call("Third line here.", generateEmbeddings=False)
        
        # Verify combine_metadata_tags was called with all tag sets
        expected_tag_sets = [["webpage"], ["content"], ["content"]]
        mock_llml.combine_metadata_tags.assert_called_once_with(expected_tag_sets, generateEmbeddings=False)