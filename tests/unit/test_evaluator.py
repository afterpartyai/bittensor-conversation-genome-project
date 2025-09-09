import numpy as np
import pytest

from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.utils.Utils import Utils
from conversationgenome.validator.evaluator import Evaluator


class DummyUtils:
    @staticmethod
    def compare_arrays(arr1, arr2):
        # Returns dict with 'both' (intersection), 'unique_2' (arr2 - arr1)
        return {'both': list(set(arr1) & set(arr2)), 'unique_2': list(set(arr2) - set(arr1))}

    @staticmethod
    def empty(val):
        return not val

    @staticmethod
    def append_log(path, msg):
        pass

    @staticmethod
    def get(obj, key, default=None):
        return obj.get(key, default)

    @staticmethod
    def safe_value(val):
        val = Utils.safe_value(val)
        return val


class DummyConfig:
    @staticmethod
    def get(section, key):
        return None


class DummyBTLogging:
    @staticmethod
    def debug(msg):
        pass

    @staticmethod
    def error(msg):
        pass

    @staticmethod
    def info(msg):
        pass


class DummyBT:
    logging = DummyBTLogging()


@pytest.fixture(autouse=True)
def patch_evaluator(monkeypatch):
    monkeypatch.setattr("conversationgenome.validator.evaluator.Utils", DummyUtils)
    monkeypatch.setattr("conversationgenome.validator.evaluator.c", DummyConfig)
    monkeypatch.setattr("conversationgenome.validator.evaluator.bt", DummyBT)


def make_vector(dim, val):
    return np.full(dim, val, dtype=np.float32)


@pytest.mark.asyncio
async def test_calc_scores_basic_overlap():
    evaluator = Evaluator()
    evaluator.max_scored_tags = 10

    # Ground truth tags
    full_convo_tags = ["apple", "banana", "pear"]
    miner_tags = ["apple", "banana", "orange", "kiwi"]

    tag_vector_dict = {
        "apple": {"vectors": make_vector(5, 1.0)},
        "banana": {"vectors": make_vector(5, 2.0)},
        "orange": {"vectors": make_vector(5, 3.0)},
        "kiwi": {"vectors": make_vector(5, 4.0)},
    }

    # Dummy full conversation neighborhood vector
    full_conversation_neighborhood = make_vector(5, 2.0)

    miner_result = {"tags": miner_tags, "vectors": tag_vector_dict}
    full_convo_metadata = ConversationMetadata(tags=full_convo_tags, vectors={})

    scores, scores_both, scores_unique, diff = await evaluator.calc_scores(full_convo_metadata, full_conversation_neighborhood, miner_result)

    # 'apple' and 'banana' are both, 'orange' and 'kiwi' are unique
    assert len(scores) == 4
    assert len(scores_both) == 2
    assert len(scores_unique) == 2
    assert set(diff['both']) == {"apple", "banana"}
    assert set(diff['unique_2']) == {"orange", "kiwi"}


@pytest.mark.asyncio
async def test_given_no_miner_vector_then_scores_should_not_be_zero():
    evaluator = Evaluator()
    evaluator.max_scored_tags = 10

    full_convo_tags = ["apple", "banana"]
    miner_tags = ["apple", "banana", "pear"]

    tag_vector_dict = {
        "apple": {"vectors": make_vector(3, 1.0)},
        "banana": {"vectors": make_vector(3, 2.0)},
        "pear": {"vectors": make_vector(3, 3.0)},
    }
    full_conversation_neighborhood = make_vector(3, 1.0)

    miner_result = {"tags": miner_tags, "vectors": tag_vector_dict}
    full_convo_metadata = ConversationMetadata(tags=full_convo_tags, vectors={})

    scores, scores_both, scores_unique, diff = await evaluator.calc_scores(full_convo_metadata, full_conversation_neighborhood, miner_result)

    assert np.all(scores != 0)
    assert len(scores) == 3


@pytest.mark.asyncio
async def test_calc_scores_max_scored_tags_limit():
    evaluator = Evaluator()
    evaluator.max_scored_tags = 2

    full_convo_tags = ["a", "b", "c"]
    miner_tags = ["a", "b", "c", "d", "e"]

    tag_vector_dict = {tag: {"vectors": make_vector(2, 1.0)} for tag in miner_tags}
    full_conversation_neighborhood = make_vector(2, 1.0)

    miner_result = {"tags": miner_tags, "vectors": tag_vector_dict}
    full_convo_metadata = ConversationMetadata(tags=full_convo_tags, vectors={})

    scores, scores_both, scores_unique, diff = await evaluator.calc_scores(full_convo_metadata, full_conversation_neighborhood, miner_result)

    # Only first max_scored_tags tags should be scored
    assert len(scores) == evaluator.max_scored_tags + 1


@pytest.mark.asyncio
async def test_calc_scores_all_tags_irrelevant():
    evaluator = Evaluator()
    evaluator.max_scored_tags = 10

    full_convo_tags = ["apple", "banana"]
    miner_tags = ["pear", "kiwi"]

    tag_vector_dict = {
        "pear": {"vectors": make_vector(3, 1.0)},
        "kiwi": {"vectors": make_vector(3, 2.0)},
    }
    full_conversation_neighborhood = make_vector(3, 1.0)

    miner_result = {"tags": miner_tags, "vectors": tag_vector_dict}
    full_convo_metadata = ConversationMetadata(tags=full_convo_tags, vectors={})

    scores, scores_both, scores_unique, diff = await evaluator.calc_scores(full_convo_metadata, full_conversation_neighborhood, miner_result)

    # All tags are unique_2
    assert set(diff['both']) == set()
    assert set(diff['unique_2']) == set(miner_tags)
    assert len(scores_both) == 0
    assert len(scores_unique) == 2


@pytest.mark.asyncio
async def test_calc_scores_given_no_unique_tags_then_score_unique_is_an_empty_array():
    evaluator = Evaluator()
    evaluator.max_scored_tags = 10

    full_convo_tags = ["apple", "banana"]
    miner_tags = ["apple", "banana"]

    tag_vector_dict = {
        "apple": {"vectors": make_vector(3, 1.0)},
        "banana": {"vectors": make_vector(3, 2.0)},
    }

    full_conversation_neighborhood = make_vector(3, 1.0)

    miner_result = {"tags": miner_tags, "vectors": tag_vector_dict}
    full_convo_metadata = ConversationMetadata(tags=full_convo_tags, vectors={})

    results = await evaluator.calc_scores(full_convo_metadata, full_conversation_neighborhood, miner_result)

    scores, scores_both, scores_unique, diff = results

    assert len(scores_unique) == 0


@pytest.mark.asyncio
async def test_evaluate_basic_scores():
    evaluator = Evaluator()
    evaluator.min_tags = 2
    evaluator.max_scored_tags = 10

    full_convo_tags = ["apple", "banana", "pear"]
    full_convo_vectors = {
        "apple": {"vectors": make_vector(3, 1.0)},
        "banana": {"vectors": make_vector(3, 2.0)},
        "pear": {"vectors": make_vector(3, 3.0)},
    }
    full_convo_metadata = ConversationMetadata(tags=full_convo_tags, vectors=full_convo_vectors)

    class DummyAxon:
        uuid = "uuid-1"
        hotkey = "hk-1"

    # Valid miner response
    miner_result_1 = {
        "tags": ["apple", "banana", "orange"],
        "vectors": {
            "apple": {"vectors": make_vector(3, 1.0)},
            "banana": {"vectors": make_vector(3, 2.0)},
            "orange": {"vectors": make_vector(3, 3.0)},
        },
        "uid": "miner-1",
    }

    class MinerResponse1:
        axon = DummyAxon()
        cgp_output = [miner_result_1]

    # Invalid miner response (not enough tags)
    miner_result_2 = {
        "tags": ["apple"],
        "vectors": {
            "apple": {"vectors": make_vector(3, 1.0)},
        },
        "uid": "miner-2",
    }

    class MinerResponse2:
        axon = DummyAxon()
        cgp_output = [miner_result_2]

    # None miner response
    class MinerResponse3:
        axon = DummyAxon()
        cgp_output = None

    miner_responses = [MinerResponse1(), MinerResponse2(), MinerResponse3()]

    final_scores, rank_scores = await evaluator.evaluate(full_convo_metadata, miner_responses=miner_responses)

    assert len(final_scores) == 3
    assert len(rank_scores) == 3

    # First response should have nonzero score
    assert final_scores[0]['adjustedScore'] > 0
    assert final_scores[0]['final_miner_score'] > 0

    # Second and third responses should have zero scores
    assert final_scores[1]['adjustedScore'] == 0.0
    assert final_scores[1]['final_miner_score'] == 0.0
    assert final_scores[2]['adjustedScore'] == 0.0
    assert final_scores[2]['final_miner_score'] == 0.0


@pytest.mark.asyncio
async def test_evaluate_all_bad_responses():
    evaluator = Evaluator()
    evaluator.min_tags = 2

    full_convo_metadata = ConversationMetadata(tags=["apple", "banana"], vectors={})

    class DummyAxon:
        uuid = "uuid-x"
        hotkey = "hk-x"

    # Response is None
    class MinerResponseNone:
        axon = DummyAxon()
        cgp_output = None

    # Not enough tags
    miner_result = {"tags": ["apple"], "vectors": {"apple": {"vectors": make_vector(3, 1.0)}}, "uid": "miner-x"}

    class MinerResponseFewTags:
        axon = DummyAxon()
        cgp_output = [miner_result]

    miner_responses = [MinerResponseNone(), MinerResponseFewTags()]

    final_scores, rank_scores = await evaluator.evaluate(full_convo_metadata, miner_responses=miner_responses)

    assert len(final_scores) == 2
    assert all(score['adjustedScore'] == 0.0 for score in final_scores)
    assert all(score['final_miner_score'] == 0.0 for score in final_scores)
    assert np.all(rank_scores == 0.0)


@pytest.mark.asyncio
async def test_evaluate_final_scores_and_ranks_length_match():
    evaluator = Evaluator()
    evaluator.min_tags = 2

    full_convo_metadata = ConversationMetadata(tags=["apple", "banana"], vectors={})

    class DummyAxon:
        uuid = "uuid-z"
        hotkey = "hk-z"

    miner_result = {
        "tags": ["apple", "banana"],
        "vectors": {
            "apple": {"vectors": make_vector(3, 1.0)},
            "banana": {"vectors": make_vector(3, 2.0)},
        },
        "uid": "miner-z",
    }

    class MinerResponse:
        axon = DummyAxon()
        cgp_output = [miner_result]

    miner_responses = [MinerResponse(), MinerResponse()]

    final_scores, rank_scores = await evaluator.evaluate(full_convo_metadata, miner_responses=miner_responses)

    assert len(final_scores) == len(rank_scores)
    assert len(final_scores) == 2
    assert all(isinstance(score, dict) for score in final_scores)
    assert all(isinstance(rank, (float, np.floating)) for rank in rank_scores)


@pytest.mark.asyncio
async def test_evaluate_given_no_unique_tags_then_adjusted_score_is_a_valid_float():
    evaluator = Evaluator()
    evaluator.min_tags = 2

    full_convo_metadata = ConversationMetadata(tags=["apple", "banana"], vectors={})

    class DummyAxon:
        uuid = "uuid-z"
        hotkey = "hk-z"

    miner_result = {
        "tags": ["apple", "banana"],
        "vectors": {
            "apple": {"vectors": make_vector(3, 1.0)},
            "banana": {"vectors": make_vector(3, 2.0)},
        },
        "uid": "miner-z",
    }

    class MinerResponse:
        axon = DummyAxon()
        cgp_output = [miner_result]

    miner_responses = [MinerResponse(), MinerResponse()]

    final_scores, rank_scores = await evaluator.evaluate(full_convo_metadata, miner_responses=miner_responses)

    for i, score in enumerate(final_scores):
        for field in ["adjustedScore", "final_miner_score"]:
            v = score[field]
            assert isinstance(v, (float, np.floating)), f"{field}[{i}] has type {type(v)}: {v!r}"
            assert np.isfinite(v), f"{field}[{i}] is not finite (nan/inf): {v!r}"


@pytest.mark.asyncio
async def test_evaluate_handles_calc_scores_all_empty_arrays(monkeypatch):
    evaluator = Evaluator()
    evaluator.min_tags = 2

    # Patch calc_scores to always return empty arrays
    async def dummy_calc_scores(*args, **kwargs):
        return ([], [], [], {'both': [], 'unique_2': []})

    monkeypatch.setattr(evaluator, "calc_scores", dummy_calc_scores)

    class DummyAxon:
        uuid = "uuid-empty"
        hotkey = "hk-empty"

    miner_result = {
        "tags": ["apple", "banana"],
        "vectors": {},
        "uid": "miner-empty",
    }

    class MinerResponse:
        axon = DummyAxon()
        cgp_output = [miner_result]

    miner_responses = [MinerResponse()]

    full_convo_metadata = ConversationMetadata(tags=["apple", "banana"], vectors={})

    final_scores, rank_scores = await evaluator.evaluate(full_convo_metadata, miner_responses=miner_responses)

    assert len(final_scores) == 1
    assert len(rank_scores) == 1

    # With all empty arrays, adjustedScore and final_miner_score should be valid floats (likely 0.0 or nan, but not crash)
    for score in final_scores:
        for field in ["adjustedScore", "final_miner_score"]:
            v = score[field]
            assert isinstance(v, (float, np.floating)), f"{field} has type {type(v)}: {v!r}"
            assert np.isfinite(v) or np.isnan(v), f"{field} is not finite or nan: {v!r}"
