from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from metrics.prometheus_metrics import request_counter

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        api_key = getattr(request.state, "api_key", "unknown")
        ip = request.client.host
        path = request.url.path
        status = response.status_code

        request_counter.labels(
            api_key=api_key,
            ip=ip,
            path=path,
            status=status
        ).inc()

        return response