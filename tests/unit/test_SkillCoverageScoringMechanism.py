import numpy as np
import pytest

from conversationgenome.scoring_mechanism.SkillCoverageScoringMechanism import (
    SkillCoverageScoringMechanism,
)
from conversationgenome.utils.constants import PENALTIES


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


class DummyAxon:
    def __init__(self, uuid, hotkey):
        self.uuid = uuid
        self.hotkey = hotkey


class DummyResponse:
    def __init__(self, cgp_output=None, axon=None):
        self.cgp_output = cgp_output
        self.axon = axon


class DummyMetadata:
    def __init__(self, section_vectors):
        self.section_vectors = section_vectors


class DummyInput:
    def __init__(self, metadata):
        self.metadata = metadata


class DummyTaskBundle:
    def __init__(self, metadata):
        self.input = DummyInput(metadata)


def _section_vectors():
    return {
        "s1": [1.0, 0.0, 0.0],
        "s2": [0.0, 1.0, 0.0],
    }


def _make_test(name, description, vector, judged_correct=True):
    return {"name": name, "description": description, "vector": vector, "judged_correct": judged_correct}


@pytest.mark.asyncio
async def test_evaluate_with_valid_responses(monkeypatch):
    metadata = DummyMetadata(_section_vectors())
    task_bundle = DummyTaskBundle(metadata)

    monkeypatch.setattr("conversationgenome.scoring_mechanism.SkillCoverageScoringMechanism.bt.logging", DummyLogging)

    miner_result = {
        "skill_vector": [0.5, 0.5, 0.0],
        "test_vectors": {
            # Both s1 tests match perfectly -- top-2 mean is still 1.0.
            "s1": [_make_test("t1", "d1", [1.0, 0.0, 0.0]), _make_test("t2", "d2", [1.0, 0.0, 0.0])],
            "s2": [_make_test("t3", "d3", [0.0, 1.0, 0.0])],
        },
    }
    axon = DummyAxon("uuid-1", "hk-1")
    response = DummyResponse([miner_result], axon)

    scoring_mechanism = SkillCoverageScoringMechanism()
    final_scores, rank_scores = await scoring_mechanism.evaluate(task_bundle, miner_responses=[response])

    assert isinstance(final_scores, list)
    assert isinstance(rank_scores, np.ndarray)
    assert final_scores[0]["uuid"] == "uuid-1"
    assert final_scores[0]["hotkey"] == "hk-1"
    assert final_scores[0]["section_scores"]["s1"] == pytest.approx(1.0)
    assert final_scores[0]["section_scores"]["s2"] == pytest.approx(1.0)
    assert final_scores[0]["section_coverage"] == pytest.approx(1.0)
    assert final_scores[0]["final_miner_score"] > 0


@pytest.mark.asyncio
async def test_evaluate_with_empty_miner_response(monkeypatch):
    metadata = DummyMetadata(_section_vectors())
    task_bundle = DummyTaskBundle(metadata)

    monkeypatch.setattr("conversationgenome.scoring_mechanism.SkillCoverageScoringMechanism.bt.logging", DummyLogging)

    axon = DummyAxon("uuid-2", "hk-2")
    response = DummyResponse(None, axon)

    scoring_mechanism = SkillCoverageScoringMechanism()
    final_scores, rank_scores = await scoring_mechanism.evaluate(task_bundle, miner_responses=[response])

    assert final_scores[0]["uuid"] == "uuid-2"
    assert final_scores[0]["final_miner_score"] == 0.0


@pytest.mark.asyncio
async def test_evaluate_with_insufficient_tests(monkeypatch):
    metadata = DummyMetadata(_section_vectors())
    task_bundle = DummyTaskBundle(metadata)

    monkeypatch.setattr("conversationgenome.scoring_mechanism.SkillCoverageScoringMechanism.bt.logging", DummyLogging)

    miner_result = {
        "skill_vector": [0.5, 0.5, 0.0],
        "test_vectors": {"s1": [_make_test("t1", "d1", [1.0, 0.0, 0.0])]},  # only 1 test, below min_tests=3
    }
    axon = DummyAxon("uuid-3", "hk-3")
    response = DummyResponse([miner_result], axon)

    scoring_mechanism = SkillCoverageScoringMechanism()
    final_scores, rank_scores = await scoring_mechanism.evaluate(task_bundle, miner_responses=[response])

    assert final_scores[0]["final_miner_score"] == 0.0


@pytest.mark.asyncio
async def test_evaluate_final_scores_length_mismatch(monkeypatch):
    metadata = DummyMetadata(_section_vectors())
    task_bundle = DummyTaskBundle(metadata)

    monkeypatch.setattr("conversationgenome.scoring_mechanism.SkillCoverageScoringMechanism.bt.logging", DummyLogging)

    miner_result = {
        "skill_vector": [0.5, 0.5, 0.0],
        "test_vectors": {
            "s1": [_make_test("t1", "d1", [1.0, 0.0, 0.0]), _make_test("t2", "d2", [0.9, 0.1, 0.0])],
            "s2": [_make_test("t3", "d3", [0.0, 1.0, 0.0])],
        },
    }
    axon1 = DummyAxon("uuid-4", "hk-4")
    response1 = DummyResponse([miner_result], axon1)

    scoring_mechanism = SkillCoverageScoringMechanism()
    orig_np_zeros = np.zeros
    monkeypatch.setattr("numpy.zeros", lambda n: orig_np_zeros(n + 1))
    final_scores, rank_scores = await scoring_mechanism.evaluate(task_bundle, miner_responses=[response1])
    assert final_scores is None
    assert rank_scores is None


def test_score_sections_missing_section_scores_zero():
    scoring_mechanism = SkillCoverageScoringMechanism()
    section_vectors = _section_vectors()
    test_vectors = {"s1": [_make_test("t1", "d1", [1.0, 0.0, 0.0])]}  # s2 has no submitted tests

    section_scores = scoring_mechanism._score_sections(section_vectors, test_vectors)

    assert section_scores["s1"] == pytest.approx(1.0)
    assert section_scores["s2"] == 0.0


def test_score_sections_excludes_judged_incorrect_tests():
    scoring_mechanism = SkillCoverageScoringMechanism()
    section_vectors = _section_vectors()
    # Perfect match on s1, but judged incorrect -- must not win the section.
    test_vectors = {
        "s1": [
            _make_test("t1_wrong", "d1", [1.0, 0.0, 0.0], judged_correct=False),
            _make_test("t2_right", "d2", [0.5, 0.5, 0.0], judged_correct=True),
        ],
    }

    section_scores = scoring_mechanism._score_sections(section_vectors, test_vectors)

    assert section_scores["s1"] == pytest.approx(scoring_mechanism._cosine_similarity([1.0, 0.0, 0.0], [0.5, 0.5, 0.0]))
    assert section_scores["s2"] == 0.0


def test_score_sections_uses_top_k_mean_not_single_best():
    scoring_mechanism = SkillCoverageScoringMechanism()
    section_vectors = {"s1": [1.0, 0.0, 0.0]}
    # 3 judged-correct tests of decreasing quality. top_k_per_section=2, so the
    # score should be the mean of the best 2, not just the single best one --
    # a lone great test can no longer carry the section by itself.
    test_vectors = {
        "s1": [
            _make_test("t1", "d1", [1.0, 0.0, 0.0]),   # cos = 1.0
            _make_test("t2", "d2", [0.0, 1.0, 0.0]),   # cos = 0.0
            _make_test("t3", "d3", [0.0, 0.0, 1.0]),   # cos = 0.0
        ],
    }

    section_scores = scoring_mechanism._score_sections(section_vectors, test_vectors)

    # mean of the top 2 scores (1.0, 0.0) = 0.5, NOT the single best score of 1.0.
    assert section_scores["s1"] == pytest.approx(0.5)


def test_has_flooded_section():
    mechanism = SkillCoverageScoringMechanism()
    threshold = PENALTIES["test_flooding"]["threshold"]

    not_flooded = {"s1": [_make_test(f"t{i}", "d", [1.0, 0.0, 0.0]) for i in range(threshold)]}
    flooded = {"s1": [_make_test(f"t{i}", "d", [1.0, 0.0, 0.0]) for i in range(threshold + 1)]}

    assert mechanism._has_flooded_section(not_flooded) is False
    assert mechanism._has_flooded_section(flooded) is True


def test_calculate_penalty_test_flooding():
    mechanism = SkillCoverageScoringMechanism()
    base_score = 1.0
    threshold = PENALTIES["test_flooding"]["threshold"]
    # All judged-correct and mutually orthogonal (dodges near_duplicate_tests)
    # so only the flooding penalty is exercised in isolation.
    test_vectors = {
        "s1": [
            _make_test(f"t{i}", "d", [1.0 if j == i else 0.0 for j in range(threshold + 1)])
            for i in range(threshold + 1)
        ],
    }
    score = mechanism._calculate_penalty(base_score, total_tests=threshold + 1, sections_addressed=1, test_vectors=test_vectors)
    expected = base_score * PENALTIES["test_flooding"]["penalty"]
    assert score == pytest.approx(expected)


def test_score_skill_coverage_returns_zero_without_skill_vector():
    scoring_mechanism = SkillCoverageScoringMechanism()
    test_vectors = {"s1": [_make_test("t1", "d1", [1.0, 0.0, 0.0])]}
    assert scoring_mechanism._score_skill_coverage(None, test_vectors) == 0.0


def test_score_skill_coverage_ignores_judged_incorrect_tests():
    scoring_mechanism = SkillCoverageScoringMechanism()
    test_vectors = {
        "s1": [
            _make_test("t1_wrong", "d1", [0.0, 0.0, 1.0], judged_correct=False),
            _make_test("t2_right", "d2", [1.0, 0.0, 0.0], judged_correct=True),
        ],
    }
    # Skill vector matches only the judged-correct test's vector -- if the
    # incorrect test were still pooled into the mean, similarity would drop.
    assert scoring_mechanism._score_skill_coverage([1.0, 0.0, 0.0], test_vectors) == pytest.approx(1.0)


def test_calculate_penalty_no_sections_addressed():
    mechanism = SkillCoverageScoringMechanism()
    score = mechanism._calculate_penalty(1.0, total_tests=5, sections_addressed=0, test_vectors={})
    assert score == 0.0


def test_calculate_penalty_too_few_tests():
    mechanism = SkillCoverageScoringMechanism()
    base_score = 1.0
    test_vectors = {"s1": [_make_test("t1", "d1", [1.0, 0.0, 0.0])]}
    score = mechanism._calculate_penalty(base_score, total_tests=1, sections_addressed=1, test_vectors=test_vectors)
    expected = base_score * PENALTIES["too_few_tests"]["penalty"]
    assert score == pytest.approx(expected)


def test_calculate_penalty_near_duplicate_tests():
    mechanism = SkillCoverageScoringMechanism()
    base_score = 1.0
    test_vectors = {
        "s1": [
            _make_test("t1", "d1", [1.0, 0.0, 0.0]),
            _make_test("t2", "d2", [1.0, 0.0, 0.0]),  # identical vector -> near-duplicate
            _make_test("t3", "d3", [1.0, 0.0, 0.0]),
            _make_test("t4", "d4", [1.0, 0.0, 0.0]),
            _make_test("t5", "d5", [1.0, 0.0, 0.0]),
        ],
    }
    score = mechanism._calculate_penalty(base_score, total_tests=5, sections_addressed=1, test_vectors=test_vectors)
    expected = base_score * PENALTIES["near_duplicate_tests"]["penalty"]
    assert score == pytest.approx(expected)


def test_calculate_penalty_low_assertion_accuracy():
    mechanism = SkillCoverageScoringMechanism()
    base_score = 1.0
    # 1 correct out of 5 (0.2 accuracy) -- below the 0.5 threshold. Vectors are
    # mutually orthogonal so this doesn't also trip near_duplicate_tests.
    test_vectors = {
        "s1": [
            _make_test("t1", "d1", [1.0, 0.0, 0.0, 0.0, 0.0], judged_correct=True),
            _make_test("t2", "d2", [0.0, 1.0, 0.0, 0.0, 0.0], judged_correct=False),
            _make_test("t3", "d3", [0.0, 0.0, 1.0, 0.0, 0.0], judged_correct=False),
            _make_test("t4", "d4", [0.0, 0.0, 0.0, 1.0, 0.0], judged_correct=False),
            _make_test("t5", "d5", [0.0, 0.0, 0.0, 0.0, 1.0], judged_correct=False),
        ],
    }
    score = mechanism._calculate_penalty(base_score, total_tests=5, sections_addressed=1, test_vectors=test_vectors)
    expected = base_score * PENALTIES["low_assertion_accuracy"]["penalty"]
    assert score == pytest.approx(expected)


def test_calculate_penalty_high_assertion_accuracy_no_penalty():
    mechanism = SkillCoverageScoringMechanism()
    base_score = 1.0
    test_vectors = {
        "s1": [
            _make_test("t1", "d1", [1.0, 0.0, 0.0, 0.0, 0.0], judged_correct=True),
            _make_test("t2", "d2", [0.0, 1.0, 0.0, 0.0, 0.0], judged_correct=True),
            _make_test("t3", "d3", [0.0, 0.0, 1.0, 0.0, 0.0], judged_correct=True),
            _make_test("t4", "d4", [0.0, 0.0, 0.0, 1.0, 0.0], judged_correct=True),
            _make_test("t5", "d5", [0.0, 0.0, 0.0, 0.0, 1.0], judged_correct=False),
        ],
    }
    score = mechanism._calculate_penalty(base_score, total_tests=5, sections_addressed=1, test_vectors=test_vectors)
    assert score == pytest.approx(base_score)


def test_cosine_similarity_handles_zero_vectors():
    mechanism = SkillCoverageScoringMechanism()
    assert mechanism._cosine_similarity([0.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == 0.0
    assert mechanism._cosine_similarity(None, [1.0, 0.0, 0.0]) == 0.0
