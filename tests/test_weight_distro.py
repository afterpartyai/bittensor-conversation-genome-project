import pytest
import random


from conversationgenome.ConfigLib import c
from conversationgenome.utils.Utils import Utils

from conversationgenome.validator.ValidatorLib import ValidatorLib
from conversationgenome.validator.evaluator import Evaluator
from conversationgenome.analytics.WandbLib import WandbLib
from conversationgenome.mock.MockBt import MockBt
import torch

verbose = True

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()




@pytest.mark.asyncio
async def test_full():
    verbose = True
    # Config variables
    c.set('system', 'mode', 'test')

    vl = ValidatorLib()
    el = Evaluator()
    test_mode = True

    test_score_groups = [
        {"title": "normalized_scores", "scores": torch.tensor([0.1, 0.2, 0.15, 0.05, 0.1, 0.2, 0.2], dtype=torch.float32)},
        {"title": "uniform_distribution", "scores": torch.tensor([0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05], dtype=torch.float32)},
        {"title": "empty_scores", "scores": torch.tensor([], dtype=torch.float32)},
        {"title": "nan_values", "scores": torch.tensor([float('nan'), float('nan')], dtype=torch.float32)},
        {"title": "none_scores", "scores": None},
        {"title": "high_variance", "scores": torch.tensor([0.01, 0.99], dtype=torch.float32)},
        {"title": "low_variance", "scores": torch.tensor([0.5, 0.5], dtype=torch.float32)},
        {"title": "all_zero_scores", "scores": torch.tensor([0.0, 0.0, 0.0], dtype=torch.float32)},
        {"title": "single_score", "scores": torch.tensor([1.0], dtype=torch.float32)},
        {"title": "negative_scores", "scores": torch.tensor([-0.5, -0.5], dtype=torch.float32)},
    ]

    for test_score_group in test_score_groups:
        original_scores_list = test_score_group['scores']
        original_ranking = torch.argsort(original_scores_list, descending=True)

        print(f"Running test: {test_score_group['title']}")

        raw_weights = await vl.get_raw_weights(original_scores_list)
        if raw_weights is None or raw_weights.numel() == 0:
            new_ranking = torch.argsort(raw_weights, descending=True)

            if verbose:
                print(f"{test_score_group['title']} \nOriginal Order: {original_ranking}. \nNew Order: {new_ranking}")
        else:
            print("Error generating raw weights. Skipping setting weights for now")


