import json
import os

from dotenv import load_dotenv
import numpy as np

from conversationgenome.ConfigLib import c



class LlmLib:
    verbose = False
    factory_llm = None

    #def __init__(self):
    #    self.generate_llm_instance()

    async def generate_llm_instance(self, llm_type=None):
        if not llm_type:
            llm_type = c.get("env", "LLM_TYPE")
        llm_class = "llm_"+llm_type
        if self.verbose:
            print("Factory generate LLM class of type %s" % (llm_type))
        out = None
        # Import the required LLM class dynamically
        class_name = "conversationgenome.%s" % (llm_class)
        module = None
        try:
            module = __import__(class_name)
        except:
            print("LLM class %s not found" % (class_name))

        if module:
            # Get the class from the imported module
            module_class_obj = getattr(module, llm_class)
            main_class = getattr(module_class_obj, llm_class)
            llm_instance = main_class()
            out = llm_instance

        return out

    async def conversation_to_tags(self,  convo):
        if not self.factory_llm:
            self.factory_llm = await self.generate_llm_instance()
        # Get prompt template
        #pt = await cl.getConvoPromptTemplate()
        #llml =  LlmApi()
        #data = await llml.callFunction("convoParse", convo)
        response = await self.factory_llm.conversation_to_metadata(convo)
        matches_dict = response['tags']
        return matches_dict



if __name__ == "__main__":
    print("Dynamically load LLM class by factory")
    # Import the required LLM class dynamically
    llm_class = "llm_spacy"
    #llm_class = "llm_openai"

    class_name = "conversationgenome.%s" % (llm_class)
    module = None
    try:
        module = __import__(class_name)
    except:
        print("LLM class %s not found" % (class_name))

    if module:
        # Get the class from the imported module
        module_class_obj = getattr(module, llm_class)
        main_class = getattr(module_class_obj, llm_class)
        llm_instance = main_class()
        convo = {}
        llm_instance.conversation_to_metadata(convo)
    print("Done")
