import asyncio
import websockets

# Define the WebSocket handler
async def echo(websocket, path):
    print("Client connected")

    # Queue for messages to send to the client
    message_queue = asyncio.Queue()

    # Background task to handle sending messages to the client
    async def send_messages():
        while True:
            server_message = await message_queue.get()
            if server_message is None:  # Exit signal
                print("Closing connection...")
                await websocket.close()
                break
            await websocket.send(server_message)

    # Task to get user input asynchronouslyc
    async def get_user_input():
        while True:
            user_input = await asyncio.to_thread(input, "Enter a message to send to the client (or 'exit' to quit): ")
            if user_input.lower() == "exit":
                await message_queue.put(None)  # Signal to stop
                break
            if user_input.lower() == "takeoff":
                # Send takeoff command to the client
                command_message = "takeoff"
                await message_queue.put(command_message)
            else:
                await message_queue.put(user_input)

    # Task to handle receiving messages from the client
    async def receive_messages():
        async for message in websocket:
            print(f"Received from client: {message}")
            # You can process incoming messages here (parse and act accordingly)

    # Run all tasks concurrently
    await asyncio.gather(send_messages(), get_user_input(), receive_messages())

# Start the server
async def main():
    async with websockets.serve(echo, "192.168.54.197", 5000):
        print("WebSocket server listening on ws://192.168.54.197:5000")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
