import asyncio
import websockets

async def echo(websocket):
    name = await websocket.recv()
    print(f"<<< {name}")

    greeting = f"Hello, {name}!"

    await websocket.send(greeting)
    print(f">>> {greeting}")

async def main():
    async with websockets.serve(echo, "localhost", 8765):
        await asyncio.Future() #run forever

asyncio.run(main())
