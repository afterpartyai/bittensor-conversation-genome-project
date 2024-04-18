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

        #print("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))

    # Deprecated: remove
    async def calculate_base_score(self, result_dict):
        total_1 = result_dict['total_1']
        total_2 = result_dict['total_2']
        if not total_2:
            print("ERROR: total_2 empty -- nothing to eval")
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
                print("ERROR: normal_pdf --", " x: ", x, " mean: ", mean, " stdev: ", stdev)
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
            print("Found %d convo windows. Sending to miners..." % (numWindows))
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
                bt.logging.info(f"System mode {system_mode} not found. Aborting.")


    async def reserve_conversation(self, minConvWindows = 1):
        # Validator requests a full conversation from the API
        full_conversation = await self.getConvo()
        if self.verbose:
            print("full_conversation", full_conversation)

        if full_conversation:
            conversation_guid = str(Utils.get(full_conversation, "guid"))
            bt.logging.info(f"Reserved conversation ID: {conversation_guid}. Sending to {c.get('env','LLM_TYPE')} LLM...")

            # Do overview tagging and generate base participant profiles
            full_conversation_metadata = await self.generateFullConvoMetaData(full_conversation)
            full_conversation_tags = Utils.get(full_conversation_metadata, "tags", [])
            bt.logging.info(f"Found {len(full_conversation_tags)} tags in FullConvo")

            # Make sure there are enough tags to make processing worthwhile
            minValidTags = self.validateMinimumTags(full_conversation_tags)
            if minValidTags:
                # Break the full conversation up into overlapping conversation windows
                convoWindows = self.getConvoWindows(full_conversation)
                if len(convoWindows) > minConvWindows:
                    return (full_conversation, full_conversation_metadata, convoWindows)
                else:
                    print(f"Not enough convo windows -- only {len(convoWindows)}. Passing.")
            else:
                print("Not enough valid tags for conversation. Passing.")
                return None
        else:
            bt.logging.error("9879432: No conversation returned from API. Aborting.")
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
        print("generateFullConvoMetaData participants", convo['participants'])

        llml = LlmLib()
        matches_dict = await llml.conversation_to_tags(convo)
        tags = list(matches_dict.keys())

        half = int(len(tags) / 2)
        tagsQ = tags[0:half]
        tagsA = tags[half:]
        info = copy.deepcopy(proto)
        #info["interests_of_q"] = tagsQ
        #info["interests_of_a"] = tagsA
        ##print("FullConvo tags",  tags)
        data = {
            "participantProfiles": convo['participants'],
            "tags": tags,
            "tag_vectors": matches_dict,
        }
        return data

    async def sendToMiners(self, convoWindow, minerUids):
        print("Send to miners", minerUids)
        results = []
        ml = MinerLib()
        tasks = [asyncio.create_task(ml.doMining(convoWindow, minerUid)) for minerUid in minerUids]
        await asyncio.wait(tasks)
        for task in tasks:
            results.append(task.result())
        return results

    def validateMinimumTags(self, tags):
        # TODO: Validate tags
        #print("Validating tags", tags)
        return True

    def selectStage1Miners(self, uids, num=3):
        # TODO: Move to MockBt
        selectedMiners = random.sample(uids, num)
        return selectedMiners

    async def outputEmissions(self, convoId, windowId, emissionRewards):
        print("EMISSIONS for %d window %d" % (convoId, windowId), emissionRewards)

    async def send_windows_to_test_miners(self, windows, full_conversation=None, full_conversation_metadata=None):
        cguid = Utils.get(full_conversation, "uid")
        participantProfiles = Utils.get(full_conversation_metadata, "participantProfiles", [])
        full_conversationTags = Utils.get(full_conversation_metadata, "tags", [])
        full_conversationTagVectors = Utils.get(full_conversation_metadata, "tag_vectors", {})

        if self.verbose:
            print("full_conversationTagVectors", full_conversationTagVectors)
        vectorNeightborhood = []
        for key, full_conversationTagVector in full_conversationTagVectors.items():
            #print("full_conversationTagVector", key, full_conversationTagVector)
            vectorNeightborhood.append(full_conversationTagVector['vectors'])
            #print("num vectors", len(full_conversationTagVector['vectors']))

        #print("vectorNeightborhood LEN", len(vectorNeightborhood))
        semantic_neighborhood = np.mean(vectorNeightborhood, axis=0)
        #print("Full convo semantic_neighborhood", semantic_neighborhood)

        if self.verbose:
            print("Full convo tags", full_conversationTags)

        # Loop through rows in db
        success = True
        for idx, window in enumerate(windows):
            # Pick initial minors
            minersPerWindow = c.get("validator", "miners_per_window", 3)
            uids = [1,2,3,4,5,6,7,8,9]
            miners = self.selectStage1Miners(uids, minersPerWindow)
            # Send first window to miners
            minerResults = await self.sendToMiners(window, miners)
            #print("Miner results", minerResults)
            # TODO: Each miner returns data, write data into local db
            # TODO: Write up incomplete errors, such as if timeout happens for miner, send to another miner

            # When all miners have returned data for convo window, score compared to full convo tags
            for minerResult in minerResults:
                uid = Utils.get(minerResult, 'uid')
                tags = Utils.get(minerResult, 'tags')
                vectors = Utils.get(minerResult, 'vectors')
                #print("VECTORS", vectors)
                compareResults = Utils.compare_arrays(full_conversationTags, tags)
                compareResults['total_1'] = len(full_conversationTags)
                compareResults['total_2'] = len(tags)
                #print("COMPARE", compareResults)
                scoreToFullConvo = await self.calculate_base_score(compareResults)
                minerResult['score'] = scoreToFullConvo
                similarity_scores = []
                uniqueTags = compareResults['unique_2']
                if len(uniqueTags) > 0:
                    for unique_tag in uniqueTags:
                        if unique_tag in vectors:
                            tagVectors = vectors[unique_tag]['vectors']
                            #print("VECTOR", unique_tag, tagVectors[0:2])
                            # similarity_score
                            #  0 = orthogonal (perpendicular), no similarity
                            #  1 = identical in orientation, maximum similarity
                            # -1 = diametrically opposed, maximum dissimilarity
                            similarity_score = 0
                            if not Utils.is_empty_vector(tagVectors):
                                similarity_score = np.dot(semantic_neighborhood, tagVectors) / (np.linalg.norm(semantic_neighborhood) * np.linalg.norm(tagVectors))
                                #print(f"Similarity score between the content and the tag '{unique_tag}': {similarity_score}")
                            similarity_scores.append(similarity_score)
                    print("MEDIAN similarity_score of %d unique tags for miner %s" % (len(uniqueTags), str(uid)), np.median(similarity_scores), similarity_scores)
                else:
                    print( "No unique tags for miner %s" % (str(uid)) )

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
        print("Quick test for semantic neighborhood with vectors")
        llml = LlmLib()
        await llml.test_neighborhood()

    async def llm_test(self):
        print("Quick test for LLM")
        llml = LlmLib()
        await llml.test_tagging()


