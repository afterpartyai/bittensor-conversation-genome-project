verbose = False

import json
import os
import random
from typing import Any
from typing import Optional

import numpy as np

from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib
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
    bt.logging.enable_debug(True)
elif c.get('env', 'FORCE_LOG') == 'info':
    bt.logging.enable_default(True)


class ValidatorLib:
    mode = "test"  # test|local_llm|openai|anthropic
    hotkey = "v1234"
    verbose = False
    llml = LlmLib()
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

    # ############
    # old stuff below to ensure backward compatibility
    # ############

    async def reserve_conversation(self, minConvWindows=1, batch_num=None, return_indexed_windows=False, verbose=False) -> Conversation | None:
        out = None
        # Validator requests a full conversation from the API
        full_conversation: Conversation = await self.getConvo()

        if self.verbose or verbose:
            bt.logging.info(f"full_conversation: {full_conversation}")

        if full_conversation:
            num_lines = len(full_conversation.lines)
            llm_type = "openai"
            model = "gpt-4o"
            llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")

            if llm_type_override:
                llm_type = llm_type_override
                model = c.get("env", "OPENAI_MODEL")

            bt.logging.info(f"Reserved conversation with {num_lines} lines. Sending to {llm_type}:{model} LLM...")
            # Break the full conversation up into overlapping conversation windows
            convoWindows = self.getConvoWindows(full_conversation, return_indexed_windows=return_indexed_windows)

            if full_conversation.min_convo_windows is not None and full_conversation.min_convo_windows >= 0:
                bt.logging.info(f"Change in minimum required convo windows from API " f"from {minConvWindows} to {full_conversation.min_convo_windows}.")
                minConvWindows = full_conversation.min_convo_windows

            if len(convoWindows) > minConvWindows:
                out = full_conversation
            else:
                bt.logging.info(f"Not enough convo windows -- only {len(convoWindows)}. Passing.")
                out = None

            if return_indexed_windows:
                full_conversation.indexed_windows = convoWindows
            else:
                full_conversation.windows = convoWindows

            return out
        else:
            bt.logging.error(f"ERROR:9879432: No conversation returned from API. Aborting.")

        return None

    async def get_convo_metadata(self, conversation_guid: str, full_conversation: Conversation, batch_num: int) -> ConversationMetadata | None:
        # Do overview tagging and generate base participant profiles
        full_conversation_metadata: ConversationMetadata = await self.generate_full_convo_metadata(convo=full_conversation)

        if not full_conversation_metadata:
            bt.logging.error(f"ERROR:927402. No metadata for conversation returned to validator. Aborting.")
            await self.put_convo("NO-TAGS", conversation_guid, {"tags": [], "vectors": []}, type="validator", batch_num=batch_num)
            return None

        full_conversation_tags = getattr(full_conversation_metadata, "tags", [])
        full_conversation_vectors = getattr(full_conversation_metadata, "vectors", [])
        bt.logging.info(f"Found {len(full_conversation_tags)} tags and {len(full_conversation_vectors)} in FullConvo")

        # Make sure there are enough tags to make processing worthwhile
        minValidTags = self.validateMinimumTags(full_conversation_tags)
        if not minValidTags:
            bt.logging.info("Not enough valid tags for conversation. Passing.")
            out = None
        else:
            out = full_conversation_metadata

        return out

    async def getConvo(self) -> Conversation:
        hotkey = self.hotkey

        if not self.readyai_api_key:
            self.read_api_key()

        cl = ConvoLib()
        convo: Conversation = await cl.get_conversation(hotkey, api_key=self.readyai_api_key)

        return convo

    async def put_convo(self, hotkey, c_guid, data, type="validator", batch_num=None, window=None):
        cl = ConvoLib()
        convo = await cl.put_conversation(hotkey, c_guid, data, type=type, batch_num=batch_num, window=window)
        return convo

    def getConvoWindows(self, fullConvo: Conversation, return_indexed_windows=False):
        minLines = c.get("convo_window", "min_lines", 5)
        maxLines = c.get("convo_window", "max_lines", 10)
        overlapLines = c.get("convo_window", "overlap_lines", 2)

        windows = Utils.split_overlap_array(fullConvo.lines, size=maxLines, overlap=overlapLines)
        if len(windows) < 2:
            windows = Utils.split_overlap_array(fullConvo.lines, size=minLines, overlap=overlapLines)

        # TODO: Write convo windows into local database with full convo metadata
        if return_indexed_windows:
            indexed_windows = []

            for idx, window in enumerate(windows):
                indexed_windows.append((idx, window))
            windows = indexed_windows

        return windows

    async def generate_full_convo_metadata(self, convo: Conversation) -> ConversationMetadata | None:
        if self.verbose:
            bt.logging.info(f"Execute generate_full_convo_metadata for participants {convo.participants}")
        else:
            bt.logging.info(f"Execute generate_full_convo_metadata")

        llml = LlmLib()
        self.llml = llml
        result: RawMetadata = await llml.conversation_to_metadata(convo, generateEmbeddings=True)

        if not result:
            bt.logging.error(f"ERROR:2873226353. No conversation metadata returned. Aborting.")
            return None

        if not result.success:
            bt.logging.error(f"ERROR:2873226354. Conversation metadata failed: {result}. Aborting.")
            return None

        return ConversationMetadata(
            participantProfiles=convo.participants,
            tags=getattr(result, "tags", []),
            vectors=getattr(result, "vectors", {}),
        )

    def validateMinimumTags(self, tags):
        return True

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
        goodKeywordsStr = contentStr[0:malformedPos].replace("good english keywords:", "").replace("***", "").replace("\n", "").strip()
        validTags = goodKeywordsStr.split(",")
        validTags = Utils.get_clean_tag_set(validTags)

        processed_tag_list = [element for element in validTags if element in cleanTagsStr]

        return processed_tag_list

    async def get_vector_embeddings_set(self, tags):
        response = await self.llml.get_vector_embeddings_set(tags)
        return response
