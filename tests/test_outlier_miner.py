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


def print_stats(scores, ema_scores, unavailable_uids=None, iteration=-100, stop_point= ""):
    print("\n")
    print(f"\033[92m\tstop point: {stop_point} iteration: {iteration}\033[0m")
    print(f"\tEMA SCORES: \n\t{ema_scores}")
    print(f"\tSCORES: \n\t{scores}")
    for unavailable_uid in unavailable_uids:
        print(f"\033[91m\tUnavailable UID {unavailable_uid} - Score: {scores[unavailable_uid]}, EMA Score: {ema_scores[unavailable_uid]}\033[0m")

class TemplateEmaTestCase(unittest.TestCase):
    verbose = True
    vl= None

    def setUp(self):
        self.vl=ValidatorLib()
        self.vl.verbose=True
        pass

    def test_bug_and_fix(self):
        iterations = 10000
        unavailable_uids = [0,9]
        stop_points = [round(iterations * 0.1), round(iterations * 0.5),round(iterations * 0.75)]
        moving_average_alpha = 0.1
        device = "cuda"
        neurons = 5
        nonlinear_power = 3

        #iterate once without fix to show problem persisting
        use_fix = False
        j=0
        print("\n---------------")
        print("\033[94mTesting Bug Introduction and Fix\033[0m")
        print(f"\033[94miterations: {iterations}\033[0m")
        print(f"\033[94mstop points: {stop_points}\033[0m")
        print(f"\033[94mUnavailable UIDs: {unavailable_uids}\033[0m")
        while j<2:
            print(f"\033[94mRunning {iterations} Iterations with use_fix == {use_fix}\033[0m")
            i=0
            scores = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            ema_scores = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            print_stats(scores, ema_scores, unavailable_uids, 0, "start")
            while i <= iterations:
                uids = []
                rewards = []
                if i in stop_points:
                    stop_point = stop_points.index(i) + 1
                    print_stats(scores, ema_scores, unavailable_uids, i, str(stop_point))
                    if stop_point == 1:
                        print("\n\n\tINTRODUCING BUG - UPDATING UID 0\n")
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

                if use_fix:
                    #update with fix
                    scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power, unavailable_uids)
                else:
                    #update without fix
                    scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power)

                i+=1

            print(f"Completed iterations with use_fix == {use_fix}")
            print_stats(scores, ema_scores, unavailable_uids, iterations, "end")
            #update use_fix to use the fix next time through
            use_fix = True
            j+=1
            print("\n")


    def test_preexisting_bug(self):
        print(f"\n\n")
        print("---------------")
        print("\033[94mTesting Pre-existing bug\033[0m")
        iterations = 1000
        unavailable_uids = [0,9]
        stop_points = [round(iterations * 0.1), round(iterations * 0.5),round(iterations * 0.75)]
        moving_average_alpha = 0.1
        device = "cuda"
        neurons = 5
        nonlinear_power = 3
        i=0
        scores = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)
        ema_scores = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)

        print(f"\033[94miterations: {iterations}\033[0m")
        print(f"\033[94mstop points: {stop_points}\033[0m")
        print(f"\033[94mUnavailable UIDs: {unavailable_uids}\033[0m")
        print_stats(scores, ema_scores, unavailable_uids, 0, "start")

        while i <= iterations:
            uids = []
            rewards = []
            if i in stop_points:
                stop_point = stop_points.index(i) + 1
                print_stats(scores, ema_scores, unavailable_uids, i, str(stop_point))
                print("\n")
                i+=1
                continue
            else:
                uids = random.sample(range(1, 9), 3)
                rewards = np.array([random.uniform(0.35, 0.55) for _ in range(3)], dtype=np.float32)

            scores, ema_scores = self.vl.update_scores(rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power, unavailable_uids)

            i+=1

        print(f"Completed iterations")
        print_stats(scores, ema_scores, unavailable_uids, iterations, "end")
        for unavailable_uid in unavailable_uids:
            print(f"Unavailable UID {unavailable_uid} - Score: {scores[unavailable_uid]}, EMA Score: {ema_scores[unavailable_uid]}")