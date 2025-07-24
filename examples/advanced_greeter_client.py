# import sys
# breakpoint()

import asyncio

from examples.advanced_greeter import Greeter, HelloRequest


class GreeterClient(Greeter.Client):
    async def greeting(self, name: str) -> str:
        request = HelloRequest(name=name)
        response = await self.say_hello(request=request)  # pylint: disable=no-member
        return response.text


async def main():
    greeter = GreeterClient(host="127.0.0.1", port=50051)

    print("Calling Greeter say_hello...")
    text = await greeter.greeting(name="Vika")
    print("Text from response:", text)


if __name__ == "__main__":
    asyncio.run(main())
