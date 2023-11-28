import asyncio

from examples.advanced_greeter import HelloRequest, Greeter


class GreeterClient(Greeter.Client):
    async def greeting(self, name: str) -> str:
        request = HelloRequest(name=name)
        response = await self.say_hello(request=request)
        return response.text


async def main():
    greeter = GreeterClient(host="127.0.0.1", port=50051)

    text = await greeter.greeting(name="Vika")
    print(text)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
