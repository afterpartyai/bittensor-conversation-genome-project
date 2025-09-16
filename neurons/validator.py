# The MIT License (MIT)
# Copyright © 2024 Conversation Genome Project

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


import json
import random
import time
from typing import List

import bittensor as bt

import conversationgenome.utils
from conversationgenome.analytics.WandbLib import WandbLib
from conversationgenome.base.validator import BaseValidatorNeuron
from conversationgenome.ConfigLib import c
from conversationgenome.task.Task import Task
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.Utils import Utils
from conversationgenome.validator.ValidatorLib import ValidatorLib


class Validator(BaseValidatorNeuron):
    verbose = False
    """
    Keeping a moving average of the scores of the miners and using them to set weights at the end of each epoch. Additionally, the scores are reset for new hotkeys at the end of each epoch.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        c.set("system", "netuid", self.config.netuid)

        bt.logging.info("load_state()")
        self.load_state()
        self.responses = []
        self.initial_status_codes = {}
        self.final_status_codes = {}

    async def forward(self, test_mode=False):
        try:
            wl = WandbLib()

            miners_per_window = c.get("validator", "miners_per_window", 6)
            num_convos_per_buffer = c.get("validator", "num_convos_per_buffer", 10)
            num_windows_per_convo = c.get("validator", "num_windows_per_convo", 5)
            minimum_number_of_tasks = c.get("validator", "minimum_number_of_tasks", 10)

            # If command line overrides the standard 6 miners, then use that
            if self.config.neuron.sample_size != 6:
                miners_per_window = self.config.neuron.sample_size

            miner_sample_size = min(self.metagraph.n.item(), miners_per_window)
            bt.logging.debug(f"miner_sample_size: {miner_sample_size} config: {self.config.neuron.sample_size}, available: {self.metagraph.n.item()}")

            # Instance of validator and eval library
            vl = ValidatorLib()

            # Selected tasks and bundles
            buffered_task_bundles: dict[str, TaskBundle] = {}
            selected_tasks: List[Task] = []

            validatorHotkey = "FINDHOTKEY-"
            llm_type = "openai"
            model = "gpt-4o"

            try:
                validatorHotkey = str(self.axon.wallet.hotkey.ss58_address)

                llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")
                if llm_type_override:
                    llm_type = llm_type_override
                    model = c.get("env", "OPENAI_MODEL")
            except:
                pass

            for idx_convo in range(num_convos_per_buffer):
                batch_num = random.randint(100000, 9999999)
                task_bundle: TaskBundle = await vl.reserve_task_bundle()

                if not task_bundle:
                    continue

                buffered_task_bundles[task_bundle.guid] = task_bundle

                tasks: List[Task] = task_bundle.to_mining_tasks(number_of_tasks_per_bundle=num_windows_per_convo)

                if not tasks or len(tasks) == 0:
                    continue

                for task in tasks:
                    selected_tasks.append(task)

                # Needs to have a way for task bundles to send what validators pre-processed on them
                await vl.put_task(
                    hotkey=validatorHotkey,
                    task_bundle_id=task_bundle.guid,
                    task_id=None,
                    neuron_type="validator",
                    batch_number=batch_num,
                    data=task_bundle.input.metadata.model_dump(),
                )

                try:
                    wl.log(
                        {
                            "llm_type": llm_type,
                            "model": model,
                            "task_type": task_bundle.type,
                            "netuid": self.config.netuid,
                        }
                    )
                except:
                    pass

            # Make sure we have at least the minimum number of valid tasks to distribute
            if len(selected_tasks) < minimum_number_of_tasks:
                bt.logging.error(f"Not enough tasks received from endpoint: {len(selected_tasks)}. Aborting.")
                return False

            for task_idx, task in enumerate(selected_tasks):
                bt.logging.info(f"Looping for piece {task_idx + 1} out of {len(selected_tasks)}")
                task_bundle_id = task.bundle_guid
                task_bundle = buffered_task_bundles.get(task_bundle_id, None)

                if not task_bundle_id or not task_bundle:
                    bt.logging.error("No task bundle found.")
                    continue

                miner_uids = conversationgenome.utils.uids.get_random_uids(self, k=miner_sample_size)

                if self.verbose:
                    print(f"miner_uid pool {miner_uids}")

                if len(miner_uids) == 0:
                    bt.logging.error("No miners found.")
                    return

                bt.logging.info(f"miner_uid pool {miner_uids}")
                bt.logging.info(f"Sending task of type {task.type} to miners...")

                try:
                    task.bundle_guid = "HIDDEN"
                    task.input.data.window_idx = -1
                except Exception:
                    pass

                # Create a synapse to distribute to miners
                synapse = conversationgenome.protocol.CgSynapse(cgp_input=[{"task": task}])

                responses = await self.dendrite.forward(
                    axons=[self.metagraph.axons[uid] for uid in miner_uids],
                    synapse=synapse,
                    deserialize=False,
                )

                if self.verbose:
                    print("RAW RESPONSES", len(responses))
                    print(responses)

                # Generate retry list
                uids_to_retry = []

                for i, response in enumerate(responses):
                    status_code = getattr(response.dendrite, "status_code", None)

                    if status_code is not None:
                        self.initial_status_codes[status_code] = self.initial_status_codes.get(status_code, 0) + 1

                        if status_code in [408, 422]:
                            uids_to_retry.append(miner_uids[i])

                if uids_to_retry:
                    bt.logging.debug(f"Retrying requests for the following UIDs: {uids_to_retry}")
                    retry_responses = await self.dendrite.forward(
                        axons=[self.metagraph.axons[uid] for uid in uids_to_retry],
                        synapse=synapse,
                        deserialize=False,
                    )

                    uid_to_index = {uid: idx for idx, uid in enumerate(miner_uids)}

                    # Overwrite original responses with new responses
                    for i, uid in enumerate(uids_to_retry):
                        idx = uid_to_index[uid]
                        responses[idx] = retry_responses[i]

                    if self.verbose:
                        print(f"RETRY RESPONSES: {len(retry_responses)}")
                        print(retry_responses)

                for response_idx, response in enumerate(responses):
                    status_code = getattr(response.dendrite, "status_code", None)
                    if status_code is not None:
                        self.final_status_codes[status_code] = self.final_status_codes.get(status_code, 0) + 1

                    if not response.cgp_output:
                        bt.logging.debug(f"BAD RESPONSE: hotkey: {response.axon.hotkey} - status_code: {getattr(response.dendrite, 'status_code', None)}")

                    try:
                        miner_response = response.cgp_output
                    except:
                        miner_response = response

                    miner_result = miner_response[0]
                    miner_result = await task_bundle.format_results(miner_result)

                    bt.logging.debug(
                        f"GOOD RESPONSE: hotkey: {getattr(response.axon, 'hotkey', 'N/A')} "
                        f"from miner response idx: {response_idx} task id: {task.guid} "
                        f"{task_bundle.generate_result_logs(miner_result)}"
                    )

                    # Needs a way to save miner results per task
                    await vl.put_task(
                        hotkey=response.axon.hotkey,
                        task_bundle_id=task_bundle_id,
                        task_id=task.guid,
                        neuron_type="miner",
                        batch_number=batch_num,
                        data=miner_result,
                    )

                (final_scores, rank_scores) = await task_bundle.evaluate(miner_responses=responses)

                if test_mode and responses:
                    print(f"TEST MODE: {len(responses)} responses received for task {task.guid} with {len(final_scores)} final scores")
                    self.responses.append(responses)

                bt.logging.info(f"Initial status codes: {self.initial_status_codes}")
                bt.logging.info(f"Final status codes: {self.final_status_codes}")

                if final_scores:
                    for idx, score in enumerate(final_scores):
                        if self.verbose:
                            bt.logging.info(f"score {score}")

                        uid = -1
                        try:
                            uid = str(self.metagraph.hotkeys.index(Utils.get(score, "hotkey")))
                        except Exception as e:
                            print(f"ERROR 1162494 -- WandB logging error: {e}")

                        wl.log(
                            {
                                f"task_id.{uid}": task.guid,
                                f"hotkey.{uid}": Utils.get(score, "hotkey"),
                                f"adjusted_score.{uid}": Utils.get(score, "adjustedScore"),
                                f"final_miner_score.{uid}": Utils.get(score, "final_miner_score"),
                            }
                        )

                        if self.verbose:
                            print("^^^^^^RANK", final_scores, rank_scores, len(final_scores), miner_uids)

                    # Update the scores based on the rewards.
                    self.update_scores(rank_scores, miner_uids)

            return True
        except Exception as e:
            bt.logging.error(f"ERROR 2294374 -- Top Level Validator Error: {e}", exc_info=test_mode)

        return False


# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    wl = WandbLib()

    try:
        with Validator() as validator:
            try:
                wl.init_wandb(validator.config)
            except Exception as e:
                print(f"ERROR 2294375 -- WandB init error: {e}")

            while True:
                bt.logging.info(f"CGP Validator running... {time.time()}")
                time.sleep(5)
    except KeyboardInterrupt:
        bt.logging.info("Keyboard interrupt detected. Exiting validator.")
    finally:
        try:
            print("Done. Writing final to wandb.")
            wl.end_log_wandb()
        except Exception as e:
            print(f"ERROR 2294376 -- WandB end log error: {e}")
