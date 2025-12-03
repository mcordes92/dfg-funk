import threading
from config import SERVER_HOST, SERVER_PORT, TIMEOUT_SECONDS
from client_registry import ClientRegistry
from udp_server import UDPServer


def main():
    print("Starting Python Funk System Server...")
    
    client_registry = ClientRegistry(TIMEOUT_SECONDS)
    server = UDPServer(SERVER_HOST, SERVER_PORT, client_registry)
    
    server.start()
    
    receive_thread = threading.Thread(target=server.receive_and_forward, daemon=True)
    receive_thread.start()
    
    cleanup_thread = threading.Thread(target=server.cleanup_stale_clients, daemon=True)
    cleanup_thread.start()
    
    print("Server is running. Press Ctrl+C to stop.")
    
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
        print("Server stopped.")


if __name__ == '__main__':
    main()
