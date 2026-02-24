verbose = False

import json
import os
from typing import Any
from typing import Optional

import numpy as np

from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_factory import get_llm_backend
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
    bt.logging.set_debug(True)
elif c.get('env', 'FORCE_LOG') == 'info':
    bt.logging.set_default(True)


class ValidatorLib:
    mode = "test"  # test|local_llm|openai|anthropic
    hotkey = "v1234"
    verbose = False
    llml = get_llm_backend()
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

    def get_raw_weights(
        self,
        scores,
        burn_uid: Optional[int] = None,
        burn_rate: Optional[float] = 0.0,
    ):
        if scores is None or scores.size == 0 or np.isnan(scores).any():
            bt.logging.error("Nan detected in Weights. Returning None.")
            return None

        burn_rate = max(0.0, min(1.0, burn_rate))

        # If burn_uid is invalid index, ignore burn
        if burn_uid is not None:
            if not (0 <= int(burn_uid) < scores.shape[0]):
                # bt.logging.warning(f"Invalid burn_uid {burn_uid}; ignoring burn allocation")
                burn_uid = None

        # Prepare arrays
        original_scores = np.copy(scores)
        raw_weights = np.zeros_like(original_scores, dtype=float)

        distributed_weights = max(0.0, 1.0 - burn_rate)

        # Order the UIDs for weight assignment (based on original scores)
        ordered_uids = np.argsort(original_scores)[::-1]
        zero_uids = np.where(original_scores == 0)[0]

        # Determine if there are any ties in original_scores
        unique_weights, counts = np.unique(original_scores, return_counts=True)
        ties = unique_weights[counts > 1]

        # If there are ties, randomly shuffle the order of tied UIDs
        for tie in ties:
            if tie == 0:
                continue
            tied_indices = np.nonzero(original_scores == tie)[0]
            positions_in_ordered_uids = np.nonzero(np.isin(ordered_uids, tied_indices))[0]
            shuffled_positions = np.random.permutation(positions_in_ordered_uids)
            ordered_uids[positions_in_ordered_uids] = ordered_uids[shuffled_positions]

        # Build the list of uids that should receive distributed weights (exclude zeros and burn_uid)
        ordered_uids_no_zeros = ordered_uids[~np.isin(ordered_uids, zero_uids)]
        if burn_uid is not None:
            ordered_uids_no_zeros = ordered_uids_no_zeros[ordered_uids_no_zeros != burn_uid]

        num_uids = len(ordered_uids_no_zeros)

        # If there are non-burn uids to allocate to, compute their base weights
        if num_uids > 0 and distributed_weights > 0:
            temp_weights = np.zeros_like(original_scores, dtype=float)
            for i, uid in enumerate(ordered_uids_no_zeros):
                w = self.transposed_cubic_distribution(i, num_uids)
                if w:
                    temp_weights[uid] = w
                else:
                    bt.logging.error("Error in Weights calculation. Setting this UID to 0")
                    temp_weights[uid] = 0.0

            sum_temp = float(np.sum(np.abs(temp_weights)))
            if sum_temp > 0:
                # scale non-burn weights to sum to `distributed_weights`
                scale = distributed_weights / sum_temp
                raw_weights += temp_weights * scale
            else:
                bt.logging.warning("Computed non-burn weights sum to 0; leaving distributed weights as zeros")

        # Assign burn allocation if requested
        if burn_uid is not None and burn_rate > 0:
            bt.logging.debug(f"Burning {burn_rate} to UID {burn_uid}")
            raw_weights[int(burn_uid)] = burn_rate

        # Final sanity normalization: ensure sum of weights == 1 (or zeros if everything zero)
        total = float(np.sum(np.abs(raw_weights)))
        if total > 0:
            # Minor re-normalization to correct numerical drift (preserve burn_uid exact proportion)
            # If burn_uid present, ensure it remains burn_rate after normalization
            if burn_uid is not None and burn_rate > 0:
                # Preserve burn as exact fraction of final sum
                others_sum = total - abs(raw_weights[int(burn_uid)])
                if others_sum > 0:
                    # scale others so burn == burn_rate and others == distributed_weights
                    current_burn = abs(raw_weights[int(burn_uid)])
                    if current_burn != burn_rate:
                        # scale factor to map current_burn -> burn_rate while preserving non-burn ratios
                        factor = (1.0 - burn_rate) / others_sum
                        for i in range(len(raw_weights)):
                            if i == int(burn_uid):
                                raw_weights[i] = burn_rate
                            else:
                                raw_weights[i] = raw_weights[i] * factor
                else:
                    # only burn exists; normalize directly
                    raw_weights[int(burn_uid)] = burn_rate
            else:
                raw_weights = raw_weights / total

        return raw_weights
