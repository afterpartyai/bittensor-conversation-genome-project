from unittest.mock import AsyncMock, Mock, patch
import pytest
from conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle import WebpageMetadataGenerationTaskBundle
from tests.mocks.DummyData import DummyData


def test_is_ready_false_when_no_metadata():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    bundle.input.metadata = None
    assert not bundle.is_ready()


def test_is_ready_false_when_no_indexed_windows():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    bundle.input.data.indexed_windows = None
    assert not bundle.is_ready()


def test_is_ready_true_when_metadata_and_indexed_windows():
    bundle = DummyData.setup_webpage_metadata_generation_task_bundle()
    assert bundle.is_ready()


@pytest.mark.asyncio
async def test_setup_calls_trim_input_and_split_and_generate():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    with patch.object(bundle, '_split_conversation_in_windows') as mock_split, \
         patch.object(bundle, '_enforce_minimum_convo_windows') as mock_enforce, \
         patch.object(bundle, '_generate_metadata') as mock_generate:
        
        await bundle.setup()
        
        mock_split.assert_called_once()
        mock_enforce.assert_called_once()
        mock_generate.assert_called_once()


def test_to_mining_tasks_creates_tasks():
    bundle = DummyData.setup_webpage_metadata_generation_task_bundle()
    tasks = bundle.to_mining_tasks(2)
    assert len(tasks) == 2
    for task in tasks:
        assert task.type == "webpage_metadata_generation"
        assert task.bundle_guid == bundle.guid
        assert task.input.input_type == "webpage_markdown"


def test_to_mining_tasks_limits_to_requested_number():
    bundle = DummyData.setup_webpage_metadata_generation_task_bundle()
    # Ensure we have more windows than requested
    bundle.input.data.indexed_windows = [(i, []) for i in range(5)]
    tasks = bundle.to_mining_tasks(3)
    assert len(tasks) == 3


def test_generate_result_logs_counts_tags_and_vectors():
    bundle = DummyData.setup_webpage_metadata_generation_task_bundle()
    miner_result = {"tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1]}, "original_tags": ["tag1", "tag2", "tag3"]}
    log = bundle.generate_result_logs(miner_result)
    assert "tags: 2" in log
    assert "vector count: 1" in log
    assert "original tags: 3" in log


@pytest.mark.asyncio
async def test_format_results_validates_and_embeds_tags():
    bundle = DummyData.setup_webpage_metadata_generation_task_bundle()
    miner_result = {"tags": ["tag1", "tag2"]}
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.validate_tag_set.return_value = ["tag1", "tag2"]
        mock_llm_factory.return_value = mock_llm
        with patch.object(bundle, '_get_vector_embeddings_set', AsyncMock(return_value={"tag1": [0.1], "tag2": [0.2]})):
            result = await bundle.format_results(miner_result)
    assert result["original_tags"] == ["tag1", "tag2"]
    assert result["tags"] == ["tag1", "tag2"]
    assert result["vectors"] == {"tag1": [0.1], "tag2": [0.2]}


@pytest.mark.asyncio
async def test_evaluate_calls_ground_truth_scoring():
    bundle = DummyData.setup_webpage_metadata_generation_task_bundle()
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.GroundTruthTagSimilarityScoringMechanism') as mock_mech:
        mock_eval = AsyncMock(return_value="score")
        mock_mech.return_value.evaluate = mock_eval
        result = await bundle.evaluate(["response"])
    assert result == "score"


def test_split_conversation_in_windows_creates_indexed_windows():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    bundle.input.data.lines = DummyData.lines()
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.Utils.split_overlap_array') as mock_split:
        mock_split.return_value = [[(0, "line1"), (1, "line2")], [(2, "line3")]]
        bundle._split_conversation_in_windows()
        assert bundle.input.data.indexed_windows == [(0, [(0, "line1"), (1, "line2")]), (1, [(2, "line3")])]
        mock_split.assert_called()


def test_enforce_minimum_convo_windows_sets_empty_when_below_minimum():
    bundle = DummyData.setup_webpage_metadata_generation_task_bundle()
    bundle.input.data.min_convo_windows = 3
    bundle.input.data.indexed_windows = [(0, []), (1, [])]  # Only 2 windows
    bundle._enforce_minimum_convo_windows()
    assert bundle.input.data.indexed_windows == []


def test_enforce_minimum_convo_windows_keeps_when_above_minimum():
    bundle = DummyData.setup_webpage_metadata_generation_task_bundle()
    bundle.input.data.min_convo_windows = 1
    original_windows = bundle.input.data.indexed_windows
    bundle._enforce_minimum_convo_windows()
    assert bundle.input.data.indexed_windows == original_windows


@pytest.mark.asyncio
async def test_generate_metadata_calls_llm_and_sets_metadata():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    bundle.input.data.lines = DummyData.lines()
    bundle.input.data.participants = DummyData.participants()
    bundle.input.guid = DummyData.guid()
    
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.tags = ["tag1", "tag2"]
        mock_result.vectors = {"tag1": {"vectors": [0.1]}}
        mock_llm.conversation_to_metadata.return_value = mock_result
        mock_llm_factory.return_value = mock_llm
        
        await bundle._generate_metadata()
        
        assert bundle.input.metadata.tags == ["tag1", "tag2"]
        assert bundle.input.metadata.vectors == {"tag1": {"vectors": [0.1]}}


@pytest.mark.asyncio
async def test_generate_metadata_handles_failure():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    bundle.input.metadata = None  # Clear existing metadata
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_result = Mock()
        mock_result.success = False
        mock_llm.conversation_to_metadata.return_value = mock_result
        mock_llm_factory.return_value = mock_llm
        
        await bundle._generate_metadata()
        
        assert bundle.input.metadata is None


@pytest.mark.asyncio
async def test_get_vector_embeddings_set_calls_llm():
    bundle = DummyData.setup_webpage_metadata_generation_task_bundle()
    mock_llm = Mock()
    mock_llm.get_vector_embeddings_set.return_value = {"tag": [0.1]}
    result = await bundle._get_vector_embeddings_set(llml=mock_llm, tags=["tag"])
    assert result == {"tag": [0.1]}


@pytest.mark.asyncio
async def test_generate_metadata_with_enrichment():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    # Mock webpage data with enrichment
    bundle.input.data.lines = [(0, '{"website_markdown": "Main webpage about AI", "enrichment": {"search_results": {"query1": [{"title": "AI News", "snippet": "Latest AI developments"}]}}}')]
    
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        
        # Mock website_to_metadata
        website_result = Mock()
        website_result.tags = ["artificial intelligence"]
        mock_llm.website_to_metadata.return_value = website_result
        
        # Mock enrichment_to_metadata
        enrichment_result = Mock()
        enrichment_result.tags = ["machine learning"]
        mock_llm.enrichment_to_metadata.return_value = enrichment_result
        
        # Mock combine_metadata_tags
        combine_result = Mock()
        combine_result.success = True
        combine_result.tags = ["artificial intelligence", "machine learning"]
        combine_result.vectors = {"artificial intelligence": {"vectors": [0.1]}}
        mock_llm.combine_metadata_tags.return_value = combine_result
        
        mock_llm_factory.return_value = mock_llm
        
        await bundle._generate_metadata()
        
        # Verify website_to_metadata was called for main content
        mock_llm.website_to_metadata.assert_called_with("Main webpage about AI")
        
        # Verify enrichment_to_metadata was called for enrichment content
        mock_llm.enrichment_to_metadata.assert_called_with("AI News\nLatest AI developments")
        
        # Verify combine_metadata_tags was called with both tag sets
        mock_llm.combine_metadata_tags.assert_called_with([["artificial intelligence"], ["machine learning"]], generateEmbeddings=True)
        
        # Verify input data lines were updated
        assert len(bundle.input.data.lines) == 2
        assert bundle.input.data.lines[0] == (0, "Main webpage about AI")
        assert bundle.input.data.lines[1] == (0, "AI News\nLatest AI developments")


@pytest.mark.asyncio
async def test_generate_metadata_without_enrichment():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    # Mock webpage data without enrichment
    bundle.input.data.lines = [(0, '{"website_markdown": "Main webpage about AI", "enrichment": null}')]
    
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        
        # Mock website_to_metadata
        website_result = Mock()
        website_result.tags = ["artificial intelligence"]
        mock_llm.website_to_metadata.return_value = website_result
        
        # Mock combine_metadata_tags
        combine_result = Mock()
        combine_result.success = True
        combine_result.tags = ["artificial intelligence"]
        combine_result.vectors = {"artificial intelligence": {"vectors": [0.1]}}
        mock_llm.combine_metadata_tags.return_value = combine_result
        
        mock_llm_factory.return_value = mock_llm
        
        await bundle._generate_metadata()
        
        # Verify website_to_metadata was called
        mock_llm.website_to_metadata.assert_called_with("Main webpage about AI")
        
        # Verify enrichment_to_metadata was not called
        mock_llm.enrichment_to_metadata.assert_not_called()
        
        # Verify combine_metadata_tags was called with only website tags
        mock_llm.combine_metadata_tags.assert_called_with([["artificial intelligence"]], generateEmbeddings=True)
        
        # Verify input data lines contain only main content
        assert len(bundle.input.data.lines) == 1
        assert bundle.input.data.lines[0] == (0, "Main webpage about AI")


@pytest.mark.asyncio
async def test_generate_metadata_randomly_selects_enrichment_results():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    # Mock webpage data with multiple enrichment results
    bundle.input.data.lines = [(0, '{"website_markdown": "Main webpage about AI", "enrichment": {"search_results": {"query1": [{"title": "AI News 1", "snippet": "Snippet 1"}, {"title": "AI News 2", "snippet": "Snippet 2"}, {"title": "AI News 3", "snippet": "Snippet 3"}]}}}')]
    
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.get_llm_backend') as mock_llm_factory, \
         patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.random.sample') as mock_sample, \
         patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.random.randint') as mock_randint:
        
        # Mock random selection to return 2 results
        mock_randint.return_value = 2
        mock_sample.return_value = [{"title": "AI News 1", "snippet": "Snippet 1"}, {"title": "AI News 2", "snippet": "Snippet 2"}]
        
        mock_llm = Mock()
        
        # Mock website_to_metadata
        website_result = Mock()
        website_result.tags = ["artificial intelligence"]
        mock_llm.website_to_metadata.return_value = website_result
        
        # Mock enrichment_to_metadata
        enrichment_result = Mock()
        enrichment_result.tags = ["machine learning"]
        mock_llm.enrichment_to_metadata.return_value = enrichment_result
        
        # Mock combine_metadata_tags
        combine_result = Mock()
        combine_result.success = True
        combine_result.tags = ["artificial intelligence", "machine learning"]
        combine_result.vectors = {"artificial intelligence": {"vectors": [0.1]}}
        mock_llm.combine_metadata_tags.return_value = combine_result
        
        mock_llm_factory.return_value = mock_llm
        
        await bundle._generate_metadata()
        
        # Verify random.sample was called to select 2 results from 3 available
        mock_sample.assert_called_once()
        args, kwargs = mock_sample.call_args
        assert len(args[0]) == 3  # 3 results available
        assert args[1] == 2  # Selected 2 results


@pytest.mark.asyncio
async def test_generate_metadata_handles_llm_failure():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    bundle.input.data.lines = [(0, '{"website_markdown": "Main webpage about AI", "enrichment": null}')]
    bundle.input.metadata = None  # Clear existing metadata
    
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        
        # Mock combine_metadata_tags to return failure
        combine_result = Mock()
        combine_result.success = False
        mock_llm.combine_metadata_tags.return_value = combine_result
        
        mock_llm_factory.return_value = mock_llm
        
        await bundle._generate_metadata()
        
        # Verify metadata remains None on failure
        assert bundle.input.metadata is None


@pytest.mark.asyncio
async def test_generate_metadata_handles_no_result():
    bundle = DummyData.webpage_metadata_generation_task_bundle()
    bundle.input.data.lines = [(0, '{"website_markdown": "Main webpage about AI", "enrichment": null}')]
    bundle.input.metadata = None  # Clear existing metadata
    
    with patch('conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        
        # Mock combine_metadata_tags to return None
        mock_llm.combine_metadata_tags.return_value = None
        
        mock_llm_factory.return_value = mock_llm
        
        await bundle._generate_metadata()
        
        # Verify metadata remains None when no result
        assert bundle.input.metadata is None