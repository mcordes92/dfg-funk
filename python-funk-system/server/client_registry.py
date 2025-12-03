import time
from threading import Lock


class ClientRegistry:
    def __init__(self, timeout_seconds):
        self.clients = {}
        self.channels = {}
        self.lock = Lock()
        self.timeout_seconds = timeout_seconds

    def register_client(self, client_address, channel_id, user_id):
        with self.lock:
            client_key = client_address
            
            # Initialize or update client info
            if client_key not in self.clients:
                self.clients[client_key] = {
                    'address': client_address,
                    'channel_ids': set(),  # Multiple channels per client
                    'user_id': user_id,
                    'last_seen': time.time()
                }
            
            # Add channel to client's channel list
            self.clients[client_key]['channel_ids'].add(channel_id)
            self.clients[client_key]['last_seen'] = time.time()
            
            # Add client to channel's client list
            if channel_id not in self.channels:
                self.channels[channel_id] = set()
            self.channels[channel_id].add(client_key)

    def update_timestamp(self, client_address):
        with self.lock:
            if client_address in self.clients:
                self.clients[client_address]['last_seen'] = time.time()

    def get_clients_in_channel(self, channel_id, exclude_address=None):
        with self.lock:
            if channel_id not in self.channels:
                return []
            
            clients = []
            for client_key in self.channels[channel_id]:
                if client_key != exclude_address and client_key in self.clients:
                    clients.append(self.clients[client_key]['address'])
            return clients

    def remove_stale_clients(self):
        current_time = time.time()
        with self.lock:
            stale_clients = []
            for client_key, client_info in self.clients.items():
                if current_time - client_info['last_seen'] > self.timeout_seconds:
                    stale_clients.append(client_key)
            
            for client_key in stale_clients:
                client_info = self.clients[client_key]
                # Remove client from all channels
                for channel_id in client_info.get('channel_ids', set()):
                    if channel_id in self.channels:
                        self.channels[channel_id].discard(client_key)
                        if not self.channels[channel_id]:
                            del self.channels[channel_id]
                del self.clients[client_key]
            
            return len(stale_clients)
