# src/metrics.py
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('app_request_count', 'Total API requests', ['endpoint', 'method', 'status'])
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Request latency (s)', ['endpoint'])
