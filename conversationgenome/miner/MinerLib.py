verbose = False

import copy
import random
import asyncio
from conversationgenome.ConfigLib import c
from conversationgenome.mock.MockBt import MockBt


from conversationgenome.utils.Utils import Utils


bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()

from conversationgenome.llm.LlmLib import LlmLib

if c.get('env', 'FORCE_LOG') == 'debug':
    bt.logging.enable_debug(True)
elif c.get('env', 'FORCE_LOG') == 'info':
    bt.logging.enable_default(True)


class MinerLib:
    verbose = False

    async def do_mining(self, conversation_guid, window_idx, conversation_window, minerUid, dryrun=False):
        #bt.logging.debug("MINERCONVO", convoWindow, minerUid)
        out = {"uid":minerUid, "tags":[], "profiles":[], "convoChecksum":11}

        if not dryrun:
            llml = LlmLib()
            lines = copy.deepcopy(conversation_window)
            result = await llml.conversation_to_metadata({"lines":lines})
            tags = Utils.get(result, 'tags')
            out["tags"] = tags
            out["vectors"] = Utils.get(result, 'vectors', {})
            num_tags = len(Utils.get(out, 'tags', []))
            bt.logging.info(f"Miner: Mined {num_tags} vectors and tags")

            if self.verbose:
                bt.logging.debug(f"MINED TAGS: {out['tags']}")
        else:
            llml = LlmLib()
            exampleSentences = [
                "Who's there?",
                "Nay, answer me. Stand and unfold yourself.",
                "Long live the King!",
                "Barnardo?",
                "He.",
                "You come most carefully upon your hour.",
                "Tis now struck twelve. Get thee to bed, Francisco.",
                "For this relief much thanks. Tis bitter cold, And I am sick at heart.",
                "Have you had quiet guard?",
                "Not a mouse stirring.",
                "Well, good night. If you do meet Horatio and Marcellus, The rivals of my watch, bid them make haste.",
                "I think I hear them. Stand, ho! Who is there?",
                "Friends to this ground.",
                "And liegemen to the Dane.",
            ]
            lines = copy.deepcopy(exampleSentences)
            lines.append(random.choice(exampleSentences))
            lines.append(random.choice(exampleSentences))
            matches_dict = await llml.conversation_to_metadata({"lines":lines})
            tags = list(matches_dict.keys())
            out["tags"] = tags
            out["vectors"] = matches_dict
        return out

