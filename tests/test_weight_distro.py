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
import numpy as np
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
    tied_indices = np.array([])
    if original_scores_list is not None and original_scores_list.size != 0 and not np.isnan(original_scores_list).any():
        # Identify unique scores and their counts
        unique_weights, counts = np.unique(original_scores_list, return_counts=True)
        ties = unique_weights[counts > 1]

        # Collect all indices of tied scores
        tied_indices_list = []
        for tie in ties:
            if tie == 0:
                continue
            tied_indices_list.extend(np.where(original_scores_list == tie)[0].tolist())
        
        tied_indices = np.array(tied_indices_list)
    return tied_indices

def get_real_weights():
    metagraph = bt.metagraph(33, lite = False)
    otf_weights = metagraph.W[63]

    stakes = metagraph.S
    weights = metagraph.W
    
    high_stake_indices = np.nonzero(stakes > 20000)[0].tolist()

    # Initialize the stake-weighted average array
    stake_weighted_average = np.zeros_like(weights[0])

    # Accumulate stake-weighted values for each index across all high stake indices
    for index in high_stake_indices:
        stake = stakes[index]
        weight_array = weights[index]

        for i, weight in enumerate(weight_array):
            stake_weighted_average[i] += weight * stake
    
    # Normalize the stake-weighted average
    total_stake_weight = sum(stakes[index] for index in high_stake_indices)
    if total_stake_weight > 0:
        stake_weighted_average /= total_stake_weight
    
    return stake_weighted_average,otf_weights

def print_stats(scores_list):
    if scores_list is None or scores_list.size == 0:
        print("Original List is None or length zero")
        return
    if np.isnan(scores_list).any():
        print("Original contains nan")
        return
    
    num_uids = len(scores_list)
    sorted_uids = np.argsort(scores_list)[::-1]

    print(f"Total UIDs : {num_uids}")
    print(f"Min Weight: {scores_list[sorted_uids[num_uids-1]]}")
    print(f"Max Weight: {scores_list[sorted_uids[0]]}")
    print(f"Ordered UIDs: {sorted_uids}")
    print("\n\n")


@pytest.mark.asyncio
async def test_full():
    verbose = True
    plotting = True
    # Config variables
    c.set('system', 'mode', 'test')

    vl = ValidatorLib()
    el = Evaluator()
    test_mode = True
    start_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    stake_weighted_average,otf_weights = get_real_weights()
    
    test_score_groups = [
        {"title": "normalized_scores", "scores": np.array([0.6, 0.7, 0.16, 0.01, 0.1, 0.2, 0.2, 0.05, 0.05, 0.1], dtype=np.float32)},
        {"title": "normalized_scores some zeros1", "scores": np.array([0.0,0.0,0.0,0.0,0.1, 0.2, 0.15, 0.05, 0.1, 0.2, 0.2, 0.05, 0.05, 0.1], dtype=np.float32)},
        {"title": "normalized_scores some zeros2", "scores": np.array([0.0, 0.1,0.0, 0.2, 0.15, 0.0, 0.05, 0.1, 0.0, 0.2, 0.2, 0.0, 0.05, 0.0, 0.05, 0.0, 0.1], dtype=np.float32)},
        {"title": "uniform_distribution", "scores": np.array([0.05] * 20, dtype=np.float32)},
        {"title": "empty_scores", "scores": np.array([], dtype=np.float32)},
        {"title": "nan_values", "scores": np.array([float('nan')] * 10, dtype=np.float32)},
        {"title": "none_scores", "scores": None},
        {"title": "high_variance", "scores": np.array([0.01, 0.99, 0.2, 0.8, 0.15, 0.85, 0.3, 0.7, 0.4, 0.6], dtype=np.float32)},
        {"title": "low_variance", "scores": np.array([0.5, 0.51, 0.49, 0.52, 0.48, 0.53, 0.47, 0.54, 0.46, 0.55], dtype=np.float32)},
        {"title": "all_zero_scores", "scores": np.array([0.0, 0.0,0.0, 0.0,0.0, 0.0,0.0, 0.0,0.0, 0.0], dtype=np.float32)},
        {"title": "single_score", "scores": np.array([1.0] + [0.0] * 9, dtype=np.float32)},
        {"title": "random_50", "scores": np.random.rand(50).astype(np.float32)},
        {"title": "random_100", "scores": np.random.rand(100).astype(np.float32)},
        {"title": "OTF Weights", "scores": otf_weights},
        {"title": "real stake-weighted-average", "scores": stake_weighted_average},
    ]

    for test_score_group in test_score_groups:
        print("\n\n----------------------------")
        print(f"\033[1mRunning test: {test_score_group['title']}\033[0m")
        print("----------------------------")

        original_scores_list = test_score_group['scores']

        #Print Stats
        print("Printing Test Case stats")
        print_stats(original_scores_list)

        if original_scores_list is not None:
            #sort original list
            original_ranking = np.argsort(-original_scores_list)
            
        #find tied indices to identify intentional shuffling later on
        tied_indices = get_tied_indices(original_scores_list)
        original_zero_indices = np.where(original_scores_list == 0)[0]
        
        print("------------")
        print("calculating raw_weights using ValidatorLibFunction")

        #calculate raw weights using validatorLib function
        raw_weights = vl.get_raw_weights(original_scores_list)
        print("\n------------")
        print("Printing Result stats")
        print_stats(raw_weights)

        if raw_weights is not None:

            print(f"Found Tied Indices: {tied_indices}")

            #create new ranking
            new_ranking = np.argsort(-raw_weights)
            new_zero_indices = np.where(raw_weights == 0)[0]

            # Sort both lists and confirm that new_zero_indices == original_zero_indices
            sorted_original_zero_indices = np.sort(original_zero_indices)
            sorted_new_zero_indices = np.sort(new_zero_indices)

            if np.array_equal(sorted_original_zero_indices, sorted_new_zero_indices):
                print("Zero indices match between original and new weights.")
            else:
                print("Mismatch in zero indices between original and new weights.")
                print(f"Original zero indices: {sorted_original_zero_indices}")
                print(f"New zero indices: {sorted_new_zero_indices}")

            print("Comparing new ordered UIDS to original Ordered UIDs to confirm raw_weights were calculated properly.")
            print("If out of order indices are found, they will be either due to Tie-shuffling, or due to unexpected error. Print will specify below:")
            print("\n")
            # Compare the new ranking to the original ranking
            for rank, (original_uid, new_uid) in enumerate(zip(original_ranking, new_ranking)):
                if np.isnan(original_uid) or np.isnan(new_uid):
                    print(f"Error: NaN detected at rank {rank}. Original UID: {original_uid}, New UID: {new_uid}")
                    continue
                if original_uid != new_uid:
                    if original_uid in tied_indices:
                        print(f"Rank {rank}: Original UID {original_uid} -> New UID {new_uid} (Shuffle due to Tied index)")
                    else:
                        print(f"Rank {rank}: Original UID {original_uid} -> New UID {new_uid} (Unexpected change)")
            
            
            if plotting:
                folder_name = f"plots_{start_time}"
                os.makedirs(folder_name, exist_ok=True)

                # Plot original scores list
                plt.figure(figsize=(10, 6))
                plt.plot(range(len(original_scores_list)), np.array(original_scores_list), marker='o', linestyle='-', color='g')
                plt.xlabel('Index')
                plt.ylabel('Score Value')
                plt.title(f"Original Scores List {test_score_group['title']}")
                plt.grid(True)
                subfolder_before = os.path.join(folder_name, f"{test_score_group['title']}_before")
                os.makedirs(subfolder_before, exist_ok=True)
                plt.savefig(os.path.join(subfolder_before, f"original_scores_{test_score_group['title']}.png"))
                plt.close()

                # Plot original scores list in descending order
                ordered_original_scores = np.array(original_scores_list)[original_ranking]
                plt.figure(figsize=(10, 6))
                plt.plot(range(len(ordered_original_scores)), ordered_original_scores, marker='o', linestyle='-', color='g')
                plt.xlabel('Index')
                plt.ylabel('Score Value')
                plt.title(f"Original Scores List Descending {test_score_group['title']}")
                plt.grid(True)
                plt.savefig(os.path.join(subfolder_before, f"original_scores_descending_{test_score_group['title']}.png"))
                plt.close()

                # Plot raw weights
                plt.figure(figsize=(10, 6))
                plt.plot(range(len(raw_weights)), np.array(raw_weights), marker='o', linestyle='-', color='b')
                plt.xlabel('Index')
                plt.ylabel('Weight Value')
                plt.title(f"Raw Weights {test_score_group['title']}")
                plt.grid(True)
                subfolder_after = os.path.join(folder_name, f"{test_score_group['title']}_after")
                os.makedirs(subfolder_after, exist_ok=True)
                plt.savefig(os.path.join(subfolder_after, f"raw_weights_{test_score_group['title']}.png"))
                plt.close()

                # Plot raw weights in descending order
                ordered_raw_weights_final = np.copy(raw_weights)[new_ranking]
                plt.figure(figsize=(10, 6))
                plt.plot(range(len(ordered_raw_weights_final)), ordered_raw_weights_final, marker='o', linestyle='-', color='b')
                plt.xlabel('Index')
                plt.ylabel('Weight Value')
                plt.title(f"Raw Weights Descending {test_score_group['title']}")
                plt.grid(True)
                plt.savefig(os.path.join(subfolder_after, f"raw_weights_descending_{test_score_group['title']}.png"))
                plt.close()
            else: 
                print("\n------------")
                print("Skipping graphing step")
        else:
            raw_weights = None
            new_ranking = None
            print("Error generating raw weights. Skipping setting weights for now\n\n")


        #Assert Statements
        if original_scores_list is None or original_scores_list.size == 0:
            assert raw_weights is None, "Expected raw_weights to be None"
            assert new_ranking is None, "Expected new_ranking to be None"
        else:
            if original_scores_list is not None and np.isnan(original_scores_list).any():
                assert raw_weights is None, "Expected raw_weights to be None"
                assert new_ranking is None, "Expected new_ranking to be None"
            else:
                assert len(raw_weights) == len(original_scores_list), "Expected Length of output to be same as input"
                if np.sum(original_scores_list) > 0:
                    assert np.isclose(np.sum(raw_weights), 1.0), "Expected original_scores_list to sum to 1"
                else:
                    assert np.isclose(np.sum(raw_weights), 0.0), "Expected Tensor to equal 0"
                if len(tied_indices) == 0:
                    assert np.array_equal(original_ranking, new_ranking), "Original ranking and new ranking should be the same when there are no tied indices."

            print("\n\n")

