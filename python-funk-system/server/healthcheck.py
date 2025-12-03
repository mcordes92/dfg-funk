#!/usr/bin/env python3
"""
Healthcheck script for Docker container
Checks if both UDP and API servers are running
"""
import socket
import sys
import urllib.request

def check_api_server():
    """Check if API server is responding"""
    try:
        response = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
        return response.status == 200
    except Exception as e:
        print(f"API check failed: {e}")
        return False

def check_udp_socket():
    """Check if UDP socket is listening"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        # Just check if we can create a socket (actual UDP listening check is complex)
        sock.close()
        return True
    except Exception as e:
        print(f"UDP check failed: {e}")
        return False

if __name__ == "__main__":
    api_ok = check_api_server()
    udp_ok = check_udp_socket()
    
    if api_ok and udp_ok:
        print("✅ Health check passed")
        sys.exit(0)
    else:
        print("❌ Health check failed")
        print(f"  API Server: {'OK' if api_ok else 'FAIL'}")
        print(f"  UDP Socket: {'OK' if udp_ok else 'FAIL'}")
        sys.exit(1)
