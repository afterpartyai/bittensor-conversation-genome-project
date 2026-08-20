# The MIT License (MIT)
# Copyright © 2024 Afterparty, Inc.

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


import argparse
import asyncio
import copy
import datetime
import logging
import os
import re
import threading
import time
from traceback import print_exception
from typing import Dict, List, Tuple

import bittensor as bt
import numpy as np
import torch

from conversationgenome.base.neuron import BaseNeuron
from conversationgenome.ConfigLib import c
from conversationgenome.mock.mock import MockDendrite
from conversationgenome.utils.config import add_validator_args
from conversationgenome.utils.uids import check_uid_availability
from conversationgenome.validator.ValidatorLib import ValidatorLib


class BaseValidatorNeuron(BaseNeuron):
    """
    Base class for Bittensor validators. Your validator should inherit from this class.
    """

    neuron_type: str = "ValidatorNeuron"

    first_sync = True

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        super().add_args(parser)
        add_validator_args(cls, parser)

    def __init__(self, config=None):
        super().__init__(config=config)

        # Save a copy of the hotkeys to local memory.
        self.hotkeys = copy.deepcopy(self.metagraph.hotkeys)

        # Dendrite lets us send messages to other nodes (axons) in the network.
        if self.config.mock:
            self.dendrite = MockDendrite(wallet=self.wallet)
        else:
            self.dendrite = bt.Dendrite(wallet=self.wallet)
        bt.logging.info(f"Dendrite: {self.dendrite}")

        # Install a log filter to redact miner IP addresses from bittensor's
        # internal dendrite/axon logs (trace, debug, error messages).
        # Matches ip:port, ip:port/, ('ip', port), and bare IPs in URLs.
        _ip_redact_patterns = re.compile(
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d{1,5})?\b"
        )

        class _RedactIPFilter(logging.Filter):
            def filter(self, record):
                msg = getattr(record, "msg", "")
                if isinstance(msg, str):
                    # Drop dendrite connection error logs entirely — they leak IPs
                    if "Can not write request body" in msg or "Cannot connect to host" in msg:
                        return False
                    record.msg = _ip_redact_patterns.sub("[REDACTED]", msg)
                if hasattr(record, "args") and record.args:
                    if isinstance(record.args, dict):
                        record.args = {
                            k: _ip_redact_patterns.sub("[REDACTED]", str(v)) if isinstance(v, str) else v
                            for k, v in record.args.items()
                        }
                    elif isinstance(record.args, tuple):
                        record.args = tuple(
                            _ip_redact_patterns.sub("[REDACTED]", str(a)) if isinstance(a, str) else a
                            for a in record.args
                        )
                return True

        for handler in logging.root.handlers:
            handler.addFilter(_RedactIPFilter())

        # Set up initial scoring weights for validation
        bt.logging.info("Building validation weights.")
        self.scores = np.zeros(self.metagraph.n, dtype=np.float32)

        self.ema_scores = np.zeros(self.metagraph.n, dtype=np.float32)

        # Initialize the non-linear transformation power
        self.nonlinear_power = 3.0

        # Burn rate -> burns 90% of the emissions.
        self.burn_rate = 0

        # Committed endpoint cache: {hotkey_ss58: (ip, port)}
        self.committed_endpoints: Dict[str, Tuple[str, int]] = {}
        # Block-aware cache: {hotkey_ss58: (block, ip, port)}
        self._commitment_cache: dict = {}
        self._last_commitment_refresh: float = 0.0

        # Init sync with the network. Updates the metagraph.
        self.sync()

        # Serve axon to enable external connections.
        if not self.config.neuron.axon_off:
            self.serve_axon()
        else:
            bt.logging.warning("axon off, not serving ip to chain.")

        # Create asyncio event loop to manage async tasks.
        self.loop = asyncio.get_event_loop()

        # Instantiate runners
        self.should_exit: bool = False
        self.is_running: bool = False
        self.thread: threading.Thread = None
        self.lock = asyncio.Lock()

        # Failsafe dispatch throttle: guarantees miners are never hit faster
        # than min_seconds_between_dispatches, regardless of num_concurrent_forwards
        # or how fast forward() happens to complete (e.g. due to a bad config
        # or fast-failing requests removing the natural network-latency pacing).
        self._dispatch_lock = asyncio.Lock()
        self._last_dispatch_time = 0.0
        self._min_dispatch_interval = c.get("validator", "min_seconds_between_dispatches", 12.0)

        if self.config.neuron.num_concurrent_forwards > 1:
            bt.logging.warning(
                f"neuron.num_concurrent_forwards is set to {self.config.neuron.num_concurrent_forwards} "
                "(default is 1). Running multiple forward() loops concurrently can cause miners to be "
                "queried much more frequently than intended. Verify this is intentional."
            )

    def serve_axon(self):
        """Serve axon to enable external connections."""

        bt.logging.info("serving ip to chain...")
        try:
            self.axon = bt.Axon(wallet=self.wallet, config=self.config)

            try:
                self.subtensor.serve_axon(
                    netuid=self.config.netuid,
                    axon=self.axon,
                )
                bt.logging.info(f"Running validator {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}")
            except Exception as e:
                bt.logging.error(f"Failed to serve Axon with exception: {e}")
                pass

        except Exception as e:
            bt.logging.error(f"Failed to create Axon initialize with exception: {e}")
            pass

    async def concurrent_forward(self):
        coroutines = [self.forward() for _ in range(self.config.neuron.num_concurrent_forwards)]
        results = await asyncio.gather(*coroutines)
        return results

    async def throttle_dispatch(self):
        """Failsafe rate limit: block until at least min_seconds_between_dispatches
        has passed since the last dispatch. Shared across all concurrent forward()
        coroutines via _dispatch_lock, so it holds even if num_concurrent_forwards
        is misconfigured or a task loop completes unusually fast."""
        async with self._dispatch_lock:
            wait = self._min_dispatch_interval - (time.monotonic() - self._last_dispatch_time)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_dispatch_time = time.monotonic()

    def run(self):
        """
        Initiates and manages the main loop for the miner on the Bittensor network. The main loop handles graceful shutdown on keyboard interrupts and logs unforeseen errors.

        This function performs the following primary tasks:
        1. Check for registration on the Bittensor network.
        2. Continuously forwards queries to the miners on the network, rewarding their responses and updating the scores accordingly.
        3. Periodically resynchronizes with the chain; updating the metagraph with the latest network state and setting weights.

        The essence of the validator's operations is in the forward function, which is called every step. The forward function is responsible for querying the network and scoring the responses.

        Note:
            - The function leverages the global configurations set during the initialization of the miner.
            - The miner's axon serves as its interface to the Bittensor network, handling incoming and outgoing requests.

        Raises:
            KeyboardInterrupt: If the miner is stopped by a manual interruption.
            Exception: For unforeseen errors during the miner's operation, which are logged for diagnosis.
        """

        # Check that validator is registered on the network.
        self.sync()

        bt.logging.info(f"Validator starting at block: {self.block}")

        # This loop maintains the validator's operations until intentionally stopped.
        try:
            while True:
                bt.logging.info(f"step({self.step}) block({self.block})")

                # Run multiple forwards concurrently.
                results = self.loop.run_until_complete(self.concurrent_forward())

                # Check if we should exit.
                if self.should_exit:
                    break

                # Sync metagraph and potentially set weights.
                success = True
                for result in results:
                    if not result:
                        success = False
                        break
                if success:
                    print("________________________________SYNC to set weight")
                    self.sync()
                else:
                    bt.logging.error(f"Error occurred during validation. Skipping weight set.")

                self.step += 1

        # If someone intentionally stops the validator, it'll safely terminate operations.
        except KeyboardInterrupt:
            self.axon.stop()
            bt.logging.success("Validator killed by keyboard interrupt.")
            exit()

        # In case of unforeseen errors, the validator will log the error and continue operations.
        except Exception as err:
            bt.logging.error("Error during validation", str(err))
            bt.logging.debug(print_exception(type(err), err, err.__traceback__))

    def run_in_background_thread(self):
        """
        Starts the validator's operations in a background thread upon entering the context.
        This method facilitates the use of the validator in a 'with' statement.
        """
        if not self.is_running:
            bt.logging.debug("Starting validator in background thread.")
            self.should_exit = False
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            self.is_running = True
            bt.logging.debug("Started")

    def stop_run_thread(self):
        """
        Stops the validator's operations that are running in the background thread.
        """
        if self.is_running:
            bt.logging.debug("Stopping validator in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped")

    def __enter__(self):
        self.run_in_background_thread()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Stops the validator's background operations upon exiting the context.
        This method facilitates the use of the validator in a 'with' statement.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
                      None if the context was exited without an exception.
            exc_value: The instance of the exception that caused the context to be exited.
                       None if the context was exited without an exception.
            traceback: A traceback object encoding the stack trace.
                       None if the context was exited without an exception.
        """
        if self.is_running:
            bt.logging.debug("Stopping validator in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped")

    def get_burn_uid(self):
        # Get the subtensor owner hotkey
        sn_owner_hotkey = self.subtensor.query_subtensor(
            "SubnetOwnerHotkey",
            params=[self.config.netuid],
        )
        bt.logging.debug(f"Burn key (Subnet Owner Hotkey): {sn_owner_hotkey}")

        # Get the UID of this hotkey
        sn_owner_uid = self.subtensor.get_uid_for_hotkey_on_subnet(
            hotkey_ss58=sn_owner_hotkey,
            netuid=self.config.netuid,
        )
        bt.logging.debug(f"Burn UID: {sn_owner_uid}")

        return sn_owner_uid

    def set_weights(self):
        """
        Sets the validator weights to the metagraph hotkeys based on the scores it has received from the miners. The weights determine the trust and incentive level the validator assigns to miner nodes on the network.
        """
        msg = None
        # Check if self.scores contains any NaN values and log a warning if it does.
        if np.isnan(self.scores).any():
            bt.logging.warning(f"Scores contain NaN values. This may be due to a lack of responses from miners, or a bug in your reward functions.")

        # if self.scores is empty or all zeros, return
        if self.scores is None or np.all(self.scores == 0) or self.scores.size == 0:
            bt.logging.info(f"Score array is empty or all zeros. Skipping weight setting.")
            return

        # Calculate the average reward for each uid across non-zero values.
        # Replace any NaN values with 0.
        vl = ValidatorLib()

        burn_uid = self.get_burn_uid()
        burn_rate = self.burn_rate

        # Eligible UIDs receive a tiny baseline weight even if their score is 0,
        # so a miner that has never been sampled (or had a transient failure) is
        # not permanently locked out of the cubic distribution. Filter matches
        # the sampling filter in get_random_uids -> check_uid_availability.
        eligible_uids = [
            uid for uid in range(self.metagraph.n.item())
            if check_uid_availability(self.metagraph, uid, self.config.neuron.vpermit_tao_limit)
        ]

        raw_weights = vl.get_raw_weights(
            self.scores,
            burn_uid=burn_uid,
            burn_rate=burn_rate,
            eligible_uids=eligible_uids,
        )

        if raw_weights is None or raw_weights.size == 0:
            bt.logging.error("Error Generating raw weights. Returning without setting weights")
            return

        bt.logging.debug(f"raw_weights: {raw_weights}")
        bt.logging.debug(f"raw_weight_uids{self.metagraph.uids.tolist()}")
        # Process the raw weights to final_weights via subtensor limitations.
        (
            processed_weight_uids,
            processed_weights,
        ) = bt.utils.weight_utils.process_weights_for_netuid(
            uids=self.metagraph.uids,
            weights=raw_weights,
            netuid=self.config.netuid,
            subtensor=self.subtensor,
            metagraph=self.metagraph,
        )
        bt.logging.debug(f"processed_weights {processed_weights}")
        bt.logging.debug(f"processed_weight_uids {processed_weight_uids}")

        # Convert to uint16 weights and uids.
        (
            uint_uids,
            uint_weights,
        ) = bt.utils.weight_utils.convert_weights_and_uids_for_emit(
            uids=processed_weight_uids,
            weights=processed_weights,
        )
        bt.logging.debug(f"uint_weights: {uint_weights}")
        bt.logging.debug(f"uint_uids: {uint_uids}")

        # Set the weights on chain via our subtensor connection.
        print("---Set the weights on chain", self.wallet, self.config.netuid, uint_uids, uint_weights, self.spec_version)
        result = None
        try:
            result, msg = self.subtensor.set_weights(
                wallet=self.wallet,
                netuid=self.config.netuid,
                uids=uint_uids,
                weights=uint_weights,
                wait_for_finalization=False,
                wait_for_inclusion=False,
                version_key=self.spec_version,
            )
        except:
            print("ERROR")
        if result is True:
            bt.logging.info("set_weights on chain successfully!")
        else:
            bt.logging.error(f"set_weights failed: {msg}")

    def refresh_miner_endpoints(self, force: bool = False):
        """Read and decrypt encrypted endpoint commitments for all miners.

        Args:
            force: If True, bypass the 5-minute debounce. Use at the start of
                each forward() loop to guarantee freshness before sampling
                miners. The chain query (query_map) is debounced cheaply by
                block-number caching inside read_all_commitments, so forcing
                here only re-fetches the map (~tens of ms) and re-decrypts
                only entries whose block changed.
        """
        private_key_hex = c.get("env", "COMMITMENT_PRIVATE_KEY", "").strip()
        if not private_key_hex:
            return

        # 5-min debounce protects against thrashing when resync_metagraph fires
        # frequently; callers that need fresh state at a specific moment can
        # pass force=True (e.g. before a new forward loop dispatches synapses).
        import time as _time
        now = _time.time()
        if not force and now - self._last_commitment_refresh < 300:
            bt.logging.info(f"Skipping commitment refresh — last refresh was {int(now - self._last_commitment_refresh)}s ago.")
            return
        self._last_commitment_refresh = now

        try:
            from conversationgenome.commitment.commitment import read_all_commitments

            private_key_bytes = bytes.fromhex(private_key_hex)
            endpoints, self._commitment_cache = read_all_commitments(
                self.subtensor, self.config.netuid, self.metagraph.hotkeys, private_key_bytes,
                cache=self._commitment_cache,
            )
            self.committed_endpoints = endpoints
            for hotkey in endpoints:
                uid = self.metagraph.hotkeys.index(hotkey) if hotkey in self.metagraph.hotkeys else "?"
                bt.logging.info(f"  Commitment found for UID {uid}")
        except Exception as e:
            bt.logging.error(f"Error refreshing miner commitments: {e}")

    def resync_metagraph(self):
        """Resyncs the metagraph and updates the hotkeys and moving averages based on the new metagraph."""
        bt.logging.info("resync_metagraph()")

        # Copies state of metagraph before syncing.
        previous_metagraph = copy.deepcopy(self.metagraph)

        # Sync the metagraph.
        self.metagraph.sync(subtensor=self.subtensor)

        # Clean stale entries from commitment caches for hotkeys no longer in metagraph.
        current_hotkeys = set(self.metagraph.hotkeys)
        stale_keys = [hk for hk in self.committed_endpoints if hk not in current_hotkeys]
        for hk in stale_keys:
            del self.committed_endpoints[hk]
            self._commitment_cache.pop(hk, None)
        if stale_keys:
            bt.logging.info(f"Cleaned {len(stale_keys)} stale commitment cache entries.")

        # Refresh encrypted endpoint commitments on every metagraph sync,
        # regardless of whether axon info changed (commitments are independent).
        self.refresh_miner_endpoints()

        # Check if the metagraph axon info has changed.
        if previous_metagraph.axons == self.metagraph.axons:
            return

        bt.logging.info("Metagraph updated, re-syncing hotkeys, dendrite pool and moving averages")
        # Zero out all hotkeys that have been replaced.
        for uid, hotkey in enumerate(self.hotkeys):
            if hotkey != self.metagraph.hotkeys[uid]:
                self.scores[uid] = 0  # hotkey has been replaced
                self.ema_scores[uid] = 0  # hotkey has been replaced

        # Check to see if the metagraph has changed size.
        # If so, we need to add new hotkeys and moving averages.
        if len(self.hotkeys) < len(self.metagraph.hotkeys):
            # Update the size of the moving average scores.
            new_moving_average = np.zeros((self.metagraph.n))
            new_scores = np.zeros((self.metagraph.n))
            min_len = min(len(self.hotkeys), len(self.scores))
            new_scores[:min_len] = self.scores[:min_len]
            new_moving_average = self.ema_scores[:min_len]
            self.scores = new_scores
            self.ema_scores = new_moving_average

        # Update the hotkeys.
        self.hotkeys = copy.deepcopy(self.metagraph.hotkeys)

    def update_scores(self, rewards: np.ndarray, uids: List[int]):
        """
        Performs exponential moving average on the scores based on the rewards received from the miners,
        then normalizes, applies a non-linear transformation, and renormalizes the scores.
        """

        vl = ValidatorLib()
        updated_scores, updated_ema_scores = vl.update_scores(
            rewards,
            uids,
            self.ema_scores,
            self.scores,
            self.config.neuron.moving_average_alpha,
            self.device,
            self.metagraph.n,
            self.nonlinear_power,
        )

        if updated_scores.size > 0 and updated_ema_scores.size > 0 and not np.isnan(updated_scores).any() and not np.isnan(updated_ema_scores).any():
            self.scores = updated_scores
            self.ema_scores = updated_ema_scores
        else:
            bt.logging.error("Error 2378312: Error with Nonlinear transformation and Renormalization in update_scores. self.scores not updated")

        bt.logging.debug(f"Updated final scores: {self.scores}")

    def save_state(self):
        """Saves the state of the validator to a file."""
        if self.first_sync:
            bt.logging.info(f"Ignore first sync so it doesn't save over last data.")
            self.first_sync = False
            return

        # check if self.scores and self.ema_scores are empty, if so, don't save
        if np.all(self.ema_scores == 0) or np.all(self.scores == 0) or self.ema_scores.size == 0 or self.scores.size == 0:
            bt.logging.info(f"EMA score and/or Score array is empty or all zeros. Skipping save state.")
            return

        state_path = self.config.neuron.full_path + "/state.npz"
        bt.logging.info(f"Saving validator state to {state_path}.")

        # Save the state of the validator to file.
        np.savez(
            self.config.neuron.full_path + "/state.npz",
            step=self.step,
            scores=self.scores,
            hotkeys=self.hotkeys,
            ema_scores=self.ema_scores,
        )

        if os.path.isfile(state_path):
            bt.logging.info(f"Save state confirmed")
        else:
            bt.logging.info(f"Save state failed.")

    def load_state(self):
        """Loads the state of the validator from a file."""
        npz_path = self.config.neuron.full_path + "/state.npz"
        pt_path = self.config.neuron.full_path + "/state.pt"

        if os.path.isfile(npz_path):
            file_stats = os.stat(npz_path)
            last_mod_dt = datetime.datetime.fromtimestamp(file_stats.st_mtime)
            bt.logging.info(f"\n\nLoading state file. File last updated: {last_mod_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            # Load state from .npz file
            bt.logging.info(f"Loading validator state from {npz_path}.")
            state = np.load(npz_path)
            self.step = state["step"].item()  # Ensure it's a Python scalar
            self.scores = state["scores"]
            self.hotkeys = state["hotkeys"]
            if "ema_scores" in state:
                self.ema_scores = state["ema_scores"]
            else:
                bt.logging.info("ema_scores not found in saved state. Initializing with default values.")
                self.ema_scores = np.zeros_like(self.scores)
        elif os.path.isfile(pt_path):
            file_stats = os.stat(pt_path)
            last_mod_dt = datetime.datetime.fromtimestamp(file_stats.st_mtime)
            bt.logging.info(f"\n\nLoading state file. File last updated: {last_mod_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            # Load state from .pt file
            bt.logging.info(f"Loading validator state from {pt_path}.")
            state = torch.load(pt_path)
            self.step = int(state["step"])
            self.hotkeys = np.array(state["hotkeys"])
            self.scores = state["scores"].cpu().numpy()  # Convert to NumPy array

            if "ema_scores" in state:
                self.ema_scores = state["ema_scores"].cpu().numpy()  # Convert to NumPy array
            else:
                bt.logging.info("ema_scores not found in saved state. Initializing with default values.")
                self.ema_scores = np.zeros_like(self.scores)

            # Save the state as a .npz file
            self.save_state()
        else:
            bt.logging.info("No state file found.")

        try:
            bt.logging.debug(f"Loaded state. Step: {self.step} Num scores: {len(self.scores)} Sum scores: {np.sum(self.scores)} Num hotkeys: {len(self.hotkeys)}")
        except Exception as e:
            print("Log error", e)
