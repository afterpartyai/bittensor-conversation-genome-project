import importlib
import inspect

class Extensions():
    verbose = True

    @staticmethod
    def execute(className, methodName, params):
        if Extensions.verbose:
            print(f"Running {className}.{methodName} with {params}...")
        try:
            module = importlib.import_module("."+className, package=__package__)
            classRef = getattr(module, className)
            instance = classRef()
        except Exception as e:
            if Extensions.verbose:
                print(f"Module '{className}' not found. Skipping.")
            return
        if not hasattr(instance, methodName):
            if Extensions.verbose:
                print(f"Method '{className}.{methodName}' not found. Skipping.")
            return
        method = getattr(instance, methodName)
        result = method(params)
