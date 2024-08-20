import json
import os

from dotenv import load_dotenv
import numpy as np

from conversationgenome.ConfigLib import c
from conversationgenome.mock.MockBt import MockBt
#from conversationgenome.llm.llm_openai import llm_openai

verbose = False
bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()


class LlmLib:
    verbose = False
    factory_llm = None

    async def generate_llm_instance(self, llm_type=None):
        if not llm_type:
            llm_type = c.get("env", "LLM_TYPE")
        llm_class = "llm_"+llm_type
        if self.verbose:
            bt.logging.info("Factory generate LLM class of type %s" % (llm_type))
        out = None

        # Import the required LLM class dynamically
        class_name = f"conversationgenome.llm.{llm_class}"
        module = None
        try:
            module = __import__(class_name)
        except Exception as e:
            bt.logging.error(f"LLM class '{class_name}' failed to import: {e}")

        if module:
            # Get the class from the imported module
            module_class_obj = getattr(module.llm, llm_class)
            main_class = getattr(module_class_obj, llm_class)
            llm_instance = main_class()
            out = llm_instance

        return out

    async def conversation_to_metadata(self,  conversation):
        if not self.factory_llm:
            self.factory_llm = await self.generate_llm_instance()
            if not self.factory_llm:
                bt.logging.error("LLM not found. Aborting conversation_to_metadata.")
                return

        response = await self.factory_llm.conversation_to_metadata(conversation)
        return response

    async def miner_conversation_to_metadata(self,  conversation):
        if not self.factory_llm:
            self.factory_llm = await self.generate_llm_instance()
            if not self.factory_llm:
                bt.logging.error("LLM not found. Aborting conversation_to_metadata.")
                return

        response = await self.factory_llm.miner_conversation_to_metadata(conversation)
        return response



if __name__ == "__main__":
    bt.logging.info("Dynamically load LLM class by factory")
    # Import the required LLM class dynamically
    llm_class = "llm_spacy"
    #llm_class = "llm_openai"

    class_name = "conversationgenome.%s" % (llm_class)
    module = None
    try:
        module = __import__(class_name)
    except:
        bt.logging.info("LLM class %s not found" % (class_name))

    if module:
        # Get the class from the imported module
        module_class_obj = getattr(module, llm_class)
        main_class = getattr(module_class_obj, llm_class)
        llm_instance = main_class()
        convo = {}
        llm_instance.conversation_to_metadata(convo)
    bt.logging.info("Done")
