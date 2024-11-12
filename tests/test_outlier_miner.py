import pytest
import random
import unittest
import torch
import numpy as np

from conversationgenome.ConfigLib import c
from conversationgenome.utils.Utils import Utils
#
from conversationgenome.validator.ValidatorLib import ValidatorLib
from typing import List

verbose = True

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()

class TemplateEmaTestCase(unittest.TestCase):
    verbose = True
    vl= None

    def setUp(self):
        self.vl=ValidatorLib()
        self.vl.verbose=False
        pass

    def test_great_score_variation(self):
        iterations = 10000
        unavailable_uids = [0,9]
        stop_points = [round(iterations * 0.1), round(iterations * 0.5),round(iterations * 0.75)]
        print(f"iterations: {iterations}")
        print(f"stop points: {stop_points}")
        moving_average_alpha = 0.1
        device = "cuda"
        neurons = 5
        nonlinear_power = 3
        i=0
        scores = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        ema_scores = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        while i <= iterations:
            uids = []
            rewards = []
            if i in stop_points:
                stop_point = stop_points.index(i) + 1
                print(f"stop point {stop_point} iteration: {i}")
                print(f"EMA SCORES: {ema_scores}")
                print(f"SCORES: {scores}")
                print("\n")
                if stop_point == 1:
                    print("------UPDATING UID 0--------\n")
                    # Hardcode UID 0 reward to be 0.75, randomize the other two for this update
                    uids.append(0)
                    uids.extend(random.sample(range(1, 9), 2))
                    rewards.append(0.75)
                    rewards.extend([random.uniform(0.35, 0.55) for _ in range(2)])
                else:
                    i+=1
                    continue
            else:
                uids = random.sample(range(1, 9), 3)
                rewards = np.array([random.uniform(0.35, 0.55) for _ in range(3)], dtype=np.float32)
            
            #update without fix
            #scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)

            #update with fix
            scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power, unavailable_uids)

            i+=1

        print(f"Completed iterations")
        print(f"EMA SCORES: {ema_scores}")
        print(f"SCORES: {scores}")
