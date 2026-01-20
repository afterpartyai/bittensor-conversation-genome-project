from unittest.mock import AsyncMock, Mock, patch, mock_open
import json
import pytest
from conversationgenome.task_bundle.NamedEntitiesExtractionTaskBundle import NamedEntitiesExtractionTaskBundle
from tests.mocks.DummyData import DummyData


def test_get_webpage_text_returns_text_content():
    bundle = NamedEntitiesExtractionTaskBundle()
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.text = "<html><body><script>alert('test')</script><p>Line 1</p><p>Line 2</p></body></html>"
        mock_get.return_value = mock_response
        
        result = bundle.get_webpage_text("http://example.com")
        assert "Line 1" in result
        assert "Line 2" in result
        assert "alert" not in result  # Script content should be removed


def test_get_webpage_text_handles_request_errors():
    bundle = NamedEntitiesExtractionTaskBundle()
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("Connection error")
        
        result = bundle.get_webpage_text("http://example.com")
        assert result == ""


def test_is_ready_false_when_no_metadata():
    bundle = DummyData.named_entities_extraction_task_bundle()
    bundle.input.metadata = None
    assert not bundle.is_ready()


def test_is_ready_false_when_no_lines():
    bundle = DummyData.named_entities_extraction_task_bundle()
    bundle.input.data.lines = None
    assert not bundle.is_ready()


def test_is_ready_true_when_metadata_and_lines():
    bundle = DummyData.setup_named_entities_extraction_task_bundle()
    assert bundle.is_ready()


@pytest.mark.asyncio
async def test_setup_generates_metadata():
    bundle = DummyData.named_entities_extraction_task_bundle()
    with patch.object(bundle, '_generate_metadata') as mock_generate:
        await bundle.setup()
        mock_generate.assert_called_once()


def test_to_mining_tasks_creates_tasks():
    bundle = DummyData.setup_named_entities_extraction_task_bundle()
    tasks = bundle.to_mining_tasks(3)
    assert len(tasks) == 3
    for task in tasks:
        assert task.type == "named_entities_extraction"
        assert task.bundle_guid == bundle.guid


@pytest.mark.asyncio
async def test_format_results_validates_and_embeds_tags():
    bundle = DummyData.setup_named_entities_extraction_task_bundle()
    miner_result = {"tags": ["entity1", "entity2"]}
    with patch('conversationgenome.llm.llm_factory.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.validate_named_entities_tag_set.return_value = ["entity1", "entity2"]
        mock_llm_factory.return_value = mock_llm
        with patch.object(bundle, '_get_vector_embeddings_set', AsyncMock(return_value={"entity1": [0.1], "entity2": [0.2]})):
            result = await bundle.format_results(miner_result)
    assert result["original_tags"] == ["entity1", "entity2"]
    assert set(result["tags"]) == {"entity1", "entity2"}
    assert result["vectors"] == {"entity1": [0.1], "entity2": [0.2]}


def test_generate_result_logs_counts_tags_and_vectors():
    bundle = DummyData.setup_named_entities_extraction_task_bundle()
    miner_result = {"tags": ["entity1", "entity2"], "vectors": {"entity1": [0.1]}, "original_tags": ["entity1", "entity2", "entity3"]}
    log = bundle.generate_result_logs(miner_result)
    assert "tags: 2" in log
    assert "vector count: 1" in log
    assert "original tags: 3" in log


@pytest.mark.asyncio
async def test_evaluate_calls_no_penalty_scoring():
    bundle = DummyData.setup_named_entities_extraction_task_bundle()
    with patch('conversationgenome.task_bundle.NamedEntitiesExtractionTaskBundle.NoPenaltyGroundTruthTagSimilarityScoringMechanism') as mock_mech:
        mock_eval = AsyncMock(return_value="score")
        mock_mech.return_value.evaluate = mock_eval
        result = await bundle.evaluate(["response"])
    assert result == "score"


def test_mask_task_for_miner_sets_window_idx():
    bundle = DummyData.setup_named_entities_extraction_task_bundle()
    task = Mock()
    task.input.data.window_idx = 0
    masked = bundle.mask_task_for_miner(task)
    assert masked.input.data.window_idx == -1


@pytest.mark.asyncio
async def test_generate_metadata_calls_llm():
    bundle = DummyData.named_entities_extraction_task_bundle()
    # Prepare proper JSON structure with transcript_text and enrichment data
    transcript_json = {
        "transcript_text": "Mayor Adams proposed an amendment to Local Law 55.",
        "enrichment": {
            "search_results": {
                "query1": [{"url": "http://example.com/1"}]
            }
        }
    }
    bundle.input.data.lines = [(0, json.dumps(transcript_json))]
    
    with patch('conversationgenome.task_bundle.NamedEntitiesExtractionTaskBundle.get_llm_backend') as mock_llm_factory, \
         patch.object(NamedEntitiesExtractionTaskBundle, 'get_webpage_text', return_value="web content"):
        mock_llm = Mock()
        mock_result_transcript = Mock()
        mock_result_transcript.tags = ["Mayor Adams", "Local Law 55"]
        mock_result_web = Mock()
        mock_result_web.tags = ["Downtown Project"]
        combined_result = Mock()
        combined_result.tags = ["Mayor Adams", "Local Law 55", "Downtown Project"]
        combined_result.vectors = {
            "Mayor Adams": {"vectors": [0.1]},
            "Local Law 55": {"vectors": [0.2]},
            "Downtown Project": {"vectors": [0.3]}
        }
        
        mock_llm.raw_transcript_to_named_entities.return_value = mock_result_transcript
        mock_llm.raw_webpage_to_named_entities.return_value = mock_result_web
        mock_llm.combine_named_entities.return_value = combined_result
        mock_llm_factory.return_value = mock_llm
        
        bundle._generate_metadata()
        
        assert bundle.input.metadata.tags == ["Mayor Adams", "Local Law 55", "Downtown Project"]
        assert "Mayor Adams" in bundle.input.metadata.vectors


@pytest.mark.asyncio
async def test_get_vector_embeddings_set_calls_llm():
    bundle = DummyData.setup_named_entities_extraction_task_bundle()
    mock_llm = Mock()
    mock_llm.get_vector_embeddings_set.return_value = {"tag": [0.1]}
    result = await bundle._get_vector_embeddings_set(llml=mock_llm, tags=["tag"])
    assert result == {"tag": [0.1]}