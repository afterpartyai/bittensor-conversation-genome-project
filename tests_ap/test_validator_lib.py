import pytest
import random

from conversationgenome.ConfigLib import c
from conversationgenome.Utils import Utils

from conversationgenome.ValidatorLib import ValidatorLib
from conversationgenome.validator.evaluator import Evaluator


@pytest.mark.asyncio
async def test_full():
    c.set('system', 'mode', 'test')
    miner_uids = [1,2,3,4,5,6,7,8,9]
    vl = ValidatorLib()
    el = Evaluator()
    result = await vl.reserve_conversation()
    test_mode = True
    if result:
        miners_per_window = c.get("validator", "miners_per_window", 3)
        (full_conversation, full_conversation_metadata, conversation_windows) = result
        if test_mode:
            # In test_mode, to expand the miner scores, remove half of the full convo tags.
            # This "generates" more unique tags found for the miners
            half = int(len(full_conversation_metadata['tags'])/2)
            full_conversation_metadata['tags'] = full_conversation_metadata['tags'][0:half]
        conversation_guid = Utils.get(full_conversation, "uid")
        #await vl.send_windows_to_miners(conversation_windows, full_conversation=full_conversation, full_conversation_metadata=full_conversation_metadata)
        # Loop through conversation windows. Send each window to multiple miners
        print(f"Found {len(conversation_windows)} conversation windows. Sequentially sending to batches of miners")
        for window_idx, conversation_window in enumerate(conversation_windows):
            print(f"conversation_window {window_idx}", conversation_window)
            selected_miner_uids = vl.selectStage1Miners(miner_uids)
            print("Selected miners", selected_miner_uids)
            miner_results = await vl.send_to_miners(conversation_guid, window_idx, conversation_window, selected_miner_uids)
            for miner_result in miner_results:
                print(f"RESULT uid: {miner_result['uid']}, tags: {miner_result['tags']} vector count: {len(miner_result['vectors'])}")

            # Evaluate results of miners
            await el.evaluate(full_conversation_metadata, miner_results)
            break




    #await vl.neighborhood_test()
    #await vl.llm_test()


