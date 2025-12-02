import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Receive welcome message
        welcome = await websocket.recv()
        print("Welcome:", welcome)

        # Send ping
        await websocket.send(json.dumps({"type": "ping", "data": {}}))
        pong = await websocket.recv()
        print("Pong:", pong)

        # Subscribe to metrics
        await websocket.send(json.dumps({"type": "subscribe_metrics", "data": {}}))
        sub = await websocket.recv()
        print("Subscription:", sub)

if __name__ == "__main__":
    asyncio.run(test_ws()) 