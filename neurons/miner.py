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

import time
import typing

# Bittensor
import bittensor as bt

from conversationgenome.base.miner import BaseMinerNeuron
from conversationgenome.ConfigLib import c
from conversationgenome.miner.MinerLib import MinerLib
from conversationgenome.protocol import CgSynapse
from conversationgenome.task import Task
from conversationgenome.task.task_factory import parse_task
from conversationgenome.utils.Utils import Utils


class Miner(BaseMinerNeuron):
    verbose = False

    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)
        c.set("system", "netuid", self.config.netuid)

    async def forward(self, synapse: CgSynapse) -> CgSynapse:
        """
        Processes the incoming 'CgSynapse' synapse by performing a predefined operation on the input data.

        Args:
            synapse (CgSynapse): The synapse object containing the 'cgp_input' data.

        Returns:
            CgSynapse: The synapse object with the 'cgp_output' field

        """
        ml = MinerLib()

        try:
            task: Task = parse_task(synapse.cgp_input[0]["task"])

            bt.logging.info(f"Miner received task of type {task.type}")
            result = await ml.do_mining(task=task)
        except Exception as e:
            bt.logging.error(f"Error extracting task from synapse. Fallback to old method.")

            # Here we ensure miners can still process requests from validators that are yet to update.
            window = synapse.cgp_input[0]
            conversation_guid = Utils.get(window, "guid")
            window_idx = Utils.get(window, "window_idx")
            lines = Utils.get(window, "lines")
            task_prompt = Utils.get(window, "task_prompt")
            task_type = Utils.get(window, "task_type")

            result = await ml.do_old_mining(
                conversation_guid=conversation_guid,
                window_idx=window_idx,
                conversation_window=lines,
                minerUid=17,
                task_prompt=task_prompt,
                task_type=task_type,
            )

        synapse.cgp_output = [result]
        return synapse

    async def blacklist(self, synapse: CgSynapse) -> typing.Tuple[bool, str]:
        """
        Determines whether an incoming request should be blacklisted and thus ignored. Your implementation should
        define the logic for blacklisting requests based on your needs and desired security parameters.

        Blacklist runs before the synapse data has been deserialized (i.e. before synapse.data is available).
        The synapse is instead contructed via the headers of the request. It is important to blacklist
        requests before they are deserialized to avoid wasting resources on requests that will be ignored.

        Args:
            synapse (CgSynapse): A synapse object constructed from the headers of the incoming request.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether the synapse's hotkey is blacklisted,
                            and a string providing the reason for the decision.

        This function is a security measure to prevent resource wastage on undesired requests. It should be enhanced
        to include checks against the metagraph for entity registration, validator status, and sufficient stake
        before deserialization of synapse data to minimize processing overhead.

        Example blacklist logic:
        - Reject if the hotkey is not a registered entity within the metagraph.
        - Consider blacklisting entities that are not validators or have insufficient stake.

        In practice it would be wise to blacklist requests from entities that are not validators, or do not have
        enough stake. This can be checked via metagraph.S and metagraph.validator_permit. You can always attain
        the uid of the sender via a metagraph.hotkeys.index( synapse.dendrite.hotkey ) call.

        Otherwise, allow the request to be processed further.
        """
        # TODO(developer): Define how miners should blacklist requests.
        if not self.config.blacklist.allow_non_registered and synapse.dendrite.hotkey not in self.metagraph.hotkeys:
            # Ignore requests from un-registered entities.
            bt.logging.trace(f"Blacklisting un-registered hotkey {synapse.dendrite.hotkey}")
            return True, "Unrecognized hotkey"
        uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        if self.config.blacklist.force_validator_permit:
            # If the config is set to force validator permit, then we should only allow requests from validators.
            if not self.metagraph.validator_permit[uid]:
                bt.logging.warning(f"Blacklisting a request from non-validator hotkey {synapse.dendrite.hotkey}")
                return True, "Non-validator hotkey"

        bt.logging.trace(f"Not Blacklisting recognized hotkey {synapse.dendrite.hotkey}")
        return False, "Hotkey recognized!"

    async def priority(self, synapse: CgSynapse) -> float:
        """
        This implementation assigns priority to incoming requests based on the calling entity's stake in the metagraph.

        Args:
            synapse (CgSynapse): The synapse object that contains metadata about the incoming request.

        Returns:
            float: A priority score derived from the stake of the calling entity.

        Miners may recieve messages from multiple entities at once. This function determines which request should be
        processed first. Higher values indicate that the request should be processed first. Lower values indicate
        that the request should be processed later.

        """
        caller_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)  # Get the caller index.
        priority = float(self.metagraph.S[caller_uid])  # Return the stake as the priority.
        bt.logging.trace(f"Prioritizing {synapse.dendrite.hotkey} with value: {priority}")
        return priority


# This is the main function, which runs the miner.
if __name__ == "__main__":
    with Miner() as miner:
        while True:
            bt.logging.info(f"CGP Miner running... {time.time()}")
            time.sleep(5)
