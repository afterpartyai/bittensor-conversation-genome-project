import pytest
import random

from conversationgenome.ConfigLib import c
from conversationgenome.utils.Utils import Utils

from conversationgenome.validator.ValidatorLib import ValidatorLib
from conversationgenome.validator.evaluator import Evaluator
from conversationgenome.analytics.WandbLib import WandbLib


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
    miner_uids = []

    vl = ValidatorLib()
    el = Evaluator()
    result = await vl.reserve_conversation()
    test_mode = True
    if result:
        (full_conversation, full_conversation_metadata, conversation_windows) = result
        print("full_conversation", full_conversation)
        llm_type = c.get("env", "LLM_TYPE")
        model = c.get("env", "OPENAI_MODEL")
        conversation_guid = Utils.get(full_conversation, "guid")
        tags = Utils.get(full_conversation_metadata, "tags", [])
        vectors = Utils.get(full_conversation_metadata, "vectors", [])
        full_conversation_tag_count = len(tags)
        lines = Utils.get(full_conversation, "lines", [])
        participants = Utils.get(full_conversation, "participants", [])
        miners_per_window = c.get("validator", "miners_per_window", 3)
        min_lines = c.get("convo_window", "min_lines", 5)
        max_lines = c.get("convo_window", "max_lines", 50)
        overlap_lines = c.get("convo_window", "overlap_lines", 2)
        batch_num = random.randint(100000, 9999999)

        validatorHotkey = "VHK-0"
        #print("FULLCONVO", tags)
        #return

        await vl.put_convo(validatorHotkey, conversation_guid, {"tags":tags, "vectors":vectors}, type="validator", batch_num=batch_num, window=999)


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
            })
        if llm_type == "spacy":
            print("SPACY TEST MODE")
            # In test_mode, to expand the miner scores, remove half of the full convo tags.
            # This "generates" more unique tags found for the miners
            half = int(len(full_conversation_metadata['tags'])/2)
            full_conversation_metadata['tags'] = full_conversation_metadata['tags'][0:half]
        #await vl.send_windows_to_miners(conversation_windows, full_conversation=full_conversation, full_conversation_metadata=full_conversation_metadata)
        # Loop through conversation windows. Send each window to multiple miners
        print(f"Found {len(conversation_windows)} conversation windows. Sequentially sending to batches of miners")
        #conversation_windows = []
        for window_idx, conversation_window in enumerate(conversation_windows):
            print(f"conversation_window {window_idx}", conversation_window)
            selected_miner_uids = vl.selectStage1Miners(miner_uids)
            print("Selected miners", selected_miner_uids)

            miner_results = await vl.send_to_miners(conversation_guid, window_idx, conversation_window, selected_miner_uids)
            mock_miner_responses = []
            for idx, miner_result in enumerate(miner_results):
                print(f"RESULT uid: {miner_result['uid']}, tags: {miner_result['tags']} vector count: {len(miner_result['vectors'])}")
                response = MockResponse()
                response.axon.hotkey = "HK-"+str(idx)
                response.axon.uuid = str(miner_result['uid'])
                response.cgp_output = [miner_result]
                print(f"CGP Received tags: {response.cgp_output[0]['tags']} -- PUTTING OUTPUT")
                await vl.put_convo(response.axon.hotkey, conversation_guid, response.cgp_output[0], type="miner", batch_num=batch_num, window=idx)

                mock_miner_responses.append(response)
            # Evaluate results of miners
            (final_scores, rank_scores) = await el.evaluate(full_conversation_metadata, mock_miner_responses)
            for idx, score in enumerate(final_scores):
                print("score", score)
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

            break
    if wandb_enabled:
        wl.end_log_wandb()




    #await vl.neighborhood_test()
    #await vl.llm_test()


