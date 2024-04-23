verbose = False

import copy
import random
import asyncio
import math
import os
import numpy as np


from conversationgenome.Utils import Utils
from conversationgenome.MinerLib import MinerLib
from conversationgenome.ConvoLib import ConvoLib
from conversationgenome.LlmLib import LlmLib
from conversationgenome.ConfigLib import c
from conversationgenome.MockBt import MockBt

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()

import wandb

# xxx Refactor to multiple participants. Make abstract class?
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

    def __init__(self):
        super(ValidatorLib, self).__init__()

        #bt.logging.info("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))

    # Deprecated: remove
    async def calculate_base_score(self, result_dict):
        total_1 = result_dict['total_1']
        total_2 = result_dict['total_2']
        if not total_2:
            bt.logging.info("ERROR: total_2 empty -- nothing to eval")
            return 0

        unique_1_count = len(result_dict['unique_1'])
        unique_2_count = len(result_dict['unique_2'])
        both_count = len(result_dict['both'])

        # If all elements match, return a very low score
        if unique_1_count == 0 and unique_2_count == 0:
            return 0.1

        # If a large percentage of array 2 is unique, return a low score
        unique_2_ratio = unique_2_count / total_2
        if unique_2_ratio > 0.5:
            return 0.2

        # Calculate the percentage of matches
        matches_ratio = both_count / max(total_1, total_2)

        # Calculate the percentage of desired unique elements in array 2
        desired_unique_ratio = min(unique_2_count / (total_1 + unique_2_count), 0.2)

        # Combine the two ratios to get the final score
        score = (matches_ratio * 0.8) + (desired_unique_ratio * 0.2)

        return score

    # Deprecated: remove
    async def calculate_emission_rewards(self, dicts, scoreKey):
        scores = Utils.pluck(dicts, scoreKey)
        total_scores = sum(scores)
        mean = total_scores / len(scores)
        stdev = math.sqrt(sum((x - mean) ** 2 for x in scores) / len(scores))

        def normal_pdf(x, mean, stdev):
            normal = 0
            try:
                normal = math.exp(-(x - mean) ** 2 / (2 * stdev ** 2)) / (stdev * math.sqrt(2 * math.pi))
            except:
                bt.logging.error(f"ERROR:84921793 normal_pdf --", " x: ", x, " mean: ", mean, " stdev: ", stdev)
            return normal

        rewards = []
        for cur_dict in dicts:
            score = Utils.get(cur_dict, scoreKey)
            pdf_value = normal_pdf(score, mean, stdev)
            if stdev == 0:
                reward_percentage = 0
            else:
                reward_percentage = pdf_value / sum(normal_pdf(x, mean, stdev) for x in scores)
            cur_dict['reward'] = reward_percentage
            rewards.append(reward_percentage)

        return rewards

    async def conversation_process_start(self):
        result = await self.reserve_conversation()
        if result:
            (full_conversation, full_conversation_metadata, convoWindows) = result

            wandb_data = {"hello":"world"}
            wandb.loBg(wandb_data)
            bt.logging.info("WANDB_API_KEY is set")
            runs = api.runs(f"conversationgenome/{project}")
            bt.logging.info("Found %d convo windows. Sending to miners..." % (numWindows))
            system_mode = c.get('system', 'mode')
            if system_mode == 'test':
                await self.send_windows_to_test_miners(convoWindows, full_conversation=full_conversation, full_conversation_metadata=full_conversation_metadata)
            elif system_mode == 'openai':
                return {
                    "full_conversation": full_conversation,
                    "full_conversation_metadata": full_conversationMetaData,
                    "windows": convoWindows,
                }
            else:
                bt.logging.error(f"ERROR:287323487. System mode {system_mode} not found. Aborting.")

    async def begin_log_wandb(self, c_guid):
        api = wandb.Api()
        wandb_api_key = c.get("env", "WANDB_API_KEY")
        if not wandb_api_key:
            raise ValueError("Please log in to wandb using `wandb login` or set the WANDB_API_KEY environment variable.")
        run = 5
        bt.logging.info("INIT", wandb_api_key)
        epochs = 10
        wandb.init(
              # Set the project where this run will be logged
              project="cgp_test_run",
              # We pass a run name (otherwise it’ll be randomly assigned, like sunshine-lollypop-10)
              name=f"conversationgenome/cguid_{c_guid}",
              # Track hyperparameters and run metadata
              config={
              "learning_rate": 0.02,
              "architecture": "CNN",
              "dataset": "CIFAR-100",
              "epochs": epochs,
        })
    async def do_log_wandb(self, c_guid):
        print("Do log....")
        epochs = 10
        offset = random.random() / 5
        for epoch in range(2, epochs):
            acc = 1 - 2 ** -epoch - random.random() / epoch - offset
            loss = 2 ** -epoch + random.random() / epoch + offset

            wandb.log({"acc": acc, "loss": loss})
        wandb.log({"miner_uuid":10, "miner_hotkey":"a8348-123123", "score": random.random()})

    async def end_log_wandb(self, c_guid):
        # Mark the run as finished
        wandb.finish()

    async def log_wandb_finish(self):
        epochs = 2
        offset = random.random() / 5
        for epoch in range(2, epochs):
            acc = 1 - 2 ** -epoch - random.random() / epoch - offset
            loss = 2 ** -epoch + random.random() / epoch + offset

            wandb.log({"acc": acc, "loss": loss})

        # Mark the run as finished
        wandb.finish()


    async def reserve_conversation(self, minConvWindows = 1):
        import time
        out = None
        # Validator requests a full conversation from the API
        full_conversation = await self.getConvo()
        if self.verbose:
            bt.logging.info("full_conversation", full_conversation)

        if full_conversation:
            conversation_guid = str(Utils.get(full_conversation, "guid"))
            await self.begin_log_wandb(conversation_guid)
            #for i in range(5):
            #    await self.do_log_wandb(conversation_guid)
            #    time.sleep(2)
            #await self.end_log_wandb(conversation_guid)
            #return None
            bt.logging.info(f"Reserved conversation ID: {conversation_guid}. Sending to {c.get('env','LLM_TYPE')} LLM...")

            # Do overview tagging and generate base participant profiles
            full_conversation_metadata = await self.generateFullConvoMetaData(full_conversation)
            if not full_conversation_metadata:
                bt.logging.error(f"ERROR:927402. No metadata for conversation returned to validator. Aborting.")
                return None
            full_conversation_tags = Utils.get(full_conversation_metadata, "tags", [])
            bt.logging.info(f"Found {len(full_conversation_tags)} tags in FullConvo")

            # Make sure there are enough tags to make processing worthwhile
            minValidTags = self.validateMinimumTags(full_conversation_tags)
            if minValidTags:
                # Break the full conversation up into overlapping conversation windows
                convoWindows = self.getConvoWindows(full_conversation)
                if len(convoWindows) > minConvWindows:
                    out = (full_conversation, full_conversation_metadata, convoWindows)
                else:
                    bt.logging.info(f"Not enough convo windows -- only {len(convoWindows)}. Passing.")
                    out = None
            else:
                bt.logging.info("Not enough valid tags for conversation. Passing.")
                out = None
            #await self.end_log_wandb(conversation_guid)
            #return None
            return out
        else:
            bt.logging.error(f"ERROR:9879432: No conversation returned from API. Aborting.")
        return None

    async def getConvo(self):
        hotkey = self.hotkey
        cl = ConvoLib()
        convo = await cl.get_conversation(hotkey)
        return convo

    def getConvoWindows(self, fullConvo):
        minLines = c.get("convo_window", "min_lines", 5)
        maxLines = c.get("convo_window", "max_lines", 10)
        overlapLines = c.get("convo_window", "overlap_lines", 2)

        windows = Utils.split_overlap_array(fullConvo['lines'], size=maxLines, overlap=overlapLines)
        if len(windows) < 2:
            windows = Utils.split_overlap_array(fullConvo['lines'], size=minLines, overlap=overlapLines)

        # TODO: Write convo windows into local database with full convo metadata
        return windows



    async def generateFullConvoMetaData(self, convo):
        #cl = ConvoLib()
        bt.logging.info("generateFullConvoMetaData participants", convo['participants'])

        llml = LlmLib()
        result = await llml.conversation_to_metadata(convo)
        if not result:
            bt.logging.error(f"ERROR:2873226353. No conversation metadata returned. Aborting.")
            return None
        tags = result['tags']
        vectors = Utils.get(result, 'vectors', {})
        #half = int(len(tags) / 2)
        #tagsQ = tags[0:half]
        #tagsA = tags[half:]
        #info = copy.deepcopy(proto)
        #info["interests_of_q"] = tagsQ
        #info["interests_of_a"] = tagsA
        ##bt.logging.info("FullConvo tags",  tags)
        data = {
            "participantProfiles": convo['participants'],
            "tags": tags,
            "vectors": vectors,
        }
        return data

    async def send_to_miners(self, conversation_guid, window_idx, conversation_window, miner_uids):
        bt.logging.info("Send to miners", miner_uids)
        results = []
        ml = MinerLib()
        tasks = [asyncio.create_task(ml.do_mining(conversation_guid, window_idx, conversation_window, minerUid)) for minerUid in miner_uids]
        await asyncio.wait(tasks)
        for task in tasks:
            results.append(task.result())
        return results

    def validateMinimumTags(self, tags):
        # TODO: Validate tags
        #bt.logging.info("Validating tags", tags)
        return True

    def selectStage1Miners(self, uids, num=3):
        # TODO: Move to MockBt
        selectedMiners = random.sample(uids, num)
        return selectedMiners

    async def outputEmissions(self, convoId, windowId, emissionRewards):
        bt.logging.info("EMISSIONS for %d window %d" % (convoId, windowId), emissionRewards)

    async def send_windows_to_test_miners(self, windows, full_conversation=None, full_conversation_metadata=None):
        conversation_guid = Utils.get(full_conversation, "uid")
        participantProfiles = Utils.get(full_conversation_metadata, "participantProfiles", [])
        full_conversationTags = Utils.get(full_conversation_metadata, "tags", [])
        full_conversationTagVectors = Utils.get(full_conversation_metadata, "tag_vectors", {})

        if self.verbose:
            bt.logging.info("full_conversationTagVectors", full_conversationTagVectors)
        vectorNeightborhood = []
        for key, full_conversationTagVector in full_conversationTagVectors.items():
            #bt.logging.info("full_conversationTagVector", key, full_conversationTagVector)
            vectorNeightborhood.append(full_conversationTagVector['vectors'])
            #bt.logging.info("num vectors", len(full_conversationTagVector['vectors']))

        #bt.logging.info("vectorNeightborhood LEN", len(vectorNeightborhood))
        semantic_neighborhood = np.mean(vectorNeightborhood, axis=0)
        #bt.logging.info("Full convo semantic_neighborhood", semantic_neighborhood)

        if self.verbose:
            bt.logging.info("Full convo tags", full_conversationTags)

        # Loop through rows in db
        success = True
        for idx, window in enumerate(windows):
            # Pick initial minors
            minersPerWindow = c.get("validator", "miners_per_window", 3)
            uids = [1,2,3,4,5,6,7,8,9]
            miners = self.selectStage1Miners(uids, minersPerWindow)
            # Send first window to miners
            miner_results = await self.send_to_miners(conversation_guid, idx, window, miners)
            #bt.logging.info("Miner results", minerResults)
            # TODO: Each miner returns data, write data into local db
            # TODO: Write up incomplete errors, such as if timeout happens for miner, send to another miner

            # When all miners have returned data for convo window, score compared to full convo tags
            for minerResult in minerResults:
                uid = Utils.get(minerResult, 'uid')
                tags = Utils.get(minerResult, 'tags')
                vectors = Utils.get(minerResult, 'vectors')
                #bt.logging.info("VECTORS", vectors)
                compareResults = Utils.compare_arrays(full_conversationTags, tags)
                compareResults['total_1'] = len(full_conversationTags)
                compareResults['total_2'] = len(tags)
                #bt.logging.info("COMPARE", compareResults)
                scoreToFullConvo = await self.calculate_base_score(compareResults)
                minerResult['score'] = scoreToFullConvo
                similarity_scores = []
                uniqueTags = compareResults['unique_2']
                if len(uniqueTags) > 0:
                    for unique_tag in uniqueTags:
                        if unique_tag in vectors:
                            tagVectors = vectors[unique_tag]['vectors']
                            #bt.logging.info("VECTOR", unique_tag, tagVectors[0:2])
                            # similarity_score
                            #  0 = orthogonal (perpendicular), no similarity
                            #  1 = identical in orientation, maximum similarity
                            # -1 = diametrically opposed, maximum dissimilarity
                            similarity_score = 0
                            if not Utils.is_empty_vector(tagVectors):
                                similarity_score = np.dot(semantic_neighborhood, tagVectors) / (np.linalg.norm(semantic_neighborhood) * np.linalg.norm(tagVectors))
                                #bt.logging.info(f"Similarity score between the content and the tag '{unique_tag}': {similarity_score}")
                            similarity_scores.append(similarity_score)
                    bt.logging.info("MEDIAN similarity_score of %d unique tags for miner %s" % (len(uniqueTags), str(uid)), np.median(similarity_scores), similarity_scores)
                else:
                    bt.logging.info( "No unique tags for miner %s" % (str(uid)) )

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


