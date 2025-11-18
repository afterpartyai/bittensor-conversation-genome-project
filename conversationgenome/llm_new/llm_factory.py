from conversationgenome.ConfigLib import c
from conversationgenome.llm_new import LlmLib


def get_llm_backend(llm_type_override=None) -> LlmLib:
    """
    Factory function to return the specific LLM implementation 
    based on the LLM_PROVIDER environment variable.
    """
    if not llm_type_override:
        llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")

    if llm_type_override == "openai" or not llm_type_override:
        from .llm_openai import LlmOpenAI
        return LlmOpenAI()
    
    elif llm_type_override == "anthropic":
        from .llm_anthropic import LlmAnthropic
        return LlmAnthropic()
    
    elif llm_type_override == "groq":
        from .llm_groq import LlmGroq
        return LlmGroq()
    
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {llm_type_override}")