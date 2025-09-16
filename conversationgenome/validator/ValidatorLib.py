verbose = False

import json
import os
from typing import Any, Optional

import numpy as np

from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.mock.MockBt import MockBt
from conversationgenome.task.TaskLib import TaskLib
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.task_bundle.TaskBundleLib import TaskBundleLib

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()

if c.get('env', 'FORCE_LOG') == 'debug':
    bt.logging.enable_debug(True)
elif c.get('env', 'FORCE_LOG') == 'info':
    bt.logging.enable_default(True)


class ValidatorLib:
    mode = "test"  # test|local_llm|openai|anthropic
    hotkey = "v1234"
    verbose = False
    llml = LlmLib()
    readyai_api_key = None

    def __init__(self):
        super(ValidatorLib, self).__init__()
        self.read_api_key()

    def read_api_key(self):
        fail_message = "WARNING: You have not generated a ReadyAI Conversation Server API key. Starting on October 7th, 2024, you will no longer be able to request conversations from the ReadyAI Conversation server without an API Key. For instructions on how to generate your key, read the documentation in docs/generate-validator-api-key.md"
        fname = "readyai_api_data.json"
        if not os.path.isfile(fname):
            bt.logging.warning(f"{fail_message} -- Missing file")
            return
        try:
            f = open(fname)
            json_str = f.read()
            f.close()
        except Exception as e:
            bt.logging.warning(f"{fail_message} {e} -- Error reading file")
            return
        try:
            data = json.loads(json_str)
        except Exception as e:
            bt.logging.warning(f"{fail_message} {e} -- Error parsing file")
            return
        self.readyai_api_key = data['api_key']

    async def reserve_task_bundle(self) -> Optional[TaskBundle]:
        # Validator requests a full conversation from the API
        task_bundle: TaskBundle = await self.get_task_bundle()

        if task_bundle:
            bt.logging.info(f"Reserved task bundle.")
            return task_bundle
        else:
            bt.logging.error(f"ERROR:9879432: No task bundle returned from API. Aborting.")

        return None

    async def get_task_bundle(self) -> Optional[TaskBundle]:
        hotkey = self.hotkey

        if not self.readyai_api_key:
            self.read_api_key()

        tbl = TaskBundleLib()
        raw_task_data: TaskBundle = await tbl.get_task_bundle(hotkey, api_key=self.readyai_api_key)

        return raw_task_data

    async def put_task(self, *, hotkey: str, task_bundle_id: str, task_id: str, neuron_type: str, batch_number: int, data: Any) -> None:
        tl = TaskLib()
        await tl.put_task(
            hotkey=hotkey,
            task_bundle_id=task_bundle_id,
            task_id=task_id,
            neuron_type=neuron_type,
            batch_number=batch_number,
            data=data,
        )

    def update_scores(self, rewards, uids, ema_scores, scores, moving_average_alpha, device, neurons, nonlinear_power):
        if isinstance(uids, np.ndarray):
            uids_array = np.copy(uids)
        else:
            uids_array = np.array(uids, dtype=np.int64)

        # Ensure float32 dtype for consistency with PyTorch
        rewards = np.array(rewards, dtype=np.float32)
        ema_scores = np.array(ema_scores, dtype=np.float32)

        # NaN handling
        if np.isnan(rewards).any():
            if self.verbose:
                bt.logging.warning(f"NaN values detected in rewards: {rewards}")
            rewards = np.nan_to_num(rewards, 0)

        # UID handling
        if isinstance(uids, np.ndarray):
            uids_array = np.copy(uids)
        else:
            uids_array = np.array(uids, dtype=np.int64)

        # Scatter rewards (matching PyTorch scatter behavior)
        scattered_rewards = np.copy(ema_scores)
        try:
            scattered_rewards[uids_array] = rewards
        except Exception as e:
            bt.logging.error(f"ERROR:43879432: Error assigning scattered_rewards: {e}.")

        bt.logging.debug(f"Scattered rewards: {rewards}")

        # Dampening factor for scattered rewards equal to 0
        default_alpha: float = moving_average_alpha
        low_alpha: float = moving_average_alpha / 2

        # Update EMA scores
        # if the miner reward is 0, use low_alpha, otherwise use default_alpha
        ema_scores = np.where(scattered_rewards == 0, (1 - low_alpha) * ema_scores, default_alpha * scattered_rewards + (1 - default_alpha) * ema_scores)

        if self.verbose:
            bt.logging.debug(f"Updated moving avg scores: {ema_scores}")

        # Normalize EMA scores
        sum_scores = np.sum(ema_scores)
        if sum_scores > 0:
            normalized_scores = ema_scores / sum_scores
        else:
            normalized_scores = np.ones_like(ema_scores) / neurons

        # Apply non-linear transformation
        transformed_scores = np.power(normalized_scores, nonlinear_power)

        # Renormalize
        sum_transformed = np.sum(transformed_scores)
        if sum_transformed > 0:
            scores = transformed_scores / (sum_transformed)
        else:
            scores = np.ones_like(transformed_scores) / neurons

        if self.verbose:
            bt.logging.debug(f"Updated final scores: {scores}")

        return scores, ema_scores

    def transposed_cubic_distribution(self, i, num_uids):
        # Calculate the range of x values
        y_min, y_max = 0.001, 0.003

        # Normalize i to the range [-1, 1] with the middle index at the inflection point
        x_normalized = (2 * (num_uids - i - 1) / num_uids) - 1

        # Apply the cubic function
        y_normalized = x_normalized**3

        # Scale y_normalized to the desired range [y_min, y_max]
        y_scaled = y_min + (y_max - y_min) * (y_normalized + 1) / 2

        return y_scaled

    def get_raw_weights(self, scores):
        if scores is None or scores.size == 0 or np.isnan(scores).any():
            bt.logging.error("Nan detected in Weights. Returning None.")
            return None

        raw_weights = np.copy(scores)

        # Order the UIDs for weight assignment
        ordered_uids = np.argsort(raw_weights)[::-1]
        zero_uids = np.where(raw_weights == 0)[0]

        # Determine if there are any ties in raw_weights
        unique_weights, counts = np.unique(raw_weights, return_counts=True)
        ties = unique_weights[counts > 1]

        # If there are ties, randomly shuffle the order of tied UIDs
        for tie in ties:
            if tie == 0:
                continue
            # Find the indices in raw_weights that have the tied value
            tied_indices = np.nonzero(raw_weights == tie)[0]

            # Find the positions of these tied indices within ordered_uids
            positions_in_ordered_uids = np.nonzero(np.isin(ordered_uids, tied_indices))[0]

            # Shuffle these positions amongst themselves
            shuffled_positions = np.random.permutation(positions_in_ordered_uids)

            # Apply the shuffle to ordered_uids
            ordered_uids[positions_in_ordered_uids] = ordered_uids[shuffled_positions]

        # Calculate proper length for calculating weight values
        num_uids = len(ordered_uids) - len(zero_uids)
        ordered_uids_no_zeros = ordered_uids[~np.isin(ordered_uids, zero_uids)]
        # calculate proper weight values for each non-zero uid
        if num_uids > 0:
            for i, uid in enumerate(ordered_uids_no_zeros):
                weight = self.transposed_cubic_distribution(i, num_uids)

                # Assign the weight to the raw_weights tensor
                if weight:
                    raw_weights[uid] = weight
                else:
                    bt.logging.error("Error in Weights calculation. Setting this UID to 0")
                    raw_weights[uid] = 0

            # Normalize the final raw_weights
            raw_weights = raw_weights / np.sum(np.abs(raw_weights))

        return raw_weights
