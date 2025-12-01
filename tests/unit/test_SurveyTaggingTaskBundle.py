from unittest.mock import AsyncMock, Mock
from unittest.mock import patch

import pytest

from conversationgenome.task_bundle.SurveyTaggingTaskBundle import SurveyMetadata
from tests.mocks.DummyData import DummyData


def test_is_ready_false_when_no_input():
    bundle = DummyData.survey_tagging_task_bundle()
    assert not bundle.is_ready()

def test_is_ready_true_when_metadata():
    bundle = DummyData.survey_tagging_task_bundle()
    bundle.input.metadata = SurveyMetadata(
        survey_question='Valid question',
        comment='Valid comment',
        possible_choices=['a', 'b', 'c'],
        selected_choices=['a'],
        tags=[],
        vectors={}
    )
    assert bundle.is_ready()

@pytest.mark.asyncio
async def test_format_results_validates_and_embeds_tags():
    bundle = DummyData.survey_tagging_task_bundle()
    miner_result = {"tags": ["tag1", "tag2"]}
    with patch("conversationgenome.llm.LlmLib.LlmLib.validate_tag_set", Mock(return_value=["tag1", "tag2"])):
        with patch("conversationgenome.llm.LlmLib.LlmLib.get_vector_embeddings_set", Mock(return_value={"tag1": [0.1], "tag2": [0.2]})):
            result = await bundle.format_results(miner_result)
    assert result["original_tags"] == ["tag1", "tag2"]
    assert result["tags"] == ["tag1", "tag2"]
    assert result["vectors"] == {"tag1": [0.1], "tag2": [0.2]}


def test_generate_result_logs_counts_tags_and_vectors():
    bundle = DummyData.survey_tagging_task_bundle()
    miner_result = {"tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1]}, "original_tags": ["tag1", "tag2", "tag3"]}
    log = bundle.generate_result_logs(miner_result)
    assert "tags: 2" in log
    assert "vector count: 1" in log
    assert "original tags: 3" in log


@pytest.mark.asyncio
async def test_evaluate_calls_ground_truth_scoring():
    bundle = DummyData.survey_tagging_task_bundle()
    with patch("conversationgenome.task_bundle.SurveyTaggingTaskBundle.GroundTruthTagSimilarityScoringMechanism") as mock_mech:
        mock_eval = AsyncMock(return_value="score")
        mock_mech.return_value.evaluate = mock_eval
        result = await bundle.evaluate(["response"])
    assert result == "score"
