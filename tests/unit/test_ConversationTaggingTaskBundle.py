from unittest.mock import AsyncMock, Mock
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


def test_is_ready_false_when_quality_missing(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.quality_score = None
    assert not bundle.is_ready()


def test_is_ready_false_when_quality_below_threshold(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.quality_score = 5  # Assuming threshold is 6
    assert not bundle.is_ready()


def test_is_ready_true_when_metadata_and_windows(sample_input):
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.metadata = ConversationMetadata(participantProfiles=["Alice", "Bob"], tags=[], vectors={})
    bundle.input.data.indexed_windows = [(0, [(0, "Hello"), (1, "Hi")])]
    assert bundle.is_ready()


def test_is_ready_true_for_user_request_without_quality():
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.is_user_request = True
    bundle.input.quality_score = None
    bundle.input.metadata = ConversationMetadata(participantProfiles=["Alice", "Bob"], tags=[], vectors={})
    bundle.input.data.indexed_windows = [(0, [(0, "Hello"), (1, "Hi")])]
    assert bundle.is_ready()


def test_is_ready_true_for_user_request_below_quality_threshold():
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.is_user_request = True
    bundle.input.quality_score = 1
    bundle.input.metadata = ConversationMetadata(participantProfiles=["Alice", "Bob"], tags=[], vectors={})
    bundle.input.data.indexed_windows = [(0, [(0, "Hello"), (1, "Hi")])]
    assert bundle.is_ready()


def test_is_ready_false_for_user_request_missing_metadata():
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.is_user_request = True
    bundle.input.metadata = None
    bundle.input.data.indexed_windows = [(0, [(0, "Hello"), (1, "Hi")])]
    assert not bundle.is_ready()


@pytest.mark.asyncio
async def test_setup_user_request_skips_quality_and_min_windows():
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.is_user_request = True
    with patch.object(bundle, "_split_conversation_in_windows") as mock_split, \
         patch.object(bundle, "_enforce_minimum_convo_windows") as mock_enforce, \
         patch.object(bundle, "_get_conversation_quality", AsyncMock()) as mock_quality, \
         patch.object(bundle, "_generate_metadata", AsyncMock()) as mock_generate:
        await bundle.setup()
        mock_split.assert_called_once()
        mock_enforce.assert_not_called()
        mock_quality.assert_not_called()
        mock_generate.assert_called_once()


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
    with patch("conversationgenome.llm.LlmLib.LlmLib.validate_tag_set", Mock(return_value=["tag1", "tag2"])):
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


# ---------- Single window per conversation ----------

import random as _random_module

BUNDLE_MODULE = "conversationgenome.task_bundle.ConversationTaggingTaskBundle"


def _config(overrides=None):
    values = {
        ("convo_window", "min_lines"): 2,
        ("convo_window", "max_lines"): 10,
        ("convo_window", "overlap_lines"): 2,
        ("convo_window", "min_convo_windows_floor"): 3,
    }
    values.update(overrides or {})
    return lambda section, key, default=None, *a, **k: values.get((section, key), default)


@pytest.fixture
def seeded_random(monkeypatch):
    # conftest makes random helpers deterministic globally; use a real seeded RNG here.
    rng = _random_module.Random(1234)
    monkeypatch.setattr(_random_module, "choice", rng.choice)
    return rng


def _bundle_with_lines(num_lines, enrichment_lines=None):
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.data.lines = [(i % 2, f"unique line {i}") for i in range(num_lines)]
    bundle.input.data.total = num_lines
    bundle.input.data.enrichment_lines = enrichment_lines
    with patch(f"{BUNDLE_MODULE}.c.get", side_effect=_config()):
        bundle._split_conversation_in_windows()
    return bundle


@pytest.mark.parametrize("num_lines", [34, 62, 300])
@pytest.mark.parametrize("n", [1, 5])
def test_all_tasks_carry_the_same_single_window(seeded_random, num_lines, n):
    bundle = _bundle_with_lines(num_lines)
    tasks = bundle.to_mining_tasks(number_of_tasks_per_bundle=n)
    assert len(tasks) == n
    assert len({t.input.data.window_idx for t in tasks}) == 1
    assert all(t.input.data.window == tasks[0].input.data.window for t in tasks)
    assert len({t.guid for t in tasks}) == n


def test_user_request_also_gets_a_single_window(seeded_random):
    bundle = _bundle_with_lines(300)
    bundle.is_user_request = True
    tasks = bundle.to_mining_tasks(number_of_tasks_per_bundle=5)
    assert len({t.input.data.window_idx for t in tasks}) == 1


def test_selection_covers_all_window_positions(seeded_random):
    bundle = _bundle_with_lines(160)  # 20 windows
    picked = set()
    for _ in range(500):
        picked.add(bundle.to_mining_tasks(number_of_tasks_per_bundle=1)[0].input.data.window_idx)
    assert picked == set(range(len(bundle.input.data.indexed_windows)))


def test_no_windows_yields_no_tasks():
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.data.indexed_windows = []
    assert bundle.to_mining_tasks(number_of_tasks_per_bundle=5) == []


def test_all_tasks_carry_full_enrichment(seeded_random):
    enrichment = [(i, f"snippet {i}") for i in range(7)]
    bundle = _bundle_with_lines(300, enrichment_lines=enrichment)
    masked = [bundle.mask_task_for_miner(t) for t in bundle.to_mining_tasks(number_of_tasks_per_bundle=5)]
    payloads = [m.model_dump()["input"]["data"] for m in masked]
    assert all(p == payloads[0] for p in payloads), "every miner must receive the exact same challenge"
    assert [tuple(e) for e in payloads[0]["enrichment_lines"]] == enrichment


def test_no_enrichment_leaves_tasks_without_enrichment(seeded_random):
    bundle = _bundle_with_lines(300, enrichment_lines=None)
    assert all(t.input.data.enrichment_lines is None for t in bundle.to_mining_tasks(number_of_tasks_per_bundle=5))


@pytest.mark.parametrize(
    "num_windows,api_min,floor,expect_kept",
    [
        (3, 1, 3, False),  # validator floor applies even though API says 1
        (4, 1, 3, True),
        (4, 5, 3, False),  # API can raise the minimum
        (6, 5, 3, True),
        (2, 0, 1, True),   # floor is configurable
    ],
)
def test_enforce_minimum_convo_windows_uses_validator_floor(num_windows, api_min, floor, expect_kept):
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.data.min_convo_windows = api_min
    bundle.input.data.indexed_windows = [(i, [(0, f"l{i}")]) for i in range(num_windows)]
    with patch(f"{BUNDLE_MODULE}.c.get", side_effect=_config({("convo_window", "min_convo_windows_floor"): floor})):
        bundle._enforce_minimum_convo_windows()
    assert (len(bundle.input.data.indexed_windows) > 0) == expect_kept


@pytest.mark.asyncio
async def test_setup_skips_llm_calls_when_too_few_windows():
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.data.lines = [(i % 2, f"line {i}") for i in range(15)]  # 2 windows, below floor
    with patch.object(bundle, "_get_conversation_quality", AsyncMock()) as mock_quality, \
         patch.object(bundle, "_generate_metadata", AsyncMock()) as mock_generate:
        await bundle.setup()
    mock_quality.assert_not_called()
    mock_generate.assert_not_called()
    assert not bundle.is_ready()


@pytest.mark.asyncio
async def test_setup_runs_quality_check_when_enough_windows():
    bundle = DummyData.conversation_tagging_task_bundle()
    bundle.input.data.lines = [(i % 2, f"line {i}") for i in range(60)]
    with patch.object(bundle, "_get_conversation_quality", AsyncMock()) as mock_quality, \
         patch.object(bundle, "_generate_metadata", AsyncMock()):
        await bundle.setup()
    mock_quality.assert_called_once()
