import pytest
from conversationgenome.ValidatorLib import ValidatorLib
from conversationgenome.ConfigLib import c

@pytest.mark.asyncio
async def test_full():
    c.set('system', 'mode', 'test')
    vl = ValidatorLib()
    await vl.requestConvo()
    #await vl.neighborhood_test()
    #await vl.llm_test()


