import pytest
import random
import unittest
import torch

from conversationgenome.ConfigLib import c
from conversationgenome.utils.Utils import Utils
#
#from conversationgenome.validator.ValidatorLib import ValidatorLib
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

    def setUp(self):
        pass

    def test_nan(self):
       uids = [1,2,3]
       ft = torch.FloatTensor([0.1, float('nan') ,0.3])
       assert torch.isnan(ft).any() == True
       print(f"Testing: ", ft, uids)
       ema_scores = self.update_scores(ft, uids)
       assert torch.isnan(ema_scores).any() == False
       assert ema_scores[0] == 0.1
       assert ema_scores[1] == 0.0
       assert ema_scores[2] == 0.3

    def test_out_of_range(self):
       uids = [1,2,3]
       ft = torch.FloatTensor([10.1, 0.2 ,-0.3])
       print(f"Testing: ", ft, uids)
       ema_scores = self.update_scores(ft, uids)
       assert torch.isnan(ema_scores).any() == False
       assert ema_scores[0] == 1.0
       assert ema_scores[1] == 0.2
       assert ema_scores[2] == 0.0



    def update_scores(self, rewards: torch.FloatTensor, uids: List[int]):
        #return torch.FloatTensor([0.4,0.5,0.6])
        return torch.nan_to_num(rewards, 0.0)