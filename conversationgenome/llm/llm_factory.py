import bittensor as bt

from conversationgenome.ConfigLib import c
from conversationgenome.llm.LlmLib import LlmLib

LOCKED_LLM_TYPE = "openai"
_OVERRIDE_ENV_VARS = ["LLM_TYPE_OVERRIDE", "OPENAI_MODEL", "OPENAI_EMBEDDINGS_MODEL_OVERRIDE"]


def _present_llm_override_vars() -> list[str]:
    return [v for v in _OVERRIDE_ENV_VARS if c.get("env", v)]


def configure_llm_override_lockdown(netuid: int) -> bool:
    """Validator-only startup check: on mainnet, LLM provider/model/embeddings-model
    overrides from .env are ignored so all mainnet validators score with the same
    in-code default LLM config. On any other netuid, overrides are still honored but
    a warning is logged so operators notice before running on mainnet.
    """
    mainnet_netuid = c.get("network", "mainnet", 33)
    is_mainnet = netuid == mainnet_netuid
    c.set("system", "llm_overrides_locked", is_mainnet)

    present = _present_llm_override_vars()
    if present:
        if is_mainnet:
            bt.logging.warning(
                f"LLM override env var(s) {present} detected on mainnet (netuid={netuid}). "
                "Overrides are ignored on mainnet; falling back to in-code defaults."
            )
        else:
            bt.logging.warning(
                f"LLM override env var(s) {present} detected on non-mainnet netuid={netuid}. "
                "Honoring overrides now, but they will be ignored if this validator runs on mainnet."
            )
    return is_mainnet


def get_llm_backend(llm_type_override=None) -> LlmLib:
    """
    Factory function to return the specific LLM implementation
    based on the LLM_PROVIDER environment variable.
    """
    if c.get("system", "llm_overrides_locked", False):
        from .llm_openai import LlmOpenAI
        return LlmOpenAI(ignore_model_override=True)

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
    
    elif llm_type_override == "openrouter":
        from .llm_openrouter import LlmOpenRouter
        return LlmOpenRouter()
    
    elif llm_type_override == "chutes":
        from .llm_chutes import LlmChutes
        return LlmChutes()
    
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {llm_type_override}")
