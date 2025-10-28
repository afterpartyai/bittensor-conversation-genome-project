import importlib
import inspect

class Extensions():
    verbose = True

    @staticmethod
    def execute(className, methodName, params):
        print(f"Running {className}.{methodName} with {params}...")
        if True: #try:
            #className = ".Metrics"
            module = importlib.import_module("."+className, package=__package__)
            classRef = getattr(module, className)
            instance = classRef()
        else: #except Exception as e:
            print(f"Module '{className}' not found. Skipping.")
            return
