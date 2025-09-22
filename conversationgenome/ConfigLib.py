import os

from dotenv import load_dotenv

from conversationgenome.utils.Utils import Utils

load_dotenv()


class c:
    state = {
        "validator": {
            "miners_per_task": 6,
            "number_of_task_bundles": 10,
            "number_of_task_per_bundle": 5,
            "minimum_number_of_tasks": 10,
        },
        "system": {
            "mode": 'test',
            "scoring_version": 0.1,
            "netuid": -1,
        },
        "llm": {
            # "type": 'spacy',
            # "type": os.environ.get("LLM_TYPE"),
            "type": 'openai',
        },
        "network": {
            "mainnet": 33,
            "testnet": 138,
        },
    }

    @staticmethod
    def get(section, key, default=None, return_type=None):
        out = default
        if section == "env":
            val = os.environ.get(key)
            if val:
                out = val
            if return_type == 'int':
                out = Utils._int(out, default=default)
        else:
            out = Utils.get(c.state, "%s.%s" % (section, key), default)
        return out

    @staticmethod
    def set(section, key, val):
        if not section in c.state:
            c.state[section] = {}
        c.state[section][key] = val
