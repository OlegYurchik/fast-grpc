from typing import Callable


class FastGRPCMiddleware:
    """Middleware."""

    async def __call__(self, next_call: Callable, request, context):
        return await next_call(request, context)
