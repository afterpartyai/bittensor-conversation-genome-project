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
import os
import hashlib
import random

from conversationgenome.base.validator import BaseValidatorNeuron

import conversationgenome.utils
import conversationgenome.validator

from conversationgenome.ConfigLib import c
from conversationgenome.utils.Utils import Utils

from conversationgenome.analytics.WandbLib import WandbLib

from conversationgenome.validator.ValidatorLib import ValidatorLib
from conversationgenome.validator.evaluator import Evaluator

from conversationgenome.protocol import CgSynapse

import bittensor as bt

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

    async def forward(self, test_mode=False):
        try:
            wl = WandbLib()

            miners_per_window = c.get("validator", "miners_per_window", 6)
            num_convos_per_buffer = c.get("validator", "num_convos_per_buffer", 10)
            num_windows_per_convo = c.get("validator", "num_windows_per_convo", 5)

            # If command line overrides the standard 6 miners, then use that
            if self.config.neuron.sample_size != 6:
                miners_per_window = self.config.neuron.sample_size
            miner_sample_size = min(self.metagraph.n.item(), miners_per_window)
            bt.logging.debug(f"miner_sample_size: {miner_sample_size} config: {self.config.neuron.sample_size}, available: {self.metagraph.n.item()}")

            # Get hotkeys to watch for debugging
            hot_keys = c.get("env", "HIGHLIGHT_HOTKEYS", "")
            hot_key_watchlist = hot_keys.split(",")

            # Instance of validator and eval library
            vl = ValidatorLib()
            el = Evaluator()

            # Reserve conversations from the conversation API
            bufferedConvos = {}
            pieces = []
            for idx_convo in range(num_convos_per_buffer):
                batch_num = random.randint(100000, 9999999)
                full_conversation = await vl.reserve_conversation(batch_num=batch_num, return_indexed_windows=True)
                if not full_conversation:
                    continue
                conversation_guid = str(Utils.get(full_conversation, "guid"))
                bufferedConvos[conversation_guid] = full_conversation
                participants = Utils.get(full_conversation, "participants")
                indexed_windows = Utils.get(full_conversation, "indexed_windows")
                # Large number of windows were adversely impacting weight sync time, so limit to windows subset until local cache is ready.
                indexed_windows_subset = random.sample(indexed_windows, num_windows_per_convo)
                for idx, indexed_window in enumerate(indexed_windows_subset):
                    piece_data = {
                        "cguid": conversation_guid,
                        "window_idx": indexed_window[0],
                        "window": indexed_window[1],
                        "participants": participants,
                        "batch_num": batch_num
                    }
                    pieces.append(piece_data)

            bt.logging.info(f"Generating metadata for {len(pieces)} pieces")
            # Randomly shuffle all of the pieces
            random.shuffle(pieces)

            # Make sure we have at least 10 valid pieces
            if len(pieces) < 10:
                bt.logging.error(f"Not enough conversation pieces received from endpoint: {len(pieces)}. Aborting.")
                return False

            for piece_idx, piece in enumerate(pieces):
                conversation_guid = piece['cguid']
                conversation_window = piece['window']
                window_idx = piece['window_idx']
                batch_num = piece['batch_num']
                full_conversation = bufferedConvos[conversation_guid]
                if not "metadata" in full_conversation:
                    if test_mode:
                        print(f"No metadata cached for {conversation_guid}. Processing metadata...")
                    full_conversation_metadata = await vl.get_convo_metadata(conversation_guid, full_conversation, batch_num=batch_num)
                    if full_conversation_metadata:
                        full_conversation["metadata"] = full_conversation_metadata
                        llm_type = "openai"
                        model = "gpt-4o"
                        llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")
                        if llm_type_override:
                            llm_type = llm_type_override
                            model = c.get("env", "OPENAI_MODEL")

                        full_convo_tags = Utils.get(full_conversation_metadata, "tags", [])
                        full_convo_vectors = Utils.get(full_conversation_metadata, "vectors", {})
                        full_conversation_tag_count = len(full_convo_tags)
                        lines = Utils.get(full_conversation, "lines", [])
                        participants = Utils.get(full_conversation, "participants")
                        miners_per_window = c.get("validator", "miners_per_window", 6)
                        min_lines = c.get("convo_window", "min_lines", 5)
                        max_lines = c.get("convo_window", "max_lines", 10)
                        overlap_lines = c.get("convo_window", "overlap_lines", 2)
                        validatorHotkey = "FINDHOTKEY-"
                        try:
                            validatorHotkey = str(self.axon.wallet.hotkey.ss58_address)
                        except:
                            pass

                        await vl.put_convo(validatorHotkey, conversation_guid, full_conversation_metadata, type="validator",  batch_num=batch_num, window=999)
                        try:
                            wl.log({
                               "llm_type": llm_type,
                               "model": model,
                               "conversation_guid": "HIDDEN", #conversation_guid,
                               "full_convo_tag_count": full_conversation_tag_count,
                               "num_lines": len(lines),
                               "num_participants": len(participants),
                               "num_convo_windows": -1, #len(conversation_windows),
                               "convo_windows_min_lines": min_lines,
                               "convo_windows_max_lines": max_lines,
                               "convo_windows_overlap_lines": overlap_lines,
                               "netuid": self.config.netuid
                            })
                        except:
                            pass
                else:
                    if test_mode:
                        print(f"FOUND buffered metadata for {conversation_guid}")
                    full_conversation_metadata = full_conversation["metadata"]

                if test_mode:
                    # In test_mode, to expand the miner scores, remove half of the full convo tags.
                    # This "generates" more unique tags found for the miners
                    half = int(len(full_conversation_metadata['tags'])/2)
                    #full_conversation_metadata['tags'] = full_conversation_metadata['tags'][0:half]

                miner_uids = conversationgenome.utils.uids.get_random_uids(
                    self,
                    k= miner_sample_size
                )
                if self.verbose:
                    print(f"miner_uid pool {miner_uids}")
                if len(miner_uids) == 0:
                    bt.logging.error("No miners found.")
                    time.sleep(30)
                    return
                bt.logging.info(f"miner_uid pool {miner_uids}")
                # Create a synapse to distribute to miners
                bt.logging.info(f"Sending convo window {window_idx} of {len(conversation_window)} lines to miners...")

                # To prevent potential miner tracking of conversations, send meaningless guid and idx
                window_packet = {"guid":"HIDDEN", "window_idx":-1, "lines":conversation_window}

                synapse = conversationgenome.protocol.CgSynapse(cgp_input = [window_packet])

                rewards = None

                responses = await self.dendrite.forward(
                    axons=[self.metagraph.axons[uid] for uid in miner_uids],
                    synapse=synapse,
                    deserialize=False,
                )
                if self.verbose:
                    print("RAW RESPONSES", len(responses))

                for response_idx, response in enumerate(responses):
                    if not response.cgp_output:
                        #bt.logging.error(f"BAD RESPONSE: hotkey: {response.axon.hotkey} output: {response.cgp_output}")
                        bt.logging.debug(f"BAD RESPONSE: hotkey: {response.axon.hotkey}")
                        if response.axon.hotkey in hot_key_watchlist:
                            print(f"!!!!!!!!!!! BAD WATCH: {response.axon.hotkey} !!!!!!!!!!!!!")
                        continue
                    try:
                        miner_response = response.cgp_output
                    except:
                        miner_response = response
                    miner_result = miner_response[0]
                    miner_result['original_tags'] = miner_result['tags']

                    # Clean and validate tags for duplicates or whitespace matches
                    miner_result['tags'] = await vl.validate_tag_set(miner_result['original_tags'])

                    miner_result['vectors'] = await vl.get_vector_embeddings_set(miner_result['tags'])
                    #bt.logging.debug(f"GOOD RESPONSE: {response.axon.uuid}, {response.axon.hotkey}, {response.axon}, " )
                    bt.logging.debug(f"GOOD RESPONSE: hotkey: {response.axon.hotkey} from miner response idx: {response_idx} window idx: {window_idx}  tags: {len(miner_result['tags'])} vector count: {len(miner_result['vectors'])} original tags: {len(miner_result['original_tags'])}")
                    if response.axon.hotkey in hot_key_watchlist:
                        print(f"!!!!!!!!!!! GOOD WATCH: {response.axon.hotkey} !!!!!!!!!!!!!")
                    log_path = c.get('env', 'SCORING_DEBUG_LOG')
                    if not Utils.empty(log_path):
                        Utils.append_log(log_path, f"CGP Received tags: {response.cgp_output[0]['tags']} -- PUTTING OUTPUT")
                    await vl.put_convo(response.axon.hotkey, conversation_guid, miner_result, type="miner",  batch_num=batch_num, window=window_idx)

                (final_scores, rank_scores) = await el.evaluate(full_convo_metadata=full_conversation_metadata, miner_responses=responses)


                if final_scores:
                    for idx, score in enumerate(final_scores):
                        if self.verbose:
                            bt.logging.info(f"score {score}")

                        uid=-1
                        try:
                            uid = str(self.metagraph.hotkeys.index(Utils.get(score, "hotkey")))
                        except Exception as e:
                            print(f"ERROR 1162494 -- WandB logging error: {e}")
                        wl.log({
                            "conversation_guid."+uid: "HIDDEN",
                            "window_id."+uid: window_idx,
                            "hotkey."+uid: Utils.get(score, "hotkey"),
                            "adjusted_score."+uid: Utils.get(score, "adjustedScore"),
                            "final_miner_score."+uid: Utils.get(score, "final_miner_score"),
                        })
                        if self.verbose:
                            print("^^^^^^RANK", final_scores, rank_scores, len(final_scores), miner_uids)

                    # Update the scores based on the rewards.
                    self.update_scores(rank_scores, miner_uids)
            return True
        except Exception as e:
            bt.logging.error(f"ERROR 2294374 -- Top Level Validator Error: {e}")
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
        print("Done. Writing final to wandb.")
        wl.end_log_wandb()
