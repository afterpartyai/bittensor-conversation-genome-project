from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        api_key = self.get_api_key(request)

        request.state.api_key = api_key

        return await call_next(request)

    def get_api_key(self, request: Request) -> str | None:
        # Check in Auth Header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:].strip()

        # Check in Query Params
        api_key_from_query_param = request.query_params.get("api")
        if api_key_from_query_param:
            return api_key_from_query_param.strip()

        return None
