import socket
import threading
from protocol import (parse_header, build_pong_packet, build_auth_ok_packet, 
                     build_auth_fail_packet, PACKET_TYPE_PING, PACKET_TYPE_AUDIO, 
                     PACKET_TYPE_AUTH)
from config import MAX_PACKET_SIZE
from database import Database


class UDPServer:
    def __init__(self, host, port, client_registry):
        self.host = host
        self.port = port
        self.client_registry = client_registry
        self.socket = None
        self.running = False
        self.db = Database()
        self.authenticated_clients = {}  # {client_address: {'username': str, 'user_id': int, 'allowed_channels': list}}
        self.traffic_bytes_in = 0  # Total incoming bytes
        self.traffic_bytes_out = 0  # Total outgoing bytes
        self.last_traffic_save = None

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        self.running = True
        print(f"UDP Server listening on {self.host}:{self.port}")

    def receive_and_forward(self):
        while self.running:
            try:
                data, client_address = self.socket.recvfrom(MAX_PACKET_SIZE)
                
                # Track incoming traffic
                self.traffic_bytes_in += len(data)
                
                packet_type, channel_id, user_id, sequence_number, payload = parse_header(data)
                if channel_id is None:
                    continue
                
                # Handle AUTH packets first
                if packet_type == PACKET_TYPE_AUTH:
                    self._handle_auth(client_address, channel_id, user_id, payload)
                    continue
                
                # Check if client is authenticated before processing other packets
                if client_address not in self.authenticated_clients:
                    print(f"⚠️ Unauthenticated client {client_address} tried to send packet type {packet_type}")
                    # Send auth fail
                    auth_fail = build_auth_fail_packet(channel_id, user_id, b'Not authenticated')
                    try:
                        self.socket.sendto(auth_fail, client_address)
                    except:
                        pass
                    continue
                
                # Check channel permission
                auth_info = self.authenticated_clients[client_address]
                if channel_id not in auth_info['allowed_channels']:
                    print(f"⚠️ User {auth_info['username']} not authorized for channel {channel_id}")
                    continue
                
                self.client_registry.register_client(client_address, channel_id, user_id)
                self.client_registry.update_timestamp(client_address)
                
                # Handle PING packets - respond with PONG
                if packet_type == PACKET_TYPE_PING:
                    pong_packet = build_pong_packet(channel_id, user_id)
                    try:
                        self.socket.sendto(pong_packet, client_address)
                        self.traffic_bytes_out += len(pong_packet)
                    except Exception as e:
                        print(f"Failed to send PONG to {client_address}: {e}")
                    continue
                
                # Forward audio packets to other clients in channel
                if packet_type == PACKET_TYPE_AUDIO:
                    recipients = self.client_registry.get_clients_in_channel(
                        channel_id, 
                        exclude_address=client_address
                    )
                    
                    for recipient_address in recipients:
                        try:
                            self.socket.sendto(data, recipient_address)
                            self.traffic_bytes_out += len(data)
                        except Exception as e:
                            print(f"Failed to send to {recipient_address}: {e}")
                        
            except Exception as e:
                if self.running:
                    print(f"Error receiving packet: {e}")
    
    def _handle_auth(self, client_address, channel_id, user_id, payload):
        """Handle authentication request"""
        try:
            funk_key = payload.decode('utf-8').strip()
            
            # Verify funk key against database
            user = self.db.verify_user(funk_key)
            
            if user:
                # Check channel permission
                if channel_id not in user['allowed_channels']:
                    print(f"🔒 User {user['username']} not authorized for channel {channel_id}")
                    auth_fail = build_auth_fail_packet(channel_id, user_id, b'Channel not authorized')
                    self.socket.sendto(auth_fail, client_address)
                    return
                
                # Store authentication info
                self.authenticated_clients[client_address] = {
                    'username': user['username'],
                    'user_id': user['id'],
                    'allowed_channels': user['allowed_channels'],
                    'funk_key': funk_key
                }
                
                # Log connection
                self.db.log_connection(user['id'], channel_id, 'connect', client_address[0])
                self.db.update_last_seen(user['id'])
                
                print(f"✅ User {user['username']} authenticated for channel {channel_id}")
                
                # Register client immediately in this channel
                self.client_registry.register_client(client_address, channel_id, user['id'])
                
                # Send auth success
                auth_ok = build_auth_ok_packet(channel_id, user_id)
                self.socket.sendto(auth_ok, client_address)
                self.traffic_bytes_out += len(auth_ok)
            else:
                print(f"❌ Invalid funk key from {client_address}")
                auth_fail = build_auth_fail_packet(channel_id, user_id, b'Invalid funk key')
                self.socket.sendto(auth_fail, client_address)
                self.traffic_bytes_out += len(auth_fail)
                
        except Exception as e:
            print(f"Error handling auth: {e}")
            auth_fail = build_auth_fail_packet(channel_id, user_id, b'Auth error')
            try:
                self.socket.sendto(auth_fail, client_address)
            except:
                pass

    def cleanup_stale_clients(self):
        while self.running:
            removed = self.client_registry.remove_stale_clients()
            if removed > 0:
                print(f"Removed {removed} stale clients")
                # Clean up authentication cache for removed clients
                stale_auth = []
                for addr in self.authenticated_clients:
                    if addr not in self.client_registry.clients:
                        stale_auth.append(addr)
                for addr in stale_auth:
                    username = self.authenticated_clients[addr]['username']
                    print(f"🔓 Logged out: {username}")
                    del self.authenticated_clients[addr]
            
            # Save traffic stats every 5 minutes
            self._save_traffic_stats()
            
            threading.Event().wait(5)
    
    def _save_traffic_stats(self):
        """Save traffic statistics to database"""
        from datetime import datetime, timedelta
        
        # Only save every 5 minutes
        now = datetime.now()
        if self.last_traffic_save is None:
            self.last_traffic_save = now
        
        if (now - self.last_traffic_save).total_seconds() < 300:  # 5 minutes
            return
        
        if self.traffic_bytes_in > 0 or self.traffic_bytes_out > 0:
            try:
                self.db.record_traffic(self.traffic_bytes_in, self.traffic_bytes_out)
                print(f"📊 Traffic gespeichert: ⬇️ {self._format_bytes(self.traffic_bytes_in)} | ⬆️ {self._format_bytes(self.traffic_bytes_out)}")
                self.traffic_bytes_in = 0
                self.traffic_bytes_out = 0
                self.last_traffic_save = now
            except Exception as e:
                print(f"Fehler beim Speichern der Traffic-Statistiken: {e}")
    
    def _format_bytes(self, bytes_val):
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} TB"

    def stop(self):
        self.running = False
        # Save remaining traffic stats before stopping
        if self.traffic_bytes_in > 0 or self.traffic_bytes_out > 0:
            try:
                self.db.record_traffic(self.traffic_bytes_in, self.traffic_bytes_out)
                print(f"📊 Final traffic saved: ⬇️ {self._format_bytes(self.traffic_bytes_in)} | ⬆️ {self._format_bytes(self.traffic_bytes_out)}")
            except Exception as e:
                print(f"Fehler beim Speichern der finalen Traffic-Statistiken: {e}")
        if self.socket:
            self.socket.close()
    
    def get_current_traffic(self):
        """Get current traffic counters (not yet saved)"""
        return {
            "bytes_in": self.traffic_bytes_in,
            "bytes_out": self.traffic_bytes_out
        }
    
    def forward_to_channel(self, channel_id, packet, exclude_user_id=None):
        """
        Forward a packet to all clients in a specific channel
        
        Args:
            channel_id: Target channel ID
            packet: Complete packet data to send
            exclude_user_id: Optional user ID to exclude from receiving (e.g., sender)
        """
        if not self.running or not self.socket:
            return
        
        # Get all authenticated clients in the channel
        recipients = self.client_registry.get_clients_in_channel(channel_id)
        
        sent_count = 0
        for recipient_address in recipients:
            # Skip if this is the excluded user
            if exclude_user_id is not None:
                client_info = self.authenticated_clients.get(recipient_address)
                if client_info and client_info.get('user_id') == exclude_user_id:
                    continue
            
            try:
                self.socket.sendto(packet, recipient_address)
                self.traffic_bytes_out += len(packet)
                sent_count += 1
            except Exception as e:
                print(f"Failed to send to {recipient_address}: {e}")
        
        return sent_count
