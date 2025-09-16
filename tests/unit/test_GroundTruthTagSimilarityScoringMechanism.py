import numpy as np
import pytest

from conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism import GroundTruthTagSimilarityScoringMechanism


class DummyAxon:
    def __init__(self, uuid, hotkey):
        self.uuid = uuid
        self.hotkey = hotkey


class DummyResponse:
    def __init__(self, cgp_output=None, axon=None):
        self.cgp_output = cgp_output
        self.axon = axon


class DummyMetadata:
    def __init__(self, tags, vectors):
        self.tags = tags
        self.vectors = vectors


class DummyInput:
    def __init__(self, metadata):
        self.metadata = metadata


class DummyTaskBundle:
    def __init__(self, metadata):
        self.input = DummyInput(metadata)


@pytest.mark.asyncio
async def test_evaluate_with_valid_responses(monkeypatch):
    # Setup dummy metadata and vectors
    tags = ['tag1', 'tag2', 'tag3', 'tag4']
    vectors = {
        'tag1': {'vectors': np.array([1.0, 0.0, 0.0])},
        'tag2': {'vectors': np.array([0.0, 1.0, 0.0])},
        'tag3': {'vectors': np.array([0.0, 0.0, 1.0])},
        'tag4': {'vectors': np.array([1.0, 1.0, 1.0])},
    }
    metadata = DummyMetadata(tags, vectors)
    task_bundle = DummyTaskBundle(metadata)

    # Patch Utils.safe_value and Utils.compare_arrays
    monkeypatch.setattr("conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.Utils.safe_value", lambda x: x)
    monkeypatch.setattr(
        "conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.Utils.compare_arrays",
        lambda a, b: {'both': list(set(a) & set(b)), 'unique_2': list(set(b) - set(a))},
    )

    # Patch logging
    class DummyLogging:
        @staticmethod
        def info(*args, **kwargs):
            pass

        @staticmethod
        def debug(*args, **kwargs):
            pass

        @staticmethod
        def error(*args, **kwargs):
            pass

    monkeypatch.setattr("conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.bt.logging", DummyLogging)

    # Create miner responses
    miner_result = {
        'tags': ['tag1', 'tag2', 'tag3'],
        'vectors': {
            'tag1': {'vectors': np.array([1.0, 0.0, 0.0])},
            'tag2': {'vectors': np.array([0.0, 1.0, 0.0])},
            'tag3': {'vectors': np.array([0.0, 0.0, 1.0])},
        },
    }
    axon = DummyAxon('uuid-1', 'hk-1')
    response = DummyResponse([miner_result], axon)
    responses = [response]

    # Patch _calculate_penalty to just return the score as an awaitable
    async def dummy_penalty(self, score, *args, **kwargs):
        return score

    monkeypatch.setattr(GroundTruthTagSimilarityScoringMechanism, "_calculate_penalty", dummy_penalty)

    scoring_mechanism = GroundTruthTagSimilarityScoringMechanism()
    final_scores, rank_scores = await scoring_mechanism.evaluate(task_bundle, miner_responses=responses)

    assert isinstance(final_scores, list)
    assert isinstance(rank_scores, np.ndarray)
    assert final_scores[0]['uuid'] == 'uuid-1'
    assert final_scores[0]['hotkey'] == 'hk-1'
    assert final_scores[0]['final_miner_score'] > 0


@pytest.mark.asyncio
async def test_evaluate_with_empty_miner_response(monkeypatch):
    tags = ['tag1', 'tag2', 'tag3']
    vectors = {
        'tag1': {'vectors': np.array([1.0, 0.0, 0.0])},
        'tag2': {'vectors': np.array([0.0, 1.0, 0.0])},
        'tag3': {'vectors': np.array([0.0, 0.0, 1.0])},
    }
    metadata = DummyMetadata(tags, vectors)
    task_bundle = DummyTaskBundle(metadata)

    monkeypatch.setattr("conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.Utils.safe_value", lambda x: x)
    monkeypatch.setattr(
        "conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.Utils.compare_arrays",
        lambda a, b: {'both': list(set(a) & set(b)), 'unique_2': list(set(b) - set(a))},
    )

    class DummyLogging:
        @staticmethod
        def info(*args, **kwargs):
            pass

        @staticmethod
        def debug(*args, **kwargs):
            pass

        @staticmethod
        def error(*args, **kwargs):
            pass

    monkeypatch.setattr("conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.bt.logging", DummyLogging)

    axon = DummyAxon('uuid-2', 'hk-2')
    response = DummyResponse(None, axon)
    responses = [response]

    scoring_mechanism = GroundTruthTagSimilarityScoringMechanism()
    final_scores, rank_scores = await scoring_mechanism.evaluate(task_bundle, miner_responses=responses)

    assert final_scores[0]['uuid'] == 'uuid-2'
    assert final_scores[0]['hotkey'] == 'hk-2'
    assert final_scores[0]['final_miner_score'] == 0.0


@pytest.mark.asyncio
async def test_evaluate_with_insufficient_tags(monkeypatch):
    tags = ['tag1', 'tag2', 'tag3']
    vectors = {
        'tag1': {'vectors': np.array([1.0, 0.0, 0.0])},
        'tag2': {'vectors': np.array([0.0, 1.0, 0.0])},
        'tag3': {'vectors': np.array([0.0, 0.0, 1.0])},
    }
    metadata = DummyMetadata(tags, vectors)
    task_bundle = DummyTaskBundle(metadata)

    # Patch dependencies locally
    monkeypatch.setattr("conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.Utils.safe_value", lambda x: x, raising=True)
    monkeypatch.setattr(
        "conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.Utils.compare_arrays",
        lambda a, b: {'both': list(set(a) & set(b)), 'unique_2': list(set(b) - set(a))},
        raising=True,
    )

    class DummyLogging:
        @staticmethod
        def info(*args, **kwargs):
            pass

        @staticmethod
        def debug(*args, **kwargs):
            pass

        @staticmethod
        def error(*args, **kwargs):
            pass

    monkeypatch.setattr("conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.bt.logging", DummyLogging, raising=True)

    # Force min_tags to 3 for this test
    old_min_tags = GroundTruthTagSimilarityScoringMechanism.min_tags
    GroundTruthTagSimilarityScoringMechanism.min_tags = 3

    try:
        # Only 2 tags, less than min_tags (which is 3)
        miner_result = {
            'tags': ['tag1', 'tag2'],
            'vectors': {
                'tag1': {'vectors': np.array([1.0, 0.0, 0.0])},
                'tag2': {'vectors': np.array([0.0, 1.0, 0.0])},
            },
        }
        axon = DummyAxon('uuid-3', 'hk-3')
        response = DummyResponse([miner_result], axon)
        responses = [response]

        scoring_mechanism = GroundTruthTagSimilarityScoringMechanism()
        final_scores, rank_scores = await scoring_mechanism.evaluate(task_bundle, miner_responses=responses)

        assert final_scores[0]['uuid'] == 'uuid-3'
        assert final_scores[0]['hotkey'] == 'hk-3'
        assert final_scores[0]['final_miner_score'] == 0.0
    finally:
        GroundTruthTagSimilarityScoringMechanism.min_tags = old_min_tags


@pytest.mark.asyncio
async def test_evaluate_final_scores_length_mismatch(monkeypatch):
    tags = ['tag1', 'tag2', 'tag3']
    vectors = {
        'tag1': {'vectors': np.array([1.0, 0.0, 0.0])},
        'tag2': {'vectors': np.array([0.0, 1.0, 0.0])},
        'tag3': {'vectors': np.array([0.0, 0.0, 1.0])},
    }
    metadata = DummyMetadata(tags, vectors)
    task_bundle = DummyTaskBundle(metadata)

    monkeypatch.setattr("conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.Utils.safe_value", lambda x: x)
    monkeypatch.setattr(
        "conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.Utils.compare_arrays",
        lambda a, b: {'both': list(set(a) & set(b)), 'unique_2': list(set(b) - set(a))},
    )

    class DummyLogging:
        @staticmethod
        def info(*args, **kwargs):
            pass

        @staticmethod
        def debug(*args, **kwargs):
            pass

        @staticmethod
        def error(*args, **kwargs):
            pass

    monkeypatch.setattr("conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism.bt.logging", DummyLogging)

    # Patch _calculate_penalty to just return the score as an awaitable
    async def dummy_penalty(self, score, *args, **kwargs):
        return score

    monkeypatch.setattr(GroundTruthTagSimilarityScoringMechanism, "_calculate_penalty", dummy_penalty)

    # Create two responses but only one will be scored
    miner_result = {
        'tags': ['tag1', 'tag2', 'tag3'],
        'vectors': {
            'tag1': {'vectors': np.array([1.0, 0.0, 0.0])},
            'tag2': {'vectors': np.array([0.0, 1.0, 0.0])},
            'tag3': {'vectors': np.array([0.0, 0.0, 1.0])},
        },
    }
    axon1 = DummyAxon('uuid-4', 'hk-4')
    axon2 = DummyAxon('uuid-5', 'hk-5')
    response1 = DummyResponse([miner_result], axon1)
    response2 = DummyResponse(None, axon2)
    responses = [response1, response2]

    scoring_mechanism = GroundTruthTagSimilarityScoringMechanism()
    # This should not trigger the mismatch, but let's force it by patching rank_scores to be a different length
    # Patch np.zeros to return a different shape
    orig_np_zeros = np.zeros
    monkeypatch.setattr("numpy.zeros", lambda n: orig_np_zeros(n + 1))
    final_scores, rank_scores = await scoring_mechanism.evaluate(task_bundle, miner_responses=responses)
    assert final_scores is None
    assert rank_scores is None
