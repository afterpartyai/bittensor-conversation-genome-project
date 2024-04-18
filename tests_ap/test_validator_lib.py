import pytest
from conversationgenome.ValidatorLib import ValidatorLib
from conversationgenome.ConfigLib import c

@pytest.mark.asyncio
async def test_full():
    c.set('system', 'mode', 'test')
    vl = ValidatorLib()
    result = await vl.reserve_conversation()
    if result:
        (full_conversation, full_conversation_metadata, conversation_windows) = result
        #await vl.send_windows_to_miners(conversation_windows, full_conversation=full_conversation, full_conversation_metadata=full_conversation_metadata)
        # Loop through conversation windows. Send each window to multiple miners
        print(f"Found {len(conversation_windows)} conversation windows. Sequentially sending to batches of miners")
        for idx, conversation_window in enumerate(conversation_windows):
            print(f"conversation_window {idx}", conversation_window)



    #await vl.neighborhood_test()
    #await vl.llm_test()


