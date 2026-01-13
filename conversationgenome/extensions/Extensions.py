import importlib
import inspect
import pkgutil
import bittensor as bt

class Extensions():
    verbose = True
    def __init__(self):
        self.extensionDict = {}
        self.discover()


    def discover(self):
        import conversationgenome.extensions as extpkg

        for modinfo in pkgutil.iter_modules(extpkg.__path__):
            name = modinfo.name
            if name in ("__init__", "Extensions"):
                continue

            try:
                module = importlib.import_module(f"{extpkg.__name__}.{name}")
                extensionClass = getattr(module, name, None)
                if extensionClass is None:
                    continue
                self.extensionDict[name] = extensionClass()
                bt.logging.debug(f"Loaded extension: {name}")
            except Exception as e:
                # Extension import/init errors should never crash core loops.
                bt.logging.warning(f"Failed to load extension {name}: {e}")

    def execute(self, extensionClassName, extensionMethodName, params=None):
        extensionInstance = self.extensionDict.get(extensionClassName)
        if extensionInstance is None:
            return None

        extensionMethod = getattr(extensionInstance, extensionMethodName, None)
        if not callable(extensionMethod):
            return None

        try:
            return extensionMethod(params or {})
        except Exception as e:
            bt.logging.error(f"Extension error {extensionClassName}.{extensionMethodName}: {e}")
            return None

