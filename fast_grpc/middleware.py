from typing import Awaitable


class FastGRPCMiddleware:
    async def __call__(self, next_call: Awaitable, request, context):
        return await next_call
