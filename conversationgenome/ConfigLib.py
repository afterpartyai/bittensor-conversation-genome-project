from conversationgenome.Utils import Utils

class c:
    state = {
        "validator" : {
            "miners_per_window": 3,
        },
        "system" : {
            "mode": 'test',
        }
    }

    @staticmethod
    def get(section, key, default=None):
        return Utils.get(c.state, "%s.%s" % (section, key), default)

    @staticmethod
    def set(section, key, val):
        if not section in c.state:
            c.state[section] = {}
        c.state[section][key] = val

