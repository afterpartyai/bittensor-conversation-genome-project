from unittest.mock import AsyncMock, Mock, patch, mock_open
import pytest
from conversationgenome.task_bundle.NamedEntitiesExtractionTaskBundle import NamedEntitiesExtractionTaskBundle
from tests.mocks.DummyData import DummyData


def test_init_loads_transcript_and_parses():
    with patch.object(NamedEntitiesExtractionTaskBundle, '_get_random_transcript') as mock_get_transcript, \
         patch.object(NamedEntitiesExtractionTaskBundle, '_load_transcript') as mock_load, \
         patch.object(NamedEntitiesExtractionTaskBundle, '_parse_raw_transcript') as mock_parse:
        
        mock_get_transcript.return_value = Mock(transcript_link="http://example.com")
        mock_load.return_value = b"<html><body>Transcript text</body></html>"
        mock_parse.return_value = [(0, "Line 1"), (1, "Line 2")]
        
        bundle = NamedEntitiesExtractionTaskBundle()
        
        assert bundle.input.input_type == "document"
        assert bundle.input.data.lines == [(0, "Line 1"), (1, "Line 2")]
        assert bundle.input.data.total == 41  # len of bytes


def test_parse_raw_transcript_removes_scripts_and_splits_lines():
    bundle = NamedEntitiesExtractionTaskBundle()
    raw_html = "<html><body><script>alert('test')</script><p>Line 1</p><p>Line 2</p></body></html>"
    result = bundle._parse_raw_transcript(raw_html)
    expected = [[0, "Line 1Line 2"]]
    assert result == expected


def test_load_transcript_makes_request():
    bundle = NamedEntitiesExtractionTaskBundle()
    with patch('requests.get') as mock_get:
        mock_get.return_value.content = b"transcript content"
        result = bundle._load_transcript("http://example.com")
        assert result == b"transcript content"
        mock_get.assert_called_once_with("http://example.com")


def test_get_random_transcript_loads_from_files():
    bundle = NamedEntitiesExtractionTaskBundle()
    with patch('builtins.open', mock_open(read_data='[{"name": "test", "timestamp": 123, "transcript_link": "url"}]')) as mock_file, \
         patch('random.choice') as mock_choice:
        
        mock_choice.return_value = {"name": "test", "timestamp": 123, "transcript_link": "url"}
        
        result = bundle._get_random_transcript()
        assert result.name == "test"
        assert result.transcript_link == "url"


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
    bundle.input = Mock()
    bundle.input.to_raw_text.return_value = "raw text"
    with patch('conversationgenome.task_bundle.NamedEntitiesExtractionTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_result = Mock()
        mock_result.tags = ["tag1"]
        mock_result.vectors = {"tag1": {"vectors": [0.1]}}
        mock_llm.raw_transcript_to_named_entities.return_value = mock_result
        mock_llm_factory.return_value = mock_llm
        
        bundle._generate_metadata()
        
        assert bundle.input.metadata.tags == ["tag1"]
        assert bundle.input.metadata.vectors == {"tag1": {"vectors": [0.1]}}


@pytest.mark.asyncio
async def test_get_vector_embeddings_set_calls_llm():
    bundle = DummyData.setup_named_entities_extraction_task_bundle()
    mock_llm = Mock()
    mock_llm.get_vector_embeddings_set.return_value = {"tag": [0.1]}
    result = await bundle._get_vector_embeddings_set(llml=mock_llm, tags=["tag"])
    assert result == {"tag": [0.1]}