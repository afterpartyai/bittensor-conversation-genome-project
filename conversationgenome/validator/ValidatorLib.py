verbose = False

import copy
import random
import asyncio
import math
import os
import numpy as np
import json
import sys

from conversationgenome.utils.Utils import Utils
from conversationgenome.utils.uids import check_uid_availability
from conversationgenome.ConfigLib import c

from conversationgenome.miner.MinerLib import MinerLib
from conversationgenome.conversation.ConvoLib import ConvoLib
from conversationgenome.llm.LlmLib import LlmLib
from conversationgenome.mock.MockBt import MockBt

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
try:
    import wandb
except Exception as e:
    print("Wand error")

# TODO: Refactor to multiple participants. Make abstract class?
proto = {
    "interests_of_q": [],
    "hobbies_of_q": [],
    "personality_traits_of_q": [],
    "interests_of_a": [],
    "hobbies_of_a": [],
    "personality_traits_of_a": [],
}


class ValidatorLib:
    mode = "test" # test|local_llm|openai|anthropic
    hotkey = "v1234"
    verbose = False
    llml = None
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

    async def reserve_conversation(self, minConvWindows = 1, batch_num=None, return_indexed_windows=False, verbose=False):
        import time
        out = None
        # Validator requests a full conversation from the API
        full_conversation = await self.getConvo()
        if self.verbose or verbose:
            bt.logging.info(f"full_conversation: {full_conversation}")

        if full_conversation:
            conversation_guid = str(Utils.get(full_conversation, "guid"))
            num_lines = len(Utils.get(full_conversation, 'lines', []))
            llm_type = "openai"
            model = "gpt-4o"
            llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")
            if llm_type_override:
                llm_type = llm_type_override
                model = c.get("env", "OPENAI_MODEL")

            bt.logging.info(f"Reserved conversation with {num_lines} lines. Sending to {llm_type}:{model} LLM...")
            # Break the full conversation up into overlapping conversation windows
            convoWindows = self.getConvoWindows(full_conversation, return_indexed_windows=return_indexed_windows)
            if "min_convo_windows" in full_conversation:
                bt.logging.info(f"Change in minimum required convo windows from API from {minConvWindows} to {full_conversation['min_convo_windows']}.")
                minConvWindows = full_conversation['min_convo_windows']
            if len(convoWindows) > minConvWindows:
                out = full_conversation
            else:
                bt.logging.info(f"Not enough convo windows -- only {len(convoWindows)}. Passing.")
                out = None
            if return_indexed_windows:
                full_conversation['indexed_windows'] = convoWindows
            else:
                full_conversation['windows'] = convoWindows
            return out
        else:
            bt.logging.error(f"ERROR:9879432: No conversation returned from API. Aborting.")
        return None

    async def get_convo_metadata(self, conversation_guid, full_conversation, batch_num):
        # Do overview tagging and generate base participant profiles
        full_conversation_metadata = await self.generate_full_convo_metadata(full_conversation)
        if not full_conversation_metadata:
            bt.logging.error(f"ERROR:927402. No metadata for conversation returned to validator. Aborting.")
            validatorHotkey = "HK-FAIL"
            await self.put_convo("NO-TAGS", conversation_guid, {"tags":[], "vectors":[]}, type="validator", batch_num=batch_num)

            return None
        full_conversation_tags = Utils.get(full_conversation_metadata, "tags", [])
        full_conversation_vectors = Utils.get(full_conversation_metadata, "vectors", [])
        bt.logging.info(f"Found {len(full_conversation_tags)} tags and {len(full_conversation_vectors)} in FullConvo")

        log_path = c.get('env', 'SCORING_DEBUG_LOG')
        if not Utils.empty(log_path):
            Utils.append_log(log_path, f"Validator found full convo tags {full_conversation_tags} in FullConvo")

        # Make sure there are enough tags to make processing worthwhile
        minValidTags = self.validateMinimumTags(full_conversation_tags)
        if not minValidTags:
            bt.logging.info("Not enough valid tags for conversation. Passing.")
            out = None
        else:
            out = full_conversation_metadata
        #await self.end_log_wandb(conversation_guid)
        #return None
        return out

    async def getConvo(self):
        hotkey = self.hotkey
        if not self.readyai_api_key:
            self.read_api_key()
        cl = ConvoLib()
        convo = await cl.get_conversation(hotkey, api_key=self.readyai_api_key)
        return convo

    async def put_convo(self, hotkey, c_guid, data, type="validator", batch_num=None, window=None):
        cl = ConvoLib()
        convo = await cl.put_conversation(hotkey, c_guid, data, type=type, batch_num=batch_num, window=window)
        return convo


    def getConvoWindows(self, fullConvo, return_indexed_windows=False):
        minLines = c.get("convo_window", "min_lines", 5)
        maxLines = c.get("convo_window", "max_lines", 10)
        overlapLines = c.get("convo_window", "overlap_lines", 2)

        windows = Utils.split_overlap_array(fullConvo['lines'], size=maxLines, overlap=overlapLines)
        if len(windows) < 2:
            windows = Utils.split_overlap_array(fullConvo['lines'], size=minLines, overlap=overlapLines)

        # TODO: Write convo windows into local database with full convo metadata
        if return_indexed_windows:
            indexed_windows = []
            for idx, window in enumerate(windows):
                indexed_windows.append((idx, window))
            windows = indexed_windows

        return windows

    async def filter_valid_tags(self, tags):
        # Filter valid tags
        return tags


    async def generate_full_convo_metadata(self, convo):
        if self.verbose:
            bt.logging.info(f"Execute generate_full_convo_metadata for participants {convo['participants']}")
        else:
            bt.logging.info(f"Execute generate_full_convo_metadata")

        llml = LlmLib()
        self.llml = llml
        result = await llml.conversation_to_metadata(convo, generateEmbeddings=True)
        if not result:
            bt.logging.error(f"ERROR:2873226353. No conversation metadata returned. Aborting.")
            return None
        if not Utils.get(result, 'success'):
            bt.logging.error(f"ERROR:2873226354. Conversation metadata failed: {result}. Aborting.")
            return None

        tags = result['tags']
        vectors = Utils.get(result, 'vectors', {})
        data = {
            "participantProfiles": convo['participants'],
            "tags": tags,
            "vectors": vectors,
        }
        return data

    async def get_vector_embeddings_set(self, tags):
        response = await self.llml.get_vector_embeddings_set(tags)
        return response


    async def send_to_miners(self, conversation_guid, window_idx, conversation_window, miner_uids):
        bt.logging.info(f"Send to conversation window {window_idx} to miners: {miner_uids}")
        results = []
        ml = MinerLib()
        tasks = [asyncio.create_task(ml.do_mining(conversation_guid, window_idx, conversation_window, minerUid)) for minerUid in miner_uids]
        await asyncio.wait(tasks)
        for task in tasks:
            results.append(task.result())
        return results

    def validateMinimumTags(self, tags):
        # TODO: Validate tags
        #bt.logging.info(f"Validating tags: {tags}")
        return True

    def selectStage1Miners(self, uids, num=3):
        # TODO: Move to MockBt
        selectedMiners = random.sample(uids, num)
        return selectedMiners

    async def outputEmissions(self, convoId, windowId, emissionRewards):
        bt.logging.info(f"EMISSIONS for {convoId} window {windowId}: {emissionRewards}")

    async def send_windows_to_test_miners(self, windows, full_conversation=None, full_conversation_metadata=None):
        conversation_guid = Utils.get(full_conversation, "uid")
        participantProfiles = Utils.get(full_conversation_metadata, "participantProfiles", [])
        full_conversationTags = Utils.get(full_conversation_metadata, "tags", [])
        full_conversationTagVectors = Utils.get(full_conversation_metadata, "tag_vectors", {})

        if self.verbose:
            bt.logging.info(f"full_conversationTagVectors: {full_conversationTagVectors}")
        vectorNeightborhood = []
        for key, full_conversationTagVector in full_conversationTagVectors.items():
            #bt.logging.info(f"full_conversationTagVector: {key}, {full_conversationTagVector}")
            vectorNeightborhood.append(full_conversationTagVector['vectors'])
            #bt.logging.info(f"num vectors: {len(full_conversationTagVector['vectors'])}")

        #bt.logging.info(f"vectorNeightborhood LEN: {len(vectorNeightborhood)}")
        semantic_neighborhood = np.mean(vectorNeightborhood, axis=0)
        #bt.logging.info(f"Full convo semantic_neighborhood: {semantic_neighborhood}")

        if self.verbose:
            bt.logging.info(f"Full convo tags: {full_conversationTags}")

        # Loop through rows in db
        success = True
        for idx, window in enumerate(windows):
            # Pick initial minors
            minersPerWindow = c.get("validator", "miners_per_window", 3)
            uids = [1,2,3,4,5,6,7,8,9]
            miners = self.selectStage1Miners(uids, minersPerWindow)
            # Send first window to miners
            miner_results = await self.send_to_miners(conversation_guid, idx, window, miners)
            #bt.logging.info(f"Miner results: {minerResults}")
            # TODO: Each miner returns data, write data into local db
            # TODO: Write up incomplete errors, such as if timeout happens for miner, send to another miner

            # When all miners have returned data for convo window, score compared to full convo tags
            for minerResult in minerResults:
                uid = Utils.get(minerResult, 'uid')
                tags = Utils.get(minerResult, 'tags')
                bt.logging.info(f"Generate vectors from {len(tags)} miner tags")

                vectors = Utils.get(minerResult, 'vectors')
                compareResults = Utils.compare_arrays(full_conversationTags, tags)
                compareResults['total_1'] = len(full_conversationTags)
                compareResults['total_2'] = len(tags)
                #bt.logging.info(f"COMPARE: {compareResults}")
                scoreToFullConvo = await self.calculate_base_score(compareResults)
                minerResult['score'] = scoreToFullConvo
                similarity_scores = []
                uniqueTags = compareResults['unique_2']
                if len(uniqueTags) > 0:
                    for unique_tag in uniqueTags:
                        if unique_tag in vectors:
                            tagVectors = vectors[unique_tag]['vectors']
                            #bt.logging.info(f"VECTOR: {unique_tag}, {tagVectors[0:2]}")
                            # similarity_score
                            #  0 = orthogonal (perpendicular), no similarity
                            #  1 = identical in orientation, maximum similarity
                            # -1 = diametrically opposed, maximum dissimilarity
                            similarity_score = 0
                            if not Utils.is_empty_vector(tagVectors):
                                similarity_score = np.dot(semantic_neighborhood, tagVectors) / (np.linalg.norm(semantic_neighborhood) * np.linalg.norm(tagVectors))
                                #bt.logging.info(f"Similarity score between the content and the tag '{unique_tag}': {similarity_score}")
                            similarity_scores.append(similarity_score)
                    bt.logging.info(f"MEDIAN similarity_score of {len(uniqueTags)} unique tags for miner {str(uid)}: {np.median(similarity_scores)}, {similarity_scores}")
                else:
                    bt.logging.info(f"No unique tags for miner {str(uid)}")

            await self.calculate_emission_rewards(minerResults, 'score')

            rewards = {}
            for minerResult in minerResults:
                rewards[minerResult['uid']] = minerResult['reward']
            # Send emissions
            await self.outputEmissions(1, idx, rewards)

        if success == True:
            cl = ConvoLib()
            await cl.markConversionComplete(self.hotkey, cguid)

    async def neighborhood_test(self):
        bt.logging.info("Quick test for semantic neighborhood with vectors")
        llml = LlmLib()
        await llml.test_neighborhood()

    async def llm_test(self):
        bt.logging.info("Quick test for LLM")
        llml = LlmLib()
        await llml.test_tagging()


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

        # Update EMA scores
        alpha: float = moving_average_alpha
        ema_scores = alpha * scattered_rewards + (1 - alpha) * ema_scores

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


    async def prompt_call_csv(self, convoXmlStr=None, participants=None, override_prompt=None):
        llml = LlmLib()
        return await llml.prompt_call_csv(convoXmlStr, participants, override_prompt)

    async def validate_tag_set(self, originalTagList):
        cleanTagList = Utils.get_clean_tag_set(originalTagList)

        if len(cleanTagList) >= 20:
            random_indices = random.sample(range(len(cleanTagList)), 20)
            cleanTagList = [cleanTagList[i] for i in random_indices]
        else:
            if self.verbose:
                bt.logging.warning("cleanTagList has fewer than 20 elements. Skipping random selection.")

        cleanTagList = [tag[:50] for tag in cleanTagList]

        if self.verbose:
            print(f"Original tag set len: {len(originalTagList)} clean tag set len: {len(cleanTagList)}")
        cleanTagsStr = ",".join(cleanTagList)

        # Tag validation prompt
        prompt1 = "Separate these keywords into 2 groups: good English keywords and malformed keywords. Malformed keywords should include combined/compound words that are not in the English Dictionary, abbreviations, and typos. Return two comma-delimited lists."
        prompt1 += f"\n\n<keywords>\n{cleanTagsStr}\n</keywords>\n\n"

        response = await self.prompt_call_csv(override_prompt=prompt1)
        if len(response['content']) == 0:
            print(f"EMPTY RESPONSE -- no valid tags: {response['content']}")
            return None
        contentStr = response['content'].lower()
        goodPos = contentStr.find("good")
        malformedPos = contentStr.find("malformed")
        goodKeywordsStr = contentStr[0:malformedPos].replace("good english keywords:", "").replace("***","").replace("\n","").strip()
        validTags = goodKeywordsStr.split(",")
        validTags = Utils.get_clean_tag_set(validTags)

        processed_tag_list = [element for element in validTags if element in cleanTagsStr]

        return processed_tag_list

    def transposed_cubic_distribution(self, i, num_uids):
        # Calculate the range of x values
        y_min, y_max = 0.001, 0.003

        # Normalize i to the range [-1, 1] with the middle index at the inflection point
        x_normalized = (2 * (num_uids - i - 1) / num_uids) - 1

        # Apply the cubic function
        y_normalized = x_normalized ** 3

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

        #Calculate proper length for calculating weight values
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

