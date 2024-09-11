import pytest
import random
import unittest
import torch

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
        pass

    def test_nan(self):
       thisdevice = "cuda" if torch.cuda.is_available() else "cpu"
       uids = [1,2,3]
       rewards = torch.tensor([0.1, float('nan') ,0.3],device=thisdevice)
       scores = torch.tensor([0.004455, 0.035550, 0.120000, 0.284445, 0.555550],device=thisdevice)
       ema_scores = torch.tensor([0.1,0.2,0.3,0.4,0.5],device=thisdevice)
       moving_average_alpha = 0.1
       device = "cuda"
       neurons = 5
       nonlinear_power = 3
       #print(f"Testing: ", rewards, uids)
       scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)
       #print(f"Testing nan: ", scores, ema_scores)
       assert torch.isnan(ema_scores).any() == False
       assert torch.isnan(scores).any() == False
       assert ema_scores[0].item() == pytest.approx(0.1,abs=1e-3)
       assert ema_scores[1].item() == pytest.approx(0.1900,abs=1e-3)
       assert ema_scores[2].item() == pytest.approx(0.2700,abs=1e-3)       
       assert ema_scores[3].item() == pytest.approx(0.3900,abs=1e-3)
       assert ema_scores[4].item() == pytest.approx(0.5,abs=1e-3)
       assert scores[0].item() == pytest.approx(0.0047,abs=1e-3)
       assert scores[1].item() == pytest.approx(0.0324,abs=1e-3)
       assert scores[2].item() == pytest.approx(0.0929,abs=1e-3)
       assert scores[3].item() == pytest.approx(0.2800,abs=1e-3)
       assert scores[4].item() == pytest.approx(0.5900,abs=1e-3)

    def test_great_score_variation(self):
       thisdevice = "cuda" if torch.cuda.is_available() else "cpu"
       uids = [1,2,3]
       rewards = torch.tensor([0.1, 0.5, 1.0],device=thisdevice)
       scores = torch.tensor([0.004455, 0.035550, 0.120000, 0.284445, 0.555550],device=thisdevice)
       ema_scores = torch.tensor([0.1,0.2,0.3,0.4,0.5],device=thisdevice)
       moving_average_alpha = 0.1
       device = "cuda"
       neurons = 5
       nonlinear_power = 3
       #print(f"Testing: ", rewards, uids)
       scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)
       #print(f"Testing great variation: ", scores, ema_scores)
       assert torch.isnan(ema_scores).any() == False
       assert torch.isnan(scores).any() == False
       assert ema_scores[0].item() == pytest.approx(0.1,abs=1e-3)
       assert ema_scores[1].item() == pytest.approx(0.1900,abs=1e-3)
       assert ema_scores[2].item() == pytest.approx(0.3200,abs=1e-3)       
       assert ema_scores[3].item() == pytest.approx(0.4600,abs=1e-3)
       assert ema_scores[4].item() == pytest.approx(0.5,abs=1e-3)
       assert scores[0].item() == pytest.approx(0.0038,abs=1e-3)
       assert scores[1].item() == pytest.approx(0.0261,abs=1e-3)
       assert scores[2].item() == pytest.approx(0.1246,abs=1e-3)
       assert scores[3].item() == pytest.approx(0.3702,abs=1e-3)
       assert scores[4].item() == pytest.approx(0.4754,abs=1e-3)

    def test_small_variation(self):
       thisdevice = "cuda" if torch.cuda.is_available() else "cpu"
       uids = [1,2,3]
       rewards = torch.tensor([0.285, 0.295, 0.32],device=thisdevice)
       scores = torch.tensor([0.174646, 0.183967, 0.193342, 0.213330, 0.234716],device=thisdevice)
       ema_scores = torch.tensor([0.29,0.295,0.3,0.31,0.32],device=thisdevice)
       moving_average_alpha = 0.1
       device = "cuda"
       neurons = 5
       nonlinear_power = 3
       scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)
       #print(f"Testing small variation: ", scores, ema_scores)
       assert torch.isnan(ema_scores).any() == False
       assert torch.isnan(scores).any() == False
       assert ema_scores[0].item() == pytest.approx(0.2900, abs=1e-3)
       assert ema_scores[1].item() == pytest.approx(0.2940, abs=1e-3)
       assert ema_scores[2].item() == pytest.approx(0.2995, abs=1e-3)
       assert ema_scores[3].item() == pytest.approx(0.3110, abs=1e-3)
       assert ema_scores[4].item() == pytest.approx(0.3200, abs=1e-3)
       assert scores[0].item() == pytest.approx(0.1748, abs=1e-3)
       assert scores[1].item() == pytest.approx(0.1821, abs=1e-3)
       assert scores[2].item() == pytest.approx(0.1926, abs=1e-3)
       assert scores[3].item() == pytest.approx(0.2156, abs=1e-3)
       assert scores[4].item() == pytest.approx(0.2349, abs=1e-3)

    def test_no_variation(self):
       thisdevice = "cuda" if torch.cuda.is_available() else "cpu"
       uids = [1,2,3]
       rewards = torch.tensor([0.5, 0.5, 0.5],device=thisdevice)
       scores = torch.tensor([0.004455, 0.035550, 0.120000, 0.284445, 0.555550],device=thisdevice)
       ema_scores = torch.tensor([0.1,0.2,0.3,0.4,0.5],device=thisdevice)
       moving_average_alpha = 0.1
       device = "cuda"
       neurons = 5
       nonlinear_power = 3
       scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)
       
       #print(f"Testing no variation: ", scores, ema_scores)
       assert torch.isnan(ema_scores).any() == False
       assert torch.isnan(scores).any() == False
       assert ema_scores[0].item() == pytest.approx(0.1,abs=1e-3)
       assert ema_scores[1].item() == pytest.approx(0.2300,abs=1e-3)
       assert ema_scores[2].item() == pytest.approx(0.3200,abs=1e-3)       
       assert ema_scores[3].item() == pytest.approx(0.4100,abs=1e-3)
       assert ema_scores[4].item() == pytest.approx(0.5,abs=1e-3)
       assert scores[0].item() == pytest.approx(0.0042,abs=1e-3)
       assert scores[1].item() == pytest.approx(0.0507,abs=1e-3)
       assert scores[2].item() == pytest.approx(0.1366,abs=1e-3)
       assert scores[3].item() == pytest.approx(0.2873,abs=1e-3)
       assert scores[4].item() == pytest.approx(0.5211,abs=1e-3)


    def update_scores(self, rewards: torch.FloatTensor, uids: List[int]):
        #return torch.FloatTensor([0.4,0.5,0.6])
        rewards = torch.nan_to_num(rewards, 0.0)
        rewards = torch.clamp(rewards, min=0.0, max=1.0)
        return rewards
