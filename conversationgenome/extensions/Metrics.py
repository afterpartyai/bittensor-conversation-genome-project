print("Loading Metrics example extension...")

class Metrics():
    verbose = True
    
    def incStat(self, params):
        promMetric = params.get("metric_name")
        print(f"_________INCREMENTING Prometheus Metric {promMetric}")
