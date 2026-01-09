from unittest.mock import AsyncMock, Mock, patch
import pytest
from conversationgenome.task_bundle.SurveyTaggingTaskBundle import SurveyMetadata, SurveyTaggingTaskBundle
from tests.mocks.DummyData import DummyData


def test_is_ready_false_when_no_input():
    bundle = DummyData.survey_tagging_task_bundle()
    bundle.input = None
    assert not bundle.is_ready()


def test_is_ready_false_when_no_metadata():
    bundle = DummyData.survey_tagging_task_bundle()
    bundle.input.metadata = None
    assert not bundle.is_ready()


def test_is_ready_true_when_metadata():
    bundle = DummyData.setup_survey_tagging_task_bundle()
    assert bundle.is_ready()


@pytest.mark.asyncio
async def test_setup_calls_generate_metadata():
    bundle = DummyData.survey_tagging_task_bundle()
    with patch.object(bundle, '_generate_metadata') as mock_generate:
        await bundle.setup()
        mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_generate_metadata_parses_json_and_sets_metadata():
    bundle = DummyData.survey_tagging_task_bundle()
    with patch('conversationgenome.task_bundle.SurveyTaggingTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.get_vector_embeddings_set.return_value = {"tag1": {"vectors": [0.1]}}
        mock_llm_factory.return_value = mock_llm
        
        await bundle._generate_metadata()
        
        assert bundle.input.metadata.survey_question == "What did you like most about our new aCRM software? (Select all that apply)"
        assert bundle.input.metadata.comment == "The user interface is incredibly clean and intuitive, which makes training new team members a breeze. Also, the integration with our existing email client was seamless and saved us a lot of time."
        assert bundle.input.metadata.selected_choices == ["Easy to use / Intuitive UI", "Smooth Third-Party Integrations"]
        assert bundle.input.metadata.tags == ["Easy to use / Intuitive UI", "Smooth Third-Party Integrations"]


def test_to_mining_tasks_creates_correct_number_of_tasks():
    bundle = DummyData.setup_survey_tagging_task_bundle()
    tasks = bundle.to_mining_tasks(3)
    assert len(tasks) == 3
    for task in tasks:
        assert task.type == "survey_tagging"
        assert task.bundle_guid == bundle.guid
        assert task.input.input_type == "survey"


def test_generate_task_creates_valid_task():
    bundle = DummyData.setup_survey_tagging_task_bundle()
    task = bundle._generate_task()
    assert task.type == "survey_tagging"
    assert task.bundle_guid == bundle.guid
    assert task.input.data.survey_question == bundle.input.metadata.survey_question
    assert task.input.data.comment == bundle.input.metadata.comment


@pytest.mark.asyncio
async def test_format_results_validates_and_embeds_tags():
    bundle = DummyData.setup_survey_tagging_task_bundle()
    miner_result = {"tags": ["tag1", "tag2"]}
    with patch('conversationgenome.task_bundle.SurveyTaggingTaskBundle.get_llm_backend') as mock_llm_factory:
        mock_llm = Mock()
        mock_llm.validate_tag_set.return_value = ["tag1", "tag2"]
        mock_llm.get_vector_embeddings_set.return_value = {"tag1": [0.1], "tag2": [0.2]}
        mock_llm_factory.return_value = mock_llm
        result = await bundle.format_results(miner_result)
    assert result["original_tags"] == ["tag1", "tag2"]
    assert result["tags"] == ["tag1", "tag2"]
    assert result["vectors"] == {"tag1": [0.1], "tag2": [0.2]}


def test_generate_result_logs_counts_tags_and_vectors():
    bundle = DummyData.setup_survey_tagging_task_bundle()
    miner_result = {"tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1]}, "original_tags": ["tag1", "tag2", "tag3"]}
    log = bundle.generate_result_logs(miner_result)
    assert "tags: 2" in log
    assert "vector count: 1" in log
    assert "original tags: 3" in log


@pytest.mark.asyncio
async def test_evaluate_calls_ground_truth_scoring():
    bundle = DummyData.setup_survey_tagging_task_bundle()
    with patch('conversationgenome.task_bundle.SurveyTaggingTaskBundle.GroundTruthTagSimilarityScoringMechanism') as mock_mech:
        mock_eval = AsyncMock(return_value="score")
        mock_mech.return_value.evaluate = mock_eval
        result = await bundle.evaluate(["response"])
    assert result == "score"


@pytest.mark.asyncio
async def test_evaluate_sets_min_tags_to_1():
    bundle = DummyData.setup_survey_tagging_task_bundle()
    with patch('conversationgenome.task_bundle.SurveyTaggingTaskBundle.GroundTruthTagSimilarityScoringMechanism') as mock_mech:
        mock_eval = AsyncMock(return_value="score")
        mock_evaluator_instance = Mock()
        mock_evaluator_instance.evaluate = mock_eval
        mock_mech.return_value = mock_evaluator_instance
        
        await bundle.evaluate(["response"])
        
        assert mock_evaluator_instance.min_tags == 1
