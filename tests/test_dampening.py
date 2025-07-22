import unittest
from typing import List

import numpy as np
import pytest

from conversationgenome.mock import MockBt
from conversationgenome.validator.ValidatorLib import ValidatorLib

verbose = True
bt = None

try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()


class DampeningTestCase(unittest.TestCase):
    verbose = True
    vl = None

    def setUp(self):
        self.vl = ValidatorLib()
        self.vl.verbose = False
        pass

    def test_given_uids_with_previous_scores_when_they_score_0_then_they_are_dampened(self):
        uids: List[int] = [1, 2, 3]
        rewards = np.array([0.0, 0.2, 0.0], dtype=np.float32)
        ema_scores = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
        scores = np.array([0.004455, 0.035550, 0.120000, 0.284445, 0.555550], dtype=np.float32)
        moving_average_alpha = 0.1
        device = "cuda"
        neurons = 5
        nonlinear_power = 3
 
        scores, updated_ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)

        assert updated_ema_scores[0] == pytest.approx(ema_scores[0]) #  No change, same score
        assert updated_ema_scores[1] == pytest.approx(moving_average_alpha / 2 * rewards[0] + (1 - moving_average_alpha / 2) * ema_scores[1], abs=1e-2) #  Received a score of 0, so the alpha should be lower
        assert updated_ema_scores[2] == pytest.approx(moving_average_alpha * rewards[1] + (1 - moving_average_alpha) * ema_scores[2], abs=1e-2) #  Regular alpha is applied cause the miner scored
        assert updated_ema_scores[3] == pytest.approx(moving_average_alpha / 2 * rewards[2] + (1 - moving_average_alpha / 2) * ema_scores[3], abs=1e-2) #  Received a score of 0, so the alpha should be lower
        assert updated_ema_scores[4] == pytest.approx(ema_scores[4]) #  No change, same score
        
