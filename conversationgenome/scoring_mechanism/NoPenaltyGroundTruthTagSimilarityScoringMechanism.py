import bittensor as bt

from conversationgenome.scoring_mechanism.GroundTruthTagSimilarityScoringMechanism import GroundTruthTagSimilarityScoringMechanism


class NoPenaltyGroundTruthTagSimilarityScoringMechanism(GroundTruthTagSimilarityScoringMechanism):
    # We skip the penalty for some task types (like NER)
    async def _calculate_penalty(self, score, num_tags, num_unique_tags, min_score, max_score):
        bt.logging.debug('Skipping penalty evaluation')
        return score
