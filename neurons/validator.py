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


import time
import os
import hashlib

# Bittensor
import bittensor as bt

# Bittensor Validator Template:
import template
#from template.validator import forward

# import base validator class which takes care of most of the boilerplate
from conversationgenome.base.validator import BaseValidatorNeuron

import conversationgenome.utils
import conversationgenome.validator

from conversationgenome.ConfigLib import c
from conversationgenome.Utils import Utils

from conversationgenome.ValidatorLib import ValidatorLib
from conversationgenome.validator.evaluator import Evaluator

from conversationgenome.protocol import CgSynapse

class Validator(BaseValidatorNeuron):
    verbose = True
    """
    xxx
    Keeping a moving average of the scores of the miners and using them to set weights at the end of each epoch. Additionally, the scores are reset for new hotkeys at the end of each epoch.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)

        bt.logging.info("load_state()")
        self.load_state()

        # xxx
        self.image_dir = './data/conversations/'
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

    async def forward(self):

        # Get random miner IDs
        miner_uids = conversationgenome.utils.uids.get_random_uids(
            self,
            k=min(self.config.neuron.sample_size, self.metagraph.n.item())
        )
        if True or self.verbose:
            print("miner_uid pool", miner_uids)
        if len(miner_uids) == 0:
            print("No miners")
            time.sleep(30)
            return

        # Instance of validator and eval library
        vl = ValidatorLib()
        el = Evaluator()
        # xxx -- what does this do?
        vl.validateMinimumTags([])
        test_mode = True

        # Reserve a conversation (so others won't take it) from the conversation API
        result = await vl.reserve_conversation()

        if result:
            miners_per_window = c.get("validator", "miners_per_window", 3)
            (full_conversation, full_conversation_metadata, conversation_windows) = result
            if test_mode:
                # In test_mode, to expand the miner scores, remove half of the full convo tags.
                # This "generates" more unique tags found for the miners
                half = int(len(full_conversation_metadata['tags'])/2)
                #full_conversation_metadata['tags'] = full_conversation_metadata['tags'][0:half]
            conversation_guid = Utils.get(full_conversation, "guid")
            #print("full_conversation", full_conversation)
            bt.logging.info(f"Received {len(conversation_windows)} conversation_windows from API")

            # Loop through conversation windows. Send each window to multiple miners
            print(f"Found {len(conversation_windows)} conversation windows. Sequentially sending to batches of miners")
            for window_idx, conversation_window in enumerate(conversation_windows):
                # Create a synapse to distribute to miners
                bt.logging.info(f"Sending convo {conversation_guid} window of {len(conversation_window)} lines to miner.")
                window_packet = {"guid":conversation_guid, "window_idx":window_idx, "lines":conversation_window}
                #print(window_packet)

                synapse = conversationgenome.protocol.CgSynapse(cgp_input = [window_packet])

                rewards = None

                # Is this blocking?
                responses = self.dendrite.query(
                    axons=[self.metagraph.axons[uid] for uid in miner_uids],
                    synapse=synapse,
                    deserialize=False,
                )
                valid_responses = []
                for response in responses:
                    if not response.cgp_output:
                        continue
                    bt.logging.info(f"CGP Received tags: {response.cgp_output[0]['tags']}")
                    valid_responses.append(response.cgp_output[0])

                for miner_result in valid_responses:
                    #print("miner_result", miner_result)
                    bt.logging.info(f"MINER RESULT uid: {miner_result['uid']}, tags: {miner_result['tags']} vector count: {len(miner_result['vectors'])}")
                (final_scores, rank_scores) = await el.evaluate(full_conversation_metadata, valid_responses)
                # Walk through the rewards per epoch code
                #bt.logging.info(f"CGP Scored responses: {rewards}")

                # Update the scores based on the rewards. You may want to define your own update_scores function for custom behavior.
                #rewards = torch.ones(len(miner_uids))
                self.update_scores(rank_scores, miner_uids)

# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    with Validator() as validator:
        while True:
            bt.logging.info("CGP Validator running...", time.time())
            # xxx Remove for Prod? Add for mode test?
            time.sleep(5)
