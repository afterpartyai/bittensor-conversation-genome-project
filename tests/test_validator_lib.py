import pytest
import random

from conversationgenome.ConfigLib import c
from conversationgenome.utils.Utils import Utils

from conversationgenome.validator.ValidatorLib import ValidatorLib
from conversationgenome.validator.evaluator import Evaluator
from conversationgenome.analytics.WandbLib import WandbLib
from conversationgenome.mock.MockBt import MockBt

verbose = True

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()



class MockAxon:
    uuid = "a"
    hotkey = ""


class MockResponse:
    responses = {}
    responses = {}
    cgp_output = None
    axon = None

    def __init__(self):
        self.axon = MockAxon()



@pytest.mark.asyncio
async def test_full():
    wandb_enabled = Utils._int(c.get('env', 'WAND_ENABLED'), 1)
    if wandb_enabled:
        wl = WandbLib()
        wl.init_wandb()
    # Config variables
    c.set('system', 'mode', 'test')

    # Create test set of miner IDs so minimum miner checker doesn't error out
    miner_uids = [1,2,3,4,5,6,7,8,9]
    batch_num = random.randint(100000, 9999999)

    vl = ValidatorLib()
    el = Evaluator()
    num_convos_per_buffer = c.get("validator", "num_convos_per_buffer", 10)
    num_windows_per_convo = c.get("validator", "num_windows_per_convo", 5)
    bufferedConvos = {}
    pieces = []
    for i in range(num_convos_per_buffer):
        full_conversation = await vl.reserve_conversation(batch_num=batch_num, return_indexed_windows=True)
        if not full_conversation:
            continue
        conversation_guid = str(Utils.get(full_conversation, "guid"))
        bufferedConvos[conversation_guid] = full_conversation
        participants = Utils.get(full_conversation, "participants")
        indexed_windows = Utils.get(full_conversation, "windows")
        # Large number of windows were adversely impacting weight sync time, so limit to windows subset until local cache is ready.
        indexed_windows_subset = random.sample(indexed_windows, num_windows_per_convo)
        for idx, indexed_window in enumerate(indexed_windows_subset):
            pieces.append({"cguid":conversation_guid, "window_idx":indexed_window[0], "window":indexed_window[1], "participants":participants})
        #full_conversation["windows"] = indexed_windows_subset

    bt.logging.info(f"Generating metadata for {len(pieces)} pieces")
    random.shuffle(pieces)
    if False:
        print(f"Number of pieces: {len(pieces)} windows from last convo:{len(indexed_windows)}")
        for piece in pieces[0:5]:
            print(f"Window piece: {piece['cguid']} / {piece['window_idx']}")
    test_mode = True
    # Make sure we have at least 10 valid pieces
    if len(pieces) > 10:
        miners_per_window = c.get("validator", "miners_per_window", 6)

        # Loop through conversation window pieces. Send each window piece to multiple miners
        #for window_idx, conversation_window in enumerate(conversation_windows):
        for piece_idx, piece in enumerate(pieces):
            conversation_guid = piece['cguid']
            conversation_window = piece['window']
            window_idx = piece['window_idx']
            full_conversation = bufferedConvos[conversation_guid]
            if not "metadata" in full_conversation:
                print(f"No metadata for {conversation_guid}")
                full_conversation_metadata = await vl.get_convo_metadata(conversation_guid, full_conversation, batch_num=batch_num)
                if full_conversation_metadata:
                    full_conversation["metadata"] = full_conversation_metadata
                    llm_type = "openai"
                    model = "gpt-4o"
                    llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")
                    if llm_type_override:
                        llm_type = llm_type_override
                        model = c.get("env", "OPENAI_MODEL")
                    conversation_guid = Utils.get(full_conversation, "guid")
                    tags = Utils.get(full_conversation_metadata, "tags", [])
                    vectors = Utils.get(full_conversation_metadata, "vectors", [])
                    full_conversation_tag_count = len(tags)
                    lines = Utils.get(full_conversation, "lines", [])
                    participants = Utils.get(full_conversation, "participants", [])
                    min_lines = c.get("convo_window", "min_lines", 5)
                    max_lines = c.get("convo_window", "max_lines", 50)
                    overlap_lines = c.get("convo_window", "overlap_lines", 2)

                    validatorHotkey = "VHK-0"

                    #await vl.put_convo(validatorHotkey, conversation_guid, {"tags":tags, "vectors":vectors}, type="validator", batch_num=batch_num, window=999)
                    conversation_windows = Utils.get(full_conversation, "windows")

                    if wandb_enabled:
                        wl.log({
                           "llm_type": llm_type,
                           "model": model,
                           "conversation_guid": conversation_guid,
                           "full_convo_tag_count": full_conversation_tag_count,
                           "num_lines": len(lines),
                           "num_participants": len(participants),
                           "num_convo_windows": len(conversation_windows),
                           "convo_windows_min_lines": min_lines,
                           "convo_windows_max_lines": max_lines,
                           "convo_windows_overlap_lines": overlap_lines,
                           "netuid": -1
                        })
                    if llm_type == "spacy":
                        bt.logging.debug("SPACY TEST MODE -- remove half of the full convo tags")
                        # In test_mode, to expand the miner scores, remove half of the full convo tags.
                        # This "generates" more unique tags found for the miners
                        half = int(len(full_conversation_metadata['tags'])/2)
                        full_conversation_metadata['tags'] = full_conversation_metadata['tags'][0:half]

                    bt.logging.info(f"Found {len(conversation_windows)} conversation windows. Sequentially sending to batches of {miners_per_window} miners")
            else:
                print(f"FOUND metadata for {conversation_guid}")
                full_conversation_metadata = full_conversation["metadata"]

            window_idx = piece['window_idx']

            selected_miner_uids = vl.selectStage1Miners(miner_uids, num=miners_per_window)
            bt.logging.debug(f"Sending conversation_window {window_idx} for piece {piece_idx} to selected miners: {selected_miner_uids}")

            miner_results = await vl.send_to_miners(conversation_guid, window_idx, conversation_window, selected_miner_uids)
            mock_miner_responses = []
            tagVectors = {}
            bt.logging.info(f"Test Validator generating vectors from miner tags...")
            for idx, miner_result in enumerate(miner_results):
                miner_result['original_tags'] = miner_result['tags']

                # Append a couple of "unclean" test tags to make sure they are removed for scoring
                miner_result['original_tags'].append(miner_result['original_tags'][0]+"    ")
                miner_result['original_tags'].append("    "+miner_result['original_tags'][0])

                # Clean and validate tags for duplicates or whitespace matches
                miner_result['tags'] = await vl.validate_tag_set(miner_result['original_tags'])
                print("TAGS", miner_result['original_tags'], "->", miner_result['tags'])

                miner_result['vectors'] = await vl.get_vector_embeddings_set(miner_result['tags'])
                bt.logging.info(f"RESULTS from miner idx: {idx} uid: {miner_result['uid']}, clean tags: {len(miner_result['tags'])} vector count: {len(miner_result['vectors'])} , original tags: {len(miner_result['original_tags'])}")

                #bt.logging.debug(f"RESULTS from miner idx: {idx} uid: {miner_result['uid']}, tags: {miner_result['tags']} vector count: {len(miner_result['vectors'])}")
                response = MockResponse()
                response.axon.hotkey = "HK-"+str(idx)
                response.axon.uuid = str(miner_result['uid'])
                response.cgp_output = [miner_result]
                #bt.logging.debug(f"PUTting output to Api... CGP Received tags: {response.cgp_output[0]['tags']}")
                await vl.put_convo(response.axon.hotkey, conversation_guid, response.cgp_output[0], type="miner", batch_num=batch_num, window=idx)

                mock_miner_responses.append(response)
            # Evaluate results of miners
            (final_scores, rank_scores) = await el.evaluate(full_conversation_metadata, mock_miner_responses)
            if final_scores:
                for idx, score in enumerate(final_scores):
                    bt.logging.debug(f"Score for miner idx: {idx} score: {score}")
                    uid = str(Utils.get(score, "uuid"))
                    if wandb_enabled:
                        wl.log({
                            "conversation_guid."+uid: conversation_guid,
                            "window_id."+uid: window_idx,
                            "uuid."+uid: Utils.get(score, "uuid"),
                            "hotkey."+uid: Utils.get(score, "hotkey"),
                            "adjusted_score."+uid: Utils.get(score, "adjustedScore"),
                            "final_miner_score."+uid: Utils.get(score, "final_miner_score"),
                        })

            #break
    if wandb_enabled:
        wl.end_log_wandb()




    #await vl.neighborhood_test()
    #await vl.llm_test()


