from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.task_bundle.ConversationTaggingTaskBundle import (
    ConversationInput,
)
from conversationgenome.task_bundle.ConversationTaggingTaskBundle import (
    ConversationInputData,
)
from tests.mocks.DummyData import DummyData


@pytest.fixture
def sample_input():
    return ConversationInput(
        input_type="conversation",
        guid="test-guid",
        data=ConversationInputData(
            participants=["Alice", "Bob"],
            lines=[(0, "Hello"), (1, "Hi"), (2, "How are you?"), (3, "Good, thanks!")],
            total=4,
        ),
        metadata=None,
    )


def test_trim_input_trims_lines(sample_input):
    sample_input.data.lines = [(i, f"Line {i}") for i in range(400)]
    sample_input.data.total = 400
    with patch("conversationgenome.task_bundle.ConversationTaggingTaskBundle.Utils._int", return_value=300):
        sample_input.trim_input()
    assert len(sample_input.data.lines) == 300
    assert sample_input.data.total == 300


def test_is_ready_false_when_no_metadata_or_windows(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    assert not bundle.is_ready()


def test_is_ready_true_when_metadata_and_windows(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.metadata = ConversationMetadata(participantProfiles=["Alice", "Bob"], tags=[], vectors={})
    bundle.input.data.indexed_windows = [(0, [(0, "Hello"), (1, "Hi")])]
    assert bundle.is_ready()


def test_split_conversation_in_windows_sets_indexed_windows(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    with patch("conversationgenome.task_bundle.ConversationTaggingTaskBundle.c.get", side_effect=lambda *a, **k: 2):
        with patch(
            "conversationgenome.task_bundle.ConversationTaggingTaskBundle.Utils.split_overlap_array",
            return_value=[[(0, "Hello"), (1, "Hi")], [(2, "How are you?"), (3, "Good, thanks!")]],
        ):
            bundle._split_conversation_in_windows()
    assert isinstance(bundle.input.data.indexed_windows, list)
    assert len(bundle.input.data.indexed_windows) == 2


def test_enforce_minimum_convo_windows_removes_windows_if_not_enough(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.data.min_convo_windows = 2
    bundle.input.data.indexed_windows = [(0, [(0, "Hello")])]
    with patch("conversationgenome.task_bundle.ConversationTaggingTaskBundle.bt.logging.info"):
        bundle._enforce_minimum_convo_windows()
    assert bundle.input.data.indexed_windows == []


@pytest.mark.asyncio
async def test_format_results_validates_and_embeds_tags(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    miner_result = {"tags": ["tag1", "tag2"]}
    with patch("conversationgenome.utils.Utils.Utils.validate_tag_set", AsyncMock(return_value=["tag1", "tag2"])):
        with patch.object(bundle, "_get_vector_embeddings_set", AsyncMock(return_value={"tag1": [0.1], "tag2": [0.2]})):
            result = await bundle.format_results(miner_result)
    assert result["original_tags"] == ["tag1", "tag2"]
    assert result["tags"] == ["tag1", "tag2"]
    assert result["vectors"] == {"tag1": [0.1], "tag2": [0.2]}


def test_generate_result_logs_counts_tags_and_vectors(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    miner_result = {"tags": ["tag1", "tag2"], "vectors": {"tag1": [0.1]}, "original_tags": ["tag1", "tag2", "tag3"]}
    log = bundle.generate_result_logs(miner_result)
    assert "tags: 2" in log
    assert "vector count: 1" in log
    assert "original tags: 3" in log


@pytest.mark.asyncio
async def test_evaluate_calls_ground_truth_scoring(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    with patch("conversationgenome.task_bundle.ConversationTaggingTaskBundle.GroundTruthTagSimilarityScoringMechanism") as mock_mech:
        mock_eval = AsyncMock(return_value="score")
        mock_mech.return_value.evaluate = mock_eval
        result = await bundle.evaluate(["response"])
    assert result == "score"
