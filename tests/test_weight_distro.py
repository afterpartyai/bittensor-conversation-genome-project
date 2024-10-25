import pytest
import random

CYAN = "\033[96m" # field color
GREEN = "\033[92m" # indicating success
RED = "\033[91m" # indicating error
YELLOW = '\033[0;33m'
COLOR_END = '\033[m'
BOLD = '\033[1m'
BOLD_END = '\033[0m'
DIVIDER = YELLOW + ('_' * 120) + COLOR_END


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

def get_tied_scores_indices(original_scores):
    scores = {}
    outScores = {}
    outScoresList = []
    if original_scores is None:
        original_scores = np.array([], dtype=np.float32)
    #if original_scores is not None and original_scores.size != 0 and not np.isnan(original_scores).any():
    #    original_scores = []
    for idx, score in enumerate(original_scores):
        if not score in scores:
            scores[score] = []
        scores[score].append(idx)
    for key, val in scores.items():
        if len(val) < 2:
            continue
        outScores[key] = val
        outScoresList += val
    return (outScores, outScoresList)


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

def print_stats(scores_list, title=None):
    if scores_list is None or scores_list.size == 0:
        print("Original List is None or length zero")
        return
    if np.isnan(scores_list).any():
        print("Original contains nan")
        return

    num_uids = len(scores_list)
    unsorted_uids = np.arange(0, num_uids)
    sorted_uids = np.argsort(scores_list)[::-1]

    out = f'{YELLOW}{title}{COLOR_END}'
    out += f" Total UIDs : {CYAN}{num_uids}{COLOR_END} | "
    out += f"Min Weight: {CYAN}{scores_list[sorted_uids[num_uids-1]]}{COLOR_END} | "
    out += f"Max Weight: {CYAN}{scores_list[sorted_uids[0]]}{COLOR_END} | "
    scoresStr = ""
    for idx, curScore in enumerate(scores_list):
        scoresStr += f"{CYAN}{idx}{COLOR_END}:{curScore} "
    #print(f"Unordered UIDs: {unsorted_uids}")
    #out += f"Scores: {scoresStr} "
    out += f"Ordered UIDs: {CYAN}{sorted_uids}{COLOR_END} "
    print(out+"\n")


@pytest.mark.asyncio
async def test_full():
    verbose = False
    plotting = False
    # Config variables
    c.set('system', 'mode', 'test')

    vl = ValidatorLib()
    el = Evaluator()
    test_mode = True
    start_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    if False:
        stake_weighted_average,otf_weights = get_real_weights()
        stake_weighted_average = stake_weighted_average[0:10]
        otf_weights = otf_weights[0:10]
    else:
        stake_weighted_average = np.array([0.00482204, 0.00196788, 0.00187665, 0.00423791, 0.00458174, 0.00443221, 0.00473241, 0.00202872, 0.00449199, 0.00445989])
        otf_weights = np.array([0.00396116, 0.00238071, 0.00230142, 0.00399894, 0.00505707, 0.00400471, 0.00401076, 0.00256747, 0.00390845, 0.00391227])

    #print("WEIGHTS",stake_weighted_average, otf_weights, type(np.array([0.1, 0.2])))

    test_score_groups = [
        {"title": "normalized_scores", "scores": np.array([0.0, 0.7, 0.2, 0.15, 0.05, 0.1, 0.2, 0.05, 0.05, 0.1], dtype=np.float32)},
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
    epsilons = [1e-12, 0]
    epsilons = [0]

    for test_score_group in test_score_groups:
        print("\n"+DIVIDER)
        print(f"{BOLD}Running test: {test_score_group['title']}{BOLD_END}")
        print("----------------------------")
        original_scores_list = test_score_group['scores']

        #Print Stats
        print_stats(original_scores_list, title="Original Weight Scores")

        if original_scores_list is not None:
            #sort original list
            original_ranking = np.argsort(-original_scores_list)

        # Get indices of tied scores to identify intentional shuffling later on
        #tied_indices = get_tied_indices(original_scores_list)
        (tiedScoresDict, tied_indices) = get_tied_scores_indices(original_scores_list)
        print(f"Tied scores: {CYAN}{tiedScoresDict}{COLOR_END} | {len(tied_indices)} --> {tied_indices}")


        #calculate raw weights using validatorLib function
        raw_weights = vl.get_raw_weights(original_scores_list)
        #for raw_weight in raw_weights:
        #    print(f"{raw_weight}")
        print_stats(raw_weights, title="Calculating Raw Weight Scores from vl.get_raw_weights")

        if raw_weights is not None:
            #create new ranking
            new_ranking = np.argsort(-raw_weights)
            print(f"original_ranking = {original_ranking}, new_ranking={new_ranking} raw_weights={raw_weights}")

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
                        print(f"Rank {rank}:  {original_uid} -> {new_uid} (original->new) (Shuffle due to Tied score)")
                    else:
                        print(f"Rank {rank}: Original UID {original_uid} -> New UID {new_uid} (Unexpected change)")

            if False:
                originalScores = np.array([0.0, 0.035550, 0.120000, 0.284445, 0.555550], dtype=np.float32)
                originalEma_scores = np.array([0.0,0.2,0.3,0.4,0.5], dtype=np.float32)
                uids = [1,2,3]
                rewards = np.array([0.5, 0.5, 0.5], dtype=np.float32)
            else:
                originalScores = original_scores_list
                originalEma_scores = original_scores_list
                uids = []
                rewards = np.array([], dtype=np.float32)
                for i in range(len(originalScores)-1):
                    uids.append(i+1)
                    rewards = np.append(rewards, 0.2 + (0.05 * i % 1.0))

            moving_average_alpha = 0.1
            neurons = 5
            nonlinear_power = 3
            for epsilon in epsilons:
                print(f"\n{GREEN}Updating scores with epsilon {epsilon}...{COLOR_END}")
                updatedScores, updatedEma_scores = vl.update_scores(
                    rewards=rewards,
                    uids=uids,
                    ema_scores=originalEma_scores,
                    scores=originalScores,
                    eps=epsilon,
                    moving_average_alpha=moving_average_alpha,
                    neurons=neurons,
                    nonlinear_power=nonlinear_power
                )
                print(f"\n{GREEN}Done updating scores {epsilon}.{COLOR_END}")
                print(f"Original scores.   scores:{originalScores} ({len(originalScores)}) |  ema_scores: {originalEma_scores} ({len(originalEma_scores)})")
                print(f"Updated scores. scores:{updatedScores} ({len(updatedScores)}) | ema_scores: {updatedEma_scores}  ({len(updatedEma_scores)})")

            if plotting:
                self.plotScores(original_scores_list, raw_weights)
            else:
                if verbose:
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
        break

    def plotScores(self, original_scores_list, raw_weights):
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

