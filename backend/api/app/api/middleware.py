import time
import uuid
import logging
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.config.logging import request_id_ctx, user_id_ctx

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_token = request_id_ctx.set(request_id)
        
        # We try to extract user info if available in scope from a downstream auth dependency,
        # but typical dependencies run after middleware. 
        # For now, we initialize user_id as None. Auth deps will update it via contextvar.
        user_id_token = user_id_ctx.set(None)

        start_time = time.time()
        
        response = None
        exception = None
        try:
            response = await call_next(request)
        except Exception as e:
            exception = e
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            status_code = response.status_code if response else 500
            
            log_kwargs = {
                "endpoint": request.url.path,
                "http_method": request.method,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }
            
            if exception:
                logger.error(
                    f"Request failed: {request.method} {request.url.path}",
                    extra={**log_kwargs, "exception_detail": str(exception)},
                    exc_info=True
                )
            else:
                logger.info(
                    f"HTTP Request: {request.method} {request.url.path} - {status_code} - {duration_ms}ms",
                    extra=log_kwargs
                )
            
            request_id_ctx.reset(request_id_token)
            user_id_ctx.reset(user_id_token)
            
        if response:
            response.headers["X-Request-ID"] = request_id
        return response
