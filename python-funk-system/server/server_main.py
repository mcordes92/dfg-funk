import asyncio
from config import SERVER_HOST, SERVER_PORT, TIMEOUT_SECONDS
from client_registry import ClientRegistry
from async_udp_server import AsyncUDPServer


async def main():
    print("🚀 Starting Python Funk System Server (AsyncIO)...")
    
    client_registry = ClientRegistry(TIMEOUT_SECONDS)
    server = AsyncUDPServer(SERVER_HOST, SERVER_PORT, client_registry)
    
    await server.start()
    
    print("✅ Server is running. Press Ctrl+C to stop.")
    
    try:
        # Keep server running
        while server.running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        await server.stop()
        print("✅ Server stopped.")


if __name__ == '__main__':
    asyncio.run(main())
