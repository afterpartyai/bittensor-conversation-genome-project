import pytest
import random
import unittest
import torch
import numpy as np

from conversationgenome.ConfigLib import c
from conversationgenome.mock import MockBt
from conversationgenome.utils.Utils import Utils
from conversationgenome.extensions import Extensions
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

    def test_nan(self):
       uids = [1, 2, 3]
       rewards = np.array([0.1, float('nan'), 0.3], dtype=np.float32)
       scores = np.array([0.004455, 0.035550, 0.120000, 0.284445, 0.555550], dtype=np.float32)
       ema_scores = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
       moving_average_alpha = 0.1
       device = "cuda"
       neurons = 5
       nonlinear_power = 3
       #print(f"Testing: ", rewards, uids)
       scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)
       #print(f"Testing nan: ", scores, ema_scores)
       assert np.isnan(ema_scores).any() == False
       assert np.isnan(scores).any() == False
       assert ema_scores[0] == pytest.approx(0.1, abs=1e-3)
       assert ema_scores[1] == pytest.approx(0.1900, abs=1e-3)
       assert ema_scores[2] == pytest.approx(0.2700, abs=1e-3)
       assert ema_scores[3] == pytest.approx(0.3900, abs=1e-3)
       assert ema_scores[4] == pytest.approx(0.5, abs=1e-3)
       assert scores[0] == pytest.approx(0.0047, abs=1e-3)
       assert scores[1] == pytest.approx(0.0324, abs=1e-3)
       assert scores[2] == pytest.approx(0.0929, abs=1e-3)
       assert scores[3] == pytest.approx(0.2800, abs=1e-3)
       assert scores[4] == pytest.approx(0.5900, abs=1e-3)

    def test_great_score_variation(self):
       uids = [1, 2, 3]
       rewards = np.array([0.1, 0.5, 1.0], dtype=np.float32)
       scores = np.array([0.004455, 0.035550, 0.120000, 0.284445, 0.555550], dtype=np.float32)
       ema_scores = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
       moving_average_alpha = 0.1
       device = "cuda"
       neurons = 5
       nonlinear_power = 3
       #print(f"Testing: ", rewards, uids)
       scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)
       #print(f"Testing great variation: ", scores, ema_scores)
       assert np.isnan(ema_scores).any() == False
       assert np.isnan(scores).any() == False
       assert ema_scores[0] == pytest.approx(0.1, abs=1e-3)
       assert ema_scores[1] == pytest.approx(0.1900, abs=1e-3)
       assert ema_scores[2] == pytest.approx(0.3200, abs=1e-3)       
       assert ema_scores[3] == pytest.approx(0.4600, abs=1e-3)
       assert ema_scores[4] == pytest.approx(0.5, abs=1e-3)
       assert scores[0] == pytest.approx(0.0038, abs=1e-3)
       assert scores[1] == pytest.approx(0.0261, abs=1e-3)
       assert scores[2] == pytest.approx(0.1246, abs=1e-3)
       assert scores[3] == pytest.approx(0.3702, abs=1e-3)
       assert scores[4] == pytest.approx(0.4754, abs=1e-3)

    def test_small_variation(self):
       uids = [1, 2, 3]
       rewards = np.array([0.285, 0.295, 0.32], dtype=np.float32)
       scores = np.array([0.174646, 0.183967, 0.193342, 0.213330, 0.234716], dtype=np.float32)
       ema_scores = np.array([0.29, 0.295, 0.3, 0.31, 0.32], dtype=np.float32)
       moving_average_alpha = 0.1
       device = "cuda"
       neurons = 5
       nonlinear_power = 3
       scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)
       #print(f"Testing small variation: ", scores, ema_scores)
       assert np.isnan(ema_scores).any() == False
       assert np.isnan(scores).any() == False
       assert ema_scores[0] == pytest.approx(0.2900, abs=1e-3)
       assert ema_scores[1] == pytest.approx(0.2940, abs=1e-3)
       assert ema_scores[2] == pytest.approx(0.2995, abs=1e-3)
       assert ema_scores[3] == pytest.approx(0.3110, abs=1e-3)
       assert ema_scores[4] == pytest.approx(0.3200, abs=1e-3)
       assert scores[0] == pytest.approx(0.1748, abs=1e-3)
       assert scores[1] == pytest.approx(0.1821, abs=1e-3)
       assert scores[2] == pytest.approx(0.1926, abs=1e-3)
       assert scores[3] == pytest.approx(0.2156, abs=1e-3)
       assert scores[4] == pytest.approx(0.2349, abs=1e-3)

    def test_no_variation(self):
       uids = [1, 2, 3]
       rewards = np.array([0.5, 0.5, 0.5], dtype=np.float32)
       scores = np.array([0.004455, 0.035550, 0.120000, 0.284445, 0.555550], dtype=np.float32)
       ema_scores = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
       moving_average_alpha = 0.1
       device = "cuda"
       neurons = 5
       nonlinear_power = 3
       scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)
       
       #print(f"Testing no variation: ", scores, ema_scores)
       assert np.isnan(ema_scores).any() == False
       assert np.isnan(scores).any() == False
       assert ema_scores[0] == pytest.approx(0.1, abs=1e-3)
       assert ema_scores[1] == pytest.approx(0.2300, abs=1e-3)
       assert ema_scores[2] == pytest.approx(0.3200, abs=1e-3)       
       assert ema_scores[3] == pytest.approx(0.4100, abs=1e-3)
       assert ema_scores[4] == pytest.approx(0.5, abs=1e-3)
       assert scores[0] == pytest.approx(0.0042, abs=1e-3)
       assert scores[1] == pytest.approx(0.0507, abs=1e-3)
       assert scores[2] == pytest.approx(0.1366, abs=1e-3)
       assert scores[3] == pytest.approx(0.2873, abs=1e-3)
       assert scores[4] == pytest.approx(0.5211, abs=1e-3)
    
    def test_zeros(self):
       uids = [1, 2, 3]
       original_rewards = np.array([0, 0, 0], dtype=np.float32)
       original_scores = np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)
       original_ema_scores = np.array([0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)
       moving_average_alpha = 0.1
       device = "cuda"
       neurons = 5
       nonlinear_power = 3
       
       scores, ema_scores = self.vl.update_scores(original_rewards, uids, original_ema_scores, original_scores, moving_average_alpha, device, neurons, nonlinear_power)
       
       print(f"EMA SCORES: {ema_scores}")
       print(f"SCORES: {scores}")

       assert np.isnan(ema_scores).any() == False
       assert np.isnan(scores).any() == False
       assert ema_scores[0] == pytest.approx(0.000000000000000, abs=1e-15)
       assert ema_scores[1] == pytest.approx(0.000000000000000, abs=1e-15)
       assert ema_scores[2] == pytest.approx(0.000000000000000, abs=1e-15)       
       assert ema_scores[3] == pytest.approx(0.000000000000000, abs=1e-15)
       assert ema_scores[4] == pytest.approx(1.0, abs=1e-15)
       assert scores[0] == pytest.approx(0.000000000000000, abs=1e-15)
       assert scores[1] == pytest.approx(0.000000000000000, abs=1e-15)
       assert scores[2] == pytest.approx(0.000000000000000, abs=1e-15)
       assert scores[3] == pytest.approx(0.000000000000000, abs=1e-15)
       assert scores[4] == pytest.approx(1.0000000000000000, abs=1e-15)
       ext = Extensions.Extensions()
       ext.execute("Metrics", "incStat", {"metric_name":"test_ema_zeroes", "inc":2})
       ext.execute("MetricsBADCLASS", "incStatBAD", {"metric_name":"test_ema_zeroes", "inc":2})
       ext.execute("Metrics", "incStatBADMETHOD", {"metric_name":"test_ema_zeroes", "inc":2})



    def update_scores(self, rewards: np.ndarray, uids: List[int]):
        #return np.array([0.4, 0.5, 0.6])
        rewards = np.nan_to_num(rewards, nan=0.0)
        rewards = np.clip(rewards, a_min=0.0, a_max=1.0)
        return rewards
