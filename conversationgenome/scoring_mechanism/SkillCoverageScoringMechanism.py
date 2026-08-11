import pprint
from traceback import print_exception
from typing import ClassVar

import bittensor as bt
import numpy as np

from conversationgenome.scoring_mechanism.ScoringMechanism import ScoringMechanism
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.constants import PENALTIES
from conversationgenome.utils.Utils import Utils


class SkillCoverageScoringMechanism(ScoringMechanism):
    """
    Scores a skill_coverage_evaluation response via two embedding-based signals:

    - Section Coverage: for each validator-defined section, the mean cosine
      similarity of the miner's top `top_k_per_section` best-matching submitted
      tests for that section (not a single best match -- see below). Sections
      with no submitted test score 0.
    - Skill Coverage: the cosine similarity between the mean embedding of all the
      miner's submitted test descriptions (a "test-suite neighborhood", analogous
      to GroundTruthTagSimilarityScoringMechanism's semantic neighborhood) and the
      embedding of the miner's own generated skill text.

    Only tests with judged_correct=True count towards either signal. Embedding
    similarity alone can't distinguish a correct assertion from a confidently
    wrong or vaguely generic one (nothing here executes code), so
    TaskBundle.format_results() runs an LLM-as-judge correctness pass over every
    submitted test before scoring and stamps each one with judged_correct. A test
    that isn't judged_correct is excluded from best-match selection entirely --
    it can't win a section, and it can't pull the skill-coverage neighborhood
    towards itself -- rather than merely scoring low, since embedding similarity
    would otherwise still reward it for being topically on-target regardless of
    truth.

    Section scoring uses a top-K mean rather than a single max specifically to
    resist volume gaming: a lone lucky/cherry-picked test can no longer carry a
    whole section on its own -- a miner needs multiple genuinely good, distinct,
    judged-correct tests to score well, not just one. This is combined with two
    more volume guardrails: TaskBundle.format_results() hard-caps how many tests
    per section are even embedded/judged (PER_SECTION_TEST_CAP, tied to
    PENALTIES["test_flooding"]["threshold"]), and _calculate_penalty applies the
    test_flooding penalty when a section exceeds that cap, on top of losing
    scoring credit for the excess.

    No LLM/embedding calls happen here -- all vectors and judged_correct flags are
    expected to already be present on the miner_result (populated by
    TaskBundle.format_results()) and on the task_bundle's ground-truth metadata
    (populated at TaskBundle.setup()).
    """

    min_tests: int = 3
    top_k_per_section: ClassVar[int] = 2
    duplicate_test_similarity_threshold: float = PENALTIES["near_duplicate_tests"]["threshold"]
    scoring_factors: ClassVar[dict] = {
        "section_coverage": 0.6,
        "skill_coverage": 0.4,
    }

    async def evaluate(self, task_bundle: TaskBundle, miner_responses=None):
        section_vectors = task_bundle.input.metadata.section_vectors
        num_responses = len(miner_responses)
        rank_scores = np.zeros(num_responses)
        final_scores = []

        for idx, response in enumerate(miner_responses):
            score_entry = await self._evaluate_single_response(idx, response, section_vectors)
            final_scores.append(score_entry)

        bt.logging.debug(f"Complete evaluation. Final scores:\n{pprint.pformat(final_scores, indent=2)}")

        if len(final_scores) != len(rank_scores):
            bt.logging.error(f"ERROR: final scores length ({len(final_scores)}) doesn't match rank scores ({len(rank_scores)}). Aborting.")
            return (None, None)

        for idx, final_score in enumerate(final_scores):
            rank_scores[idx] = final_score.get('final_miner_score', 0.0)

        return (final_scores, rank_scores)

    async def _evaluate_single_response(self, idx, response, section_vectors):
        try:
            miner_response = response.cgp_output
        except Exception:
            miner_response = response

        uuid = f"uuid-{idx}"
        hotkey = "hk-uuid"
        try:
            uuid = response.axon.uuid
            hotkey = response.axon.hotkey
        except Exception:
            pass

        if not miner_response:
            return {"uuid": uuid, "hotkey": hotkey, "adjustedScore": 0.0, "final_miner_score": 0.0}

        miner_result = miner_response[0]
        test_vectors = miner_result.get('test_vectors') if miner_result else None
        if not self._has_enough_tests(miner_result, test_vectors, idx):
            return {"uuid": uuid, "hotkey": hotkey, "adjustedScore": 0.0, "final_miner_score": 0.0}

        try:
            section_scores = self._score_sections(section_vectors, test_vectors)
            section_coverage = float(np.mean(list(section_scores.values()))) if section_scores else 0.0
            skill_coverage = self._score_skill_coverage(miner_result.get('skill_vector'), test_vectors)
        except Exception as e:
            bt.logging.error(f"Error while calculating scores for response {idx}: {e}")
            bt.logging.debug(print_exception(type(e), e, e.__traceback__))
            return {"uuid": uuid, "hotkey": hotkey, "adjustedScore": 0.0, "final_miner_score": 0.0}

        adjusted_score = self._calculate_adjusted_score(section_coverage, skill_coverage)

        total_tests = sum(len(tests) for tests in (test_vectors or {}).values())
        sections_addressed = len([s for s in section_scores.values() if s > 0])

        final_miner_score = self._calculate_penalty(
            adjusted_score,
            total_tests=total_tests,
            sections_addressed=sections_addressed,
            test_vectors=test_vectors,
        )

        bt.logging.debug(
            f"_______ ADJ SCORE: {adjusted_score} Section Coverage: {section_coverage} Skill Coverage: {skill_coverage} Total tests: {total_tests} Sections addressed: {sections_addressed}/{len(section_vectors)}"
        )

        return {
            "uid": idx + 1,
            "uuid": uuid,
            "hotkey": hotkey,
            "section_scores": section_scores,
            "section_coverage": Utils.safe_value(section_coverage),
            "skill_coverage": Utils.safe_value(skill_coverage),
            "adjustedScore": Utils.safe_value(adjusted_score),
            "final_miner_score": Utils.safe_value(final_miner_score),
        }

    def _has_enough_tests(self, miner_result, test_vectors, idx):
        try:
            total_tests = sum(len(tests) for tests in (test_vectors or {}).values())
            if total_tests < self.min_tests:
                bt.logging.info(f"Only {total_tests} test(s) found for miner response {idx}. Skipping.")
                return False
        except Exception as e:
            bt.logging.error(f"Error while initial checking {idx}-th response: {e}")
            bt.logging.debug(print_exception(type(e), e, e.__traceback__))
            return False
        return True

    def _score_sections(self, section_vectors, test_vectors):
        section_scores = {}
        test_vectors = test_vectors or {}
        for section_id, section_vector in section_vectors.items():
            scores = []
            for test in test_vectors.get(section_id, []):
                if not test.get('judged_correct', False):
                    continue
                vector = test.get('vector')
                if not vector:
                    continue
                scores.append(self._cosine_similarity(section_vector, vector))
            if scores:
                top_scores = sorted(scores, reverse=True)[:self.top_k_per_section]
                section_scores[section_id] = float(np.mean(top_scores))
            else:
                section_scores[section_id] = 0.0
        return section_scores

    def _score_skill_coverage(self, skill_vector, test_vectors):
        if not skill_vector:
            return 0.0

        all_test_vectors = [
            test['vector']
            for tests in (test_vectors or {}).values()
            for test in tests
            if test.get('vector') and test.get('judged_correct', False)
        ]
        if not all_test_vectors:
            return 0.0

        test_suite_neighborhood = np.mean(all_test_vectors, axis=0)
        return self._cosine_similarity(test_suite_neighborhood, skill_vector)

    def _calculate_adjusted_score(self, section_coverage, skill_coverage):
        return (
            (self.scoring_factors['section_coverage'] * section_coverage)
            + (self.scoring_factors['skill_coverage'] * skill_coverage)
        )

    def _calculate_penalty(self, score, total_tests, sections_addressed, test_vectors):
        final_score = score

        # No section was addressed at all. Zero out.
        if sections_addressed == 0:
            bt.logging.debug("!!PENALTY: no sections addressed")
            return 0.0

        # Very few tests overall. Penalize.
        if total_tests < PENALTIES["too_few_tests"]["threshold"]:
            bt.logging.debug(f"!!PENALTY: < {PENALTIES['too_few_tests']['threshold']} total tests")
            final_score *= PENALTIES["too_few_tests"]["penalty"]

        # Near-duplicate/stuffed tests. Penalize.
        if self._has_near_duplicate_tests(test_vectors):
            bt.logging.debug("!!PENALTY: near-duplicate tests detected")
            final_score *= PENALTIES["near_duplicate_tests"]["penalty"]

        # Most submitted tests failed the correctness judge. This is on top of
        # (not instead of) losing best-match credit for the incorrect tests
        # themselves -- it exists to make fabrication actively costly rather
        # than merely unrewarded, since "try it and see if it slips through"
        # would otherwise be free for a miner mixing some correct tests in.
        accuracy = self._judged_accuracy(test_vectors, total_tests)
        if accuracy < PENALTIES["low_assertion_accuracy"]["threshold"]:
            bt.logging.debug(f"!!PENALTY: low judged-assertion accuracy ({accuracy:.2f})")
            final_score *= PENALTIES["low_assertion_accuracy"]["penalty"]

        # A section was flooded with more tests than PER_SECTION_TEST_CAP. The
        # excess already scores nothing (never embedded/judged), but flooding
        # is penalized on top of that rather than just left unrewarded, so
        # "submit dozens per section on the off chance it helps" has a real
        # downside instead of being a free-to-try strategy.
        if self._has_flooded_section(test_vectors):
            bt.logging.debug(f"!!PENALTY: a section exceeded the {PENALTIES['test_flooding']['threshold']}-test cap")
            final_score *= PENALTIES["test_flooding"]["penalty"]

        return final_score

    def _has_flooded_section(self, test_vectors):
        threshold = PENALTIES["test_flooding"]["threshold"]
        return any(len(tests) > threshold for tests in (test_vectors or {}).values())

    def _judged_accuracy(self, test_vectors, total_tests):
        if not total_tests:
            return 0.0
        correct = sum(
            1 for tests in (test_vectors or {}).values() for test in tests if test.get('judged_correct')
        )
        return correct / total_tests

    def _has_near_duplicate_tests(self, test_vectors):
        all_vectors = [
            test['vector']
            for tests in (test_vectors or {}).values()
            for test in tests
            if test.get('vector')
        ]
        for i in range(len(all_vectors)):
            for j in range(i + 1, len(all_vectors)):
                if self._cosine_similarity(all_vectors[i], all_vectors[j]) >= self.duplicate_test_similarity_threshold:
                    return True
        return False

    def _cosine_similarity(self, vec_a, vec_b):
        if vec_a is None or vec_b is None:
            return 0.0

        vec_a = np.array(vec_a)
        vec_b = np.array(vec_b)

        if vec_a.size == 0 or vec_b.size == 0 or np.all(vec_a == 0) or np.all(vec_b == 0):
            return 0.0

        try:
            return float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))
        except Exception:
            bt.logging.error("Error generating similarity score. Setting to zero.")
            return 0.0
