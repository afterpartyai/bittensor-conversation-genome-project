print("Loading extensions...")

Metrics = None
try:
   from .Metrics import Metrics
except Exception as e:
    pass
