import pprint
from traceback import print_exception
from typing import ClassVar

import bittensor as bt
import numpy as np

from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.scoring_mechanism.ScoringMechanism import ScoringMechanism
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.constants import PENALTIES
from conversationgenome.utils.Utils import Utils


class GroundTruthTagSimilarityScoringMechanism(ScoringMechanism):
    min_tags: int = 3
    max_scored_tags: ClassVar[int] = 20
    verbose: ClassVar[bool] = False
    scoring_factors: ClassVar[dict] = {
        "top_3_mean": 0.55,
        "median_score": 0.1,
        "mean_score": 0.25,
        "max_score": 0.1,
    }

    async def evaluate(self, task_bundle: TaskBundle, miner_responses=None):
        full_conversation_neighborhood = await self._calculate_semantic_neighborhood(task_bundle.input.metadata)
        num_responses = len(miner_responses)
        zero_score_mask = np.ones(num_responses)
        rank_scores = np.zeros(num_responses)
        final_scores = []

        for idx, response in enumerate(miner_responses):
            score_entry = await self._evaluate_single_response(idx, response, task_bundle, full_conversation_neighborhood, zero_score_mask)
            final_scores.append(score_entry)

        bt.logging.debug(f"Complete evaluation. Final scores:\n{pprint.pformat(final_scores, indent=2)}")

        if len(final_scores) != len(rank_scores):
            bt.logging.error(f"ERROR: final scores length ({len(final_scores)})  doesn't match rank scores ({len(rank_scores)}). Aborting.")
            return (None, None)

        for idx, final_score in enumerate(final_scores):
            rank_scores[idx] = final_score.get('final_miner_score', 0.0)

        return (final_scores, rank_scores)

    async def _evaluate_single_response(self, idx, response, task_bundle, full_conversation_neighborhood, zero_score_mask):
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
        if not self._has_enough_tags(miner_result, idx):
            zero_score_mask[idx] = 0
            return {"uuid": uuid, "hotkey": hotkey, "adjustedScore": 0.0, "final_miner_score": 0.0}

        try:
            results = await self._calc_scores(
                full_convo_metadata=task_bundle.input.metadata,
                full_conversation_neighborhood=full_conversation_neighborhood,
                miner_result=miner_result,
            )
        except Exception as e:
            bt.logging.error(f"Error while calculating scores for response {idx}: {e}")
            bt.logging.debug(print_exception(type(e), e, e.__traceback__))
            zero_score_mask[idx] = 0
            return {"uuid": uuid, "hotkey": hotkey, "adjustedScore": 0.0, "final_miner_score": 0.0}

        (scores, scores_both, scores_unique, diff) = results
        stats = self._calculate_stats(scores, scores_unique)
        adjusted_score = self._calculate_adjusted_score(stats)

        both_tags = diff['both']
        unique_tags = diff['unique_2']
        total_tag_count = len(both_tags) + len(unique_tags)

        final_miner_score = await self._calculate_penalty(
            adjusted_score,
            total_tag_count,
            len(unique_tags),
            stats['min_score'],
            stats['max_score'],
        )

        bt.logging.debug(
            f"_______ ADJ SCORE: {adjusted_score} ___Num Tags: {len(miner_result['tags'])} Unique Tag Scores: {scores_unique} Median score: {stats['median_score']} Mean score: {stats['mean_score']} Top 3 Mean: {stats['top_3_mean']} Min: {stats['min_score']} Max: {stats['max_score']}"
        )

        return {
            "uid": idx + 1,
            "uuid": uuid,
            "hotkey": hotkey,
            "adjustedScore": adjusted_score,
            "final_miner_score": final_miner_score,
        }

    def _has_enough_tags(self, miner_result, idx):
        try:
            if miner_result is None or not miner_result or len(miner_result['tags']) < self.min_tags:
                bt.logging.info(f"Only {len(miner_result['tags']) if miner_result and 'tags' in miner_result else 0} tag(s) found for miner response {idx}. Skipping.")
                return False
        except Exception as e:
            bt.logging.error(f"Error while initial checking {idx}-th response: {e}, 0 score")
            bt.logging.debug(print_exception(type(e), e, e.__traceback__))
            return False
        return True

    def _calculate_stats(self, scores, scores_unique):
        if len(scores) == 0:
            mean_score = 0.0
            median_score = 0.0
            min_score = 0.0
            max_score = 0.0
        else:
            mean_score = np.mean(scores)
            median_score = np.median(scores)
            min_score = np.min(scores)
            max_score = np.max(scores)

        if len(scores_unique) == 0:
            sorted_unique_scores = np.array([0.0, 0.0, 0.0])
        else:
            sorted_unique_scores = np.sort(scores_unique)

        top_3_sorted_unique_scores = sorted_unique_scores
        if len(sorted_unique_scores) >= 3:
            top_3_sorted_unique_scores = sorted_unique_scores[-3:]
        while len(top_3_sorted_unique_scores) < 3:
            top_3_sorted_unique_scores = np.append(top_3_sorted_unique_scores, 0.0)

        top_3_mean = np.mean(top_3_sorted_unique_scores)

        return {
            'top_3_mean': Utils.safe_value(top_3_mean),
            'median_score': Utils.safe_value(median_score),
            'mean_score': Utils.safe_value(mean_score),
            'max_score': Utils.safe_value(max_score),
            'min_score': Utils.safe_value(min_score),
        }

    def _calculate_adjusted_score(self, stats):
        return (
            (self.scoring_factors['top_3_mean'] * stats['top_3_mean'])
            + (self.scoring_factors['median_score'] * stats['median_score'])
            + (self.scoring_factors['mean_score'] * stats['mean_score'])
            + (self.scoring_factors['max_score'] * stats['max_score'])
        )

    async def _calculate_semantic_neighborhood(self, conversation_metadata: ConversationMetadata, tag_count_ceiling=None):
        all_vectors = []
        count = 0

        # Note: conversation_metadata['vectors'] is a dict, so:
        #       numeric_vectors = conversation_metadata['vectors'][tag_name]['vectors']
        for tag_name, val in conversation_metadata.vectors.items():
            all_vectors.append(val['vectors'])
            # all_vectors.append(val)
            count += 1
            if tag_count_ceiling and count > tag_count_ceiling:
                break

        # Create a vector representing the entire content by averaging the vectors of all tokens
        if len(all_vectors) > 0:
            neighborhood_vectors = np.mean(all_vectors, axis=0)
            return neighborhood_vectors
        else:
            return None

    async def _calc_scores(self, full_convo_metadata: ConversationMetadata, full_conversation_neighborhood, miner_result):
        full_convo_tags = full_convo_metadata.tags
        tags = miner_result["tags"]
        tag_vector_dict = miner_result["vectors"]

        scores = []
        scores_both = []
        scores_unique = []

        # Remove duplicate tags
        tag_set = list(set(tags))
        diff = Utils.compare_arrays(full_convo_tags, tag_set)

        for idx, tag in enumerate(tag_set):
            if idx > self.max_scored_tags:
                bt.logging.debug(f"WARNING 638871: Total tag count ({len(tag_set)}) is greater than max_scored_tags. Only {self.max_scored_tags} will be scored")
                break

            is_unique = False

            if tag in diff['unique_2']:
                is_unique = True

            # bt.logging.info(example, resp2)
            if not tag in tag_vector_dict:
                bt.logging.error(f"No vectors found for tag '{tag}'. Score of 0. Unique: {is_unique}")
                scores.append(0)
                if is_unique:
                    scores_unique.append(0)
                else:
                    scores_both.append(0)
                continue

            tag_vectors = tag_vector_dict[tag]['vectors']
            score = self._score_vector_similarity(full_conversation_neighborhood, tag_vectors, tag)
            scores.append(score)

            if is_unique:
                scores_unique.append(score)
            else:
                scores_both.append(score)

        bt.logging.info(f"Scores num: {len(scores)} num of Unique tags: {len(scores_unique)} num of full convo tags: {len(full_convo_tags)}")

        return (scores, scores_both, scores_unique, diff)

    async def _calculate_penalty(self, score, num_tags, num_unique_tags, min_score, max_score):
        final_score = score
        num_both_tags = num_tags - num_unique_tags

        # No both tags. Penalize.
        if num_both_tags == 0:
            bt.logging.debug("!!PENALTY: No BOTH tags")
            final_score *= PENALTIES["no_both_tags"]["penalty"]

        # All junk tags. Penalize
        if max_score < PENALTIES["all_junk_tags"]["threshold"]:
            bt.logging.debug(f"!!PENALTY: max_score < {PENALTIES['all_junk_tags']['threshold']} -- all junk tags")
            final_score *= PENALTIES["all_junk_tags"]["penalty"]

        # Very few tags. Penalize.
        if num_tags < PENALTIES["too_few_tags"]["threshold"]:
            bt.logging.debug(f"!!PENALTY: < {PENALTIES['too_few_tags']['threshold']} TOTAL tags")
            final_score *= PENALTIES["too_few_tags"]["penalty"]

        # no unique tags. Penalize
        if num_unique_tags < 1:
            bt.logging.debug("!!PENALTY: less than 1 unique tag")
            final_score *= PENALTIES["num_unique_tags"]["less_than_1"]["penalty"]
        elif num_unique_tags < 2:
            bt.logging.debug("!!PENALTY: less than 2 unique tags")
            final_score *= PENALTIES["num_unique_tags"]["less_than_2"]["penalty"]
        elif num_unique_tags < 3:
            bt.logging.debug("!!PENALTY: less than 3 unique tags")
            final_score *= PENALTIES["num_unique_tags"]["less_than_3"]["penalty"]

        return final_score

    def _score_vector_similarity(self, neighborhood_vectors, individual_vectors, tag=None):
        similarity_score = 0

        # Calculate the similarity score between the neighborhood_vectors and the individual_vectors
        # If all vectors are 0.0, the vector wasn't found for scoring in the embedding score
        if np.all(individual_vectors == 0):
            bt.logging.error("All empty vectors")
            return 0

        # Calculate the cosine similarity between two sets of vectors
        try:
            similarity_score = np.dot(neighborhood_vectors, individual_vectors) / (np.linalg.norm(neighborhood_vectors) * np.linalg.norm(individual_vectors))
        except:
            bt.logging.error("Error generating similarity_score. Setting to zero.")

        return similarity_score
