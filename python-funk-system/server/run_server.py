"""
Combined server that runs both UDP server and REST API
"""
import threading
from config import SERVER_HOST, SERVER_PORT, TIMEOUT_SECONDS
from client_registry import ClientRegistry
from udp_server import UDPServer
from api_server import start_api_server, set_udp_server


def main():
    print("=" * 60)
    print("🎙️  Starting Python Funk System Server")
    print("=" * 60)
    
    # Initialize UDP server
    print("\n[1/2] Initializing UDP server...")
    client_registry = ClientRegistry(TIMEOUT_SECONDS)
    udp_server = UDPServer(SERVER_HOST, SERVER_PORT, client_registry)
    udp_server.start()
    
    # Start UDP threads
    receive_thread = threading.Thread(target=udp_server.receive_and_forward, daemon=True)
    receive_thread.start()
    print(f"✅ UDP Server running on {SERVER_HOST}:{SERVER_PORT}")
    
    cleanup_thread = threading.Thread(target=udp_server.cleanup_stale_clients, daemon=True)
    cleanup_thread.start()
    print(f"✅ Cleanup thread started (timeout: {TIMEOUT_SECONDS}s)")
    
    # Set UDP server reference for API
    set_udp_server(udp_server)
    
    # Start API server in separate thread
    print("\n[2/2] Starting REST API server...")
    api_thread = threading.Thread(
        target=start_api_server,
        kwargs={"host": "0.0.0.0", "port": 8000},
        daemon=True
    )
    api_thread.start()
    print("✅ REST API running on http://0.0.0.0:8000")
    
    print("\n" + "=" * 60)
    print("🟢 Server is ready!")
    print("=" * 60)
    print("\n📋 Available services:")
    print(f"   • UDP Server:     {SERVER_HOST}:{SERVER_PORT}")
    print(f"   • REST API:       http://localhost:8000")
    print(f"   • Admin Web UI:   http://localhost:8000")
    print(f"   • API Docs:       http://localhost:8000/docs")
    print(f"   • Health Check:   http://localhost:8000/health")
    print("\n💡 Press Ctrl+C to stop the server\n")
    
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down server...")
        udp_server.stop()
        print("✅ Server stopped. Goodbye!")


if __name__ == '__main__':
    main()
