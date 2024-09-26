import pytest
import random
import pprint
import numpy as np


from conversationgenome.ConfigLib import c
from conversationgenome.utils.Utils import Utils

from conversationgenome.validator.ValidatorLib import ValidatorLib
from conversationgenome.validator.evaluator import Evaluator
from conversationgenome.analytics.WandbLib import WandbLib
from conversationgenome.mock.MockBt import MockBt

verbose = True

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()



class MockAxon:
    uuid = "a"
    hotkey = ""


class MockResponse:
    responses = {}
    responses = {}
    cgp_output = None
    axon = None
    test_tag_groups = {}

    def __init__(self):
        self.axon = MockAxon()


def inject_scores(original_list, new_scores):
    if len(original_list) != len(new_scores):
        raise ValueError("The number of new scores must match the number of elements in the original list")
    
    for item, new_score in zip(original_list, new_scores):
        item['final_miner_score'] = new_score
    
    return original_list

@pytest.mark.asyncio
async def test_full():
    verbose = True
    # Config variables
    c.set('system', 'mode', 'test')

    vl = ValidatorLib()
    el = Evaluator()
    test_mode = True

    test_score_groups = [
        {"title": "All different, descending", "scores":[0.5, 0.4, 0.3]},
        {"title": "All different, ascending", "scores":[0.3, 0.4, 0.5]},
        {"title": "All different, shuffled", "scores":[0.5, 0.3, 0.8]},
        {"title": "one Three-way tie for first", "scores":[0.5, 0.5, 0.5]},
        {"title": "two Three-way tie for first", "scores":[0.5, 0.5, 0.5]},
        {"title": "three Three-way tie for first", "scores":[0.5, 0.5, 0.5]},
        {"title": "Two way tie for first", "scores":[0.5, 0.3, 0.5]},
        {"title": "Two way tie for second", "scores":[0.4, 0.4, 0.5]},
        {"title": "all 0s", "scores":[0.0, 0.0, 0.0]},
        {"title": "tie for first with zero", "scores":[0.5, 0.5, 0.0]},
        {"title": "two zeros", "scores":[0.5, 0.0, 0.0]},
        {"title": "one zeros", "scores":[0.4, 0.5, 0.0]},
        {"title": "non-number character", "scores":["abc", 0.0, 0.0]},
        {"title": "single numpy float", "scores":[np.float64(.314), 0.0, 0.0]},
        {"title": "all three numpy floats", "scores":[np.float64(.314), np.float64(.312), np.float64(.310)]},
        {"title": "long decimals", "scores":[0.00000000000000000000001, 0.00000000000000000000002, 0.00000000000000000000003]},       
    ]
    original_list = [
        {'adjustedScore': 0.0, 'final_miner_score': 0.9176751571093553, 'hotkey': '123', 'uid': 1, 'uuid': 'abc'},
        {'adjustedScore': 0.0, 'final_miner_score': 0.9177323391819007, 'hotkey': '123', 'uid': 2, 'uuid': 'abc'},
        {'adjustedScore': 0.0, 'final_miner_score': 0.9177323391819007, 'hotkey': '123', 'uid': 3, 'uuid': 'abc'}
    ]

    

    for score in test_score_groups:
        scores_list = score['scores']
        test_list = inject_scores(original_list, scores_list)

        print(f"Running test: {score['title']}")
        result = await vl.assign_fixed_scores(test_list)

    
        if verbose:
            print(f"{score['title']} | Final Scores:\n")
            pprint.pprint(result)
            print('\n')
            



