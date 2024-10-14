import pytest
import random


from conversationgenome.ConfigLib import c
from conversationgenome.utils.Utils import Utils

from conversationgenome.validator.ValidatorLib import ValidatorLib
from conversationgenome.validator.evaluator import Evaluator
from conversationgenome.analytics.WandbLib import WandbLib
from conversationgenome.mock.MockBt import MockBt
import matplotlib.pyplot as plt
from datetime import datetime
import os
import torch

verbose = True

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()


def get_tied_indices(original_scores_list):
    tied_indices = torch.tensor([])
    if original_scores_list is not None and original_scores_list.numel() != 0 and not torch.isnan(original_scores_list).any():
        # Identify unique scores and their counts
        unique_weights, counts = torch.unique(original_scores_list, return_counts=True)
        ties = unique_weights[counts > 1]

        # Collect all indices of tied scores
        tied_indices_list = []
        for tie in ties:
            if tie == 0:
                continue
            tied_indices_list.extend((original_scores_list == tie).nonzero(as_tuple=True)[0].tolist())
        
        tied_indices = torch.tensor(tied_indices_list)
        print(f"Tied Indices: {tied_indices}")
    return tied_indices

def get_real_weights():
    metagraph = bt.metagraph(33, lite = False)
    otf_weights = metagraph.W[63]

    stakes = metagraph.S
    weights = metagraph.W
    
    high_stake_indices = (stakes > 20000).nonzero(as_tuple=True)[0].tolist()

    # Initialize the stake-weighted average tensor
    stake_weighted_average = torch.zeros_like(weights[0])

    # Accumulate stake-weighted values for each index across all high stake indices
    for index in high_stake_indices:
        stake = stakes[index].item()
        weight_tensor = weights[index]

        for i, weight in enumerate(weight_tensor):
            stake_weighted_average[i] += weight * stake
    
    # Normalize the stake-weighted average
    total_stake_weight = sum(stakes[index].item() for index in high_stake_indices)
    if total_stake_weight > 0:
        stake_weighted_average /= total_stake_weight
    
    return stake_weighted_average,otf_weights

@pytest.mark.asyncio
async def test_full():
    verbose = True
    plotting = False
    # Config variables
    c.set('system', 'mode', 'test')

    vl = ValidatorLib()
    el = Evaluator()
    test_mode = True


    stake_weighted_average,otf_weights = get_real_weights()
    
    test_score_groups = [
        {"title": "normalized_scores", "scores": torch.tensor([0.1, 0.2, 0.15, 0.05, 0.1, 0.2, 0.2, 0.05, 0.05, 0.1], dtype=torch.float32)},
        {"title": "uniform_distribution", "scores": torch.tensor([0.05] * 20, dtype=torch.float32)},
        {"title": "empty_scores", "scores": torch.tensor([], dtype=torch.float32)},
        {"title": "nan_values", "scores": torch.tensor([float('nan')] * 10, dtype=torch.float32)},
        {"title": "none_scores", "scores": None},
        {"title": "high_variance", "scores": torch.tensor([0.01, 0.99, 0.2, 0.8, 0.15, 0.85, 0.3, 0.7, 0.4, 0.6], dtype=torch.float32)},
        {"title": "low_variance", "scores": torch.tensor([0.5, 0.51, 0.49, 0.52, 0.48, 0.53, 0.47, 0.54, 0.46, 0.55], dtype=torch.float32)},
        {"title": "all_zero_scores", "scores": torch.tensor([0.0] * 10, dtype=torch.float32)},
        {"title": "single_score", "scores": torch.tensor([1.0] + [0.0] * 9, dtype=torch.float32)},
        {"title": "random_50", "scores": torch.tensor(torch.rand(50), dtype=torch.float32)},
        {"title": "random_100", "scores": torch.tensor(torch.rand(100), dtype=torch.float32)},
        {"title": "OTF Weights", "scores": otf_weights},
        {"title": "real stake-weighted-average", "scores": stake_weighted_average},
    ]

    for test_score_group in test_score_groups:
        print(f"Running test: {test_score_group['title']}")

        original_scores_list = test_score_group['scores']

        if original_scores_list is not None:
            #sort original list
            original_ranking = torch.argsort(original_scores_list, descending=True)
            
        #find tied indices to identify intentional shuffling later on
        tied_indices = get_tied_indices(original_scores_list)

        #calculate raw weights using validatorLib function
        raw_weights = vl.get_raw_weights(original_scores_list)

        if raw_weights is not None:

            #create new ranking
            new_ranking = torch.argsort(raw_weights.clone(), descending=True)

            # Compare the new ranking to the original ranking
            for rank, (original_uid, new_uid) in enumerate(zip(original_ranking, new_ranking)):
                if original_uid != new_uid:
                    if original_uid in tied_indices:
                        print(f"Rank {rank}: Original UID {original_uid} -> New UID {new_uid} (Shuffle due to Tied index)")
                    else:
                        print(f"Rank {rank}: Original UID {original_uid} -> New UID {new_uid} (Unexpected change)")
            
            if plotting:
                # Order the raw weights and create a new tensor ordered_raw_weights_final
                ordered_indices = new_ranking.clone()
                ordered_raw_weights_final = raw_weights.clone()[ordered_indices]

                # Plot the ordered raw weights
                plt.figure(figsize=(10, 6))
                plt.plot(range(len(ordered_raw_weights_final)), ordered_raw_weights_final.cpu().numpy(), marker='o', linestyle='-', color='b')            
                plt.xlabel('UID Index')
                plt.ylabel('Weight Value')
                # Create a timestamped folder for saving the plot
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                folder_name = f"weight_distribution_{timestamp}"
                os.makedirs(folder_name, exist_ok=True)

                # Save the plot to the folder
                plt.title(f"Ordered Raw Weights by UID {test_score_group['title']}")
                plt.grid(True)
                plt.savefig(os.path.join(folder_name, f"ordered_raw_weights_{test_score_group['title']}.png"))
                plt.close()
        else:
            raw_weights = None
            new_ranking = None


            #Assert Statements
            if original_scores_list is None or original_scores_list.numel() == 0:
                raw_weights = None
                new_ranking = None

            if len(tied_indices) == 0:
                assert torch.equal(original_ranking, new_ranking), "Original ranking and new ranking should be the same when there are no tied indices."


            #print(f"{test_score_group['title']}")
            #print("Original Order and Weights:")
            #for rank, uid in enumerate(original_ranking):
                #print(f"Rank {rank}: UID {uid}, Weight {original_scores_list[uid].item()}")
            
            #print("\nNew Order and Weights:")
            #for rank, uid in enumerate(new_ranking):
                #print(f"Rank {rank}: UID {uid}, Weight {raw_weights[uid].item()}")
            print("\n\n")
        else:
            print("Error generating raw weights. Skipping setting weights for now\n\n")


