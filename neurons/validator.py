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


import copy
import os
import random
import time
from typing import List

import bittensor as bt

import conversationgenome.utils
from conversationgenome.analytics.WandbLib import WandbLib
from conversationgenome.api.models.conversation import Conversation
from conversationgenome.api.models.conversation_metadata import ConversationMetadata
from conversationgenome.base.validator import BaseValidatorNeuron
from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_factory import configure_llm_override_lockdown
from conversationgenome.task.Task import Task
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.Utils import Utils
from conversationgenome.validator.evaluator import Evaluator
from conversationgenome.validator.ValidatorLib import ValidatorLib


class Validator(BaseValidatorNeuron):
    verbose = False
    """
    Keeping a moving average of the scores of the miners and using them to set weights at the end of each epoch. Additionally, the scores are reset for new hotkeys at the end of each epoch.
    """

    def __init__(self, config=None):
        private_key_hex = c.get("env", "COMMITMENT_PRIVATE_KEY", "").strip()
        if not private_key_hex:
            bt.logging.error(
                "COMMITMENT_PRIVATE_KEY is not set. Validators require it to read miner "
                "endpoint commitments. Set it in your environment and restart. "
                "Contact ReadyAI if you need help."
            )
            raise SystemExit(1)
        try:
            bytes.fromhex(private_key_hex)
        except ValueError:
            bt.logging.error(
                "COMMITMENT_PRIVATE_KEY is set but is not valid hex. Check your environment "
                "(see env.example) and restart."
            )
            raise SystemExit(1)

        super(Validator, self).__init__(config=config)
        c.set("system", "netuid", self.config.netuid)
        configure_llm_override_lockdown(self.config.netuid)

        bt.logging.info("load_state()")
        self.load_state()
        self.responses = []
        self.initial_status_codes = {}
        self.final_status_codes = {}
        self._uid_refresh_timestamps: dict = {}  # {uid: last_refresh_time}

        # One-shot commitment refresh at startup so committed_endpoints is
        # populated before the first forward(). We do NOT refresh on every
        # forward (that stalls validators on slow chain endpoints), but the
        # initial sync()/resync_metagraph() may not fire for a full epoch
        # after boot — until then committed_endpoints would be empty and
        # every commitment-style miner would unreachable via the metagraph
        # placeholder axon.
        try:
            self.refresh_miner_endpoints(force=True)
        except Exception as e:
            bt.logging.warning(f"Initial commitment refresh failed: {e}")

    def _refresh_commitment_for_uid(self, uid):
        """Re-read and decrypt the commitment for a single miner UID. Debounced to 5 min per UID."""
        import time as _time

        now = _time.time()
        last = self._uid_refresh_timestamps.get(uid, 0)
        if now - last < 300:
            bt.logging.debug(f"Skipping commitment refresh for UID {uid} — last refresh was {int(now - last)}s ago.")
            return

        private_key_hex = c.get("env", "COMMITMENT_PRIVATE_KEY", "").strip()
        if not private_key_hex:
            return

        self._uid_refresh_timestamps[uid] = now

        try:
            from conversationgenome.commitment.commitment import decrypt_endpoint, read_commitment

            if uid >= len(self.metagraph.hotkeys):
                bt.logging.debug(f"UID {uid} out of range for current metagraph, skipping commitment refresh.")
                return
            hotkey = self.metagraph.hotkeys[uid]
            private_key_bytes = bytes.fromhex(private_key_hex)
            ciphertext = read_commitment(self.subtensor, self.config.netuid, hotkey)
            if ciphertext is None:
                return
            ip, port = decrypt_endpoint(ciphertext, private_key_bytes, expected_hotkey=hotkey)
            self.committed_endpoints[hotkey] = (ip, port)
            # Use block 0 so the next query_map re-verifies against the real block.
            self._commitment_cache[hotkey] = (0, ip, port)
            bt.logging.info(f"Refreshed commitment for UID {uid} after failed request.")
        except ValueError as e:
            # Commitment is invalid (hotkey mismatch, old format, etc.) — evict from cache
            hotkey = self.metagraph.hotkeys[uid] if uid < len(self.metagraph.hotkeys) else None
            if hotkey:
                self.committed_endpoints.pop(hotkey, None)
                self._commitment_cache.pop(hotkey, None)
            bt.logging.warning(f"Rejected commitment for UID {uid}: {e}")
        except Exception as e:
            bt.logging.debug(f"Could not refresh commitment for UID {uid}: {e}")

    def _get_axons_for_uids(self, uids):
        """Get axon list for UIDs, applying committed endpoint overrides when available."""
        axons = []
        for uid in uids:
            if uid >= len(self.metagraph.axons) or uid >= len(self.metagraph.hotkeys):
                bt.logging.debug(f"UID {uid} out of range, skipping.")
                continue
            axon = self.metagraph.axons[uid]
            hotkey = self.metagraph.hotkeys[uid]
            if hotkey in self.committed_endpoints:
                ip, port = self.committed_endpoints[hotkey]
                axon = copy.copy(axon)
                axon.ip = ip
                axon.port = port
                bt.logging.info(f"UID {uid}: using committed endpoint")
            else:
                bt.logging.info(f"UID {uid}: using metagraph endpoint")
            axons.append(axon)
        return axons

    async def forward(self, test_mode=False):
        try:
            # NOTE: deliberately no forced commitment refresh here. Refresh
            # happens in two existing paths that are sufficient and don't
            # block the loop on every iteration:
            #   1. resync_metagraph()'s periodic refresh (debounced 5 min)
            #   2. _refresh_commitment_for_uid on per-UID errors after a
            #      failed call (so a stale endpoint self-heals on retry)
            # Forcing refresh every forward stalls the async loop on slow
            # chain endpoints (e.g. public finney), causing dendrite calls
            # to time out en masse for validators not running a local node.

            wl = WandbLib()

            miners_per_task = c.get("validator", "miners_per_task", 6)
            number_of_task_bundles = c.get("validator", "number_of_task_bundles", 10)
            number_of_task_per_bundle = c.get("validator", "number_of_task_per_bundle", 5)
            minimum_number_of_tasks = c.get("validator", "minimum_number_of_tasks", 10)

            # If command line overrides the standard 6 miners, then use that
            if self.config.neuron.sample_size != 6:
                miners_per_task = self.config.neuron.sample_size

            miner_sample_size = min(self.metagraph.n.item(), miners_per_task)
            bt.logging.debug(f"miner_sample_size: {miner_sample_size} config: {self.config.neuron.sample_size}, available: {self.metagraph.n.item()}")

            # Instance of validator and eval library
            vl = ValidatorLib()

            # Selected tasks and bundles
            buffered_task_bundles: dict[str, TaskBundle] = {}
            selected_tasks: List[Task] = []

            validatorHotkey = "FINDHOTKEY-"
            llm_type = c.get('llm', 'type')
            model = c.get('llm', 'model')

            try:
                validatorHotkey = str(self.axon.wallet.hotkey.ss58_address)

                llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")
                if llm_type_override and not c.get("system", "llm_overrides_locked", False):
                    llm_type = llm_type_override
                    model = c.get("env", "OPENAI_MODEL")
            except:
                pass

            for _ in range(number_of_task_bundles):
                batch_num = random.randint(100000, 9999999)
                task_bundle: TaskBundle = await vl.reserve_task_bundle(self.config.netuid)

                if not task_bundle:
                    continue

                if not task_bundle.is_ready():
                    bt.logging.error(f"Task bundle not ready. Skipping.")
                    continue

                buffered_task_bundles[task_bundle.guid] = task_bundle

                tasks: List[Task] = task_bundle.to_mining_tasks(number_of_tasks_per_bundle=number_of_task_per_bundle)

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

                masked_task = task_bundle.mask_task_for_miner(task)

                # Create a synapse to distribute to miners
                synapse = conversationgenome.protocol.CgSynapse(cgp_input=[{"task": masked_task}])

                await self.throttle_dispatch()
                responses = await self.dendrite.forward(
                    axons=self._get_axons_for_uids(miner_uids),
                    synapse=synapse,
                    deserialize=False,
                    timeout=task.timeout,
                )

                if self.verbose:
                    print("RAW RESPONSES", len(responses))
                    print(responses)

                # Generate refresh and retry lists.
                # Refresh policy: any non-success outcome
                # Retry policy: 408/422/503 and connection-level failures (None)
                RETRY_STATUS_CODES = {408, 422, 503, None}

                uids_to_retry = []
                for i, response in enumerate(responses):
                    status_code = getattr(response.dendrite, "status_code", None)

                    if status_code is not None:
                        self.initial_status_codes[status_code] = self.initial_status_codes.get(status_code, 0) + 1

                    has_output = bool(getattr(response, "cgp_output", None))
                    is_success = status_code == 200 and has_output

                    if not is_success:
                        self._refresh_commitment_for_uid(miner_uids[i])

                    if status_code in RETRY_STATUS_CODES and not is_success:
                        uids_to_retry.append(miner_uids[i])
                        bt.logging.info(
                            f"status={status_code} output={has_output} for UID {miner_uids[i]} "
                            "— refreshing commitment and retrying."
                        )

                uid_to_index = {uid: idx for idx, uid in enumerate(miner_uids)}

                # Retry only the UIDs whose failure mode might benefit from
                # a second attempt against a refreshed endpoint.
                if uids_to_retry:
                    bt.logging.debug(f"Retrying requests for the following UIDs (same synapse): {uids_to_retry}")

                    await self.throttle_dispatch()
                    retry_responses = await self.dendrite.forward(
                        axons=self._get_axons_for_uids(uids_to_retry),
                        synapse=synapse,
                        deserialize=False,
                        timeout=task.timeout,
                    )

                    for i, uid in enumerate(uids_to_retry):
                        idx = uid_to_index[uid]
                        responses[idx] = retry_responses[i]

                    if self.verbose:
                        print(f"RETRY RESPONSES (same synapse): {len(retry_responses)}")
                        print(retry_responses)

                for response_idx, response in enumerate(responses):
                    status_code = getattr(response.dendrite, "status_code", None)
                    if status_code is not None:
                        self.final_status_codes[status_code] = self.final_status_codes.get(status_code, 0) + 1

                    if not response.cgp_output:
                        bt.logging.debug(f"BAD RESPONSE: hotkey: {response.axon.hotkey} - status_code: {getattr(response.dendrite, 'status_code', None)}")
                        continue

                    try:
                        miner_response = response.cgp_output
                    except:
                        miner_response = response

                    miner_result = miner_response[0]
                    try:
                        miner_result = await task_bundle.format_results(miner_result)
                    except Exception as e:
                        # miner_result is untrusted, miner-controlled data -- a
                        # wrong-shaped response (bad types, wrong structure)
                        # must not be able to take down scoring for the whole
                        # batch. Skip just this response
                        bt.logging.error(f"ERROR -- format_results failed for hotkey {getattr(response.axon, 'hotkey', 'N/A')}: {e}")
                        continue

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
                        data={
                            "result": miner_result,
                            "task": task.model_dump(),
                        },
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
