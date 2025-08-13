from prometheus_client import Counter

request_counter = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["api_key", "ip", "path", "status"]
)