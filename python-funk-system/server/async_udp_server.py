import asyncio
from protocol import (parse_header, build_pong_packet, build_auth_ok_packet, 
                     build_auth_fail_packet, PACKET_TYPE_PING, PACKET_TYPE_AUDIO, 
                     PACKET_TYPE_AUTH)
from config import MAX_PACKET_SIZE
from database import Database
from jitter_buffer import JitterBuffer


class AsyncUDPProtocol(asyncio.DatagramProtocol):
    """Async UDP Protocol Handler - Non-blocking packet processing"""
    
    def __init__(self, server):
        self.server = server
        super().__init__()
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data, addr):
        """Called when a datagram is received - non-blocking"""
        asyncio.create_task(self.server.handle_packet(data, addr))
    
    def error_received(self, exc):
        print(f'Error received: {exc}')


class AsyncUDPServer:
    """AsyncIO-based UDP Server for concurrent packet handling"""
    
    def __init__(self, host, port, client_registry):
        self.host = host
        self.port = port
        self.client_registry = client_registry
        self.transport = None
        self.protocol = None
        self.running = False
        self.db = Database()
        self.authenticated_clients = {}  # {client_address: {'username': str, 'user_id': int, 'allowed_channels': list}}
        self.traffic_bytes_in = 0
        self.traffic_bytes_out = 0
        self.last_traffic_save = None
        self.jitter_buffers = {}  # {(channel_id, client_addr): JitterBuffer}
        self._cleanup_task = None
        self._traffic_task = None
    
    async def start(self):
        """Start async UDP server"""
        loop = asyncio.get_event_loop()
        
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: AsyncUDPProtocol(self),
            local_addr=(self.host, self.port)
        )
        
        self.running = True
        print(f"🚀 AsyncIO UDP Server listening on {self.host}:{self.port}")
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._traffic_task = asyncio.create_task(self._traffic_stats_loop())
    
    async def handle_packet(self, data, client_address):
        """Handle incoming packet asynchronously - no blocking!"""
        try:
            # Track incoming traffic
            self.traffic_bytes_in += len(data)
            
            packet_type, channel_id, user_id, sequence_number, payload = parse_header(data)
            if channel_id is None:
                return
            
            # Handle AUTH packets first
            if packet_type == PACKET_TYPE_AUTH:
                await self._handle_auth(client_address, channel_id, user_id, payload)
                return
            
            # Check if client is authenticated before processing other packets
            if client_address not in self.authenticated_clients:
                print(f"⚠️ Unauthenticated client {client_address} tried to send packet type {packet_type}")
                auth_fail = build_auth_fail_packet(channel_id, user_id, b'Not authenticated')
                self._send_packet(auth_fail, client_address)
                return
            
            # Check channel permission
            auth_info = self.authenticated_clients[client_address]
            if channel_id not in auth_info['allowed_channels']:
                print(f"⚠️ User {auth_info['username']} not authorized for channel {channel_id}")
                return
            
            self.client_registry.register_client(client_address, channel_id, user_id)
            self.client_registry.update_timestamp(client_address)
            
            # Handle PING packets - respond with PONG
            if packet_type == PACKET_TYPE_PING:
                pong_packet = build_pong_packet(channel_id, user_id)
                self._send_packet(pong_packet, client_address)
                return
            
            # Handle AUDIO packets with jitter buffer
            if packet_type == PACKET_TYPE_AUDIO:
                await self._handle_audio_packet(
                    data, client_address, channel_id, user_id, sequence_number
                )
                
        except Exception as e:
            if self.running:
                print(f"❌ Error handling packet: {e}")
    
    async def _handle_audio_packet(self, data, client_address, channel_id, user_id, sequence_number):
        """Handle audio packet with jitter buffer for stable playback"""
        # Get or create jitter buffer for this client in this channel
        buffer_key = (channel_id, client_address)
        if buffer_key not in self.jitter_buffers:
            self.jitter_buffers[buffer_key] = JitterBuffer(buffer_size=5)
        
        jitter_buffer = self.jitter_buffers[buffer_key]
        
        # Add packet to jitter buffer
        jitter_buffer.add_packet(sequence_number, data)
        
        # Get packets ready for forwarding (in correct order)
        ready_packets = jitter_buffer.get_ready_packets()
        
        # Forward ordered packets to recipients
        recipients = self.client_registry.get_clients_in_channel(
            channel_id, 
            exclude_address=client_address
        )
        
        for packet_data in ready_packets:
            for recipient_address in recipients:
                self._send_packet(packet_data, recipient_address)
    
    def _send_packet(self, data, address):
        """Send packet (non-blocking)"""
        try:
            self.transport.sendto(data, address)
            self.traffic_bytes_out += len(data)
        except Exception as e:
            print(f"Failed to send to {address}: {e}")
    
    async def _handle_auth(self, client_address, channel_id, user_id, payload):
        """Handle authentication request"""
        try:
            funk_key = payload.decode('utf-8').strip()
            
            # Verify funk key against database (blocking I/O in thread pool)
            user = await asyncio.to_thread(self.db.verify_user, funk_key)
            
            if user:
                # Check channel permission
                if channel_id not in user['allowed_channels']:
                    print(f"🔒 User {user['username']} not authorized for channel {channel_id}")
                    auth_fail = build_auth_fail_packet(channel_id, user_id, b'Channel not authorized')
                    self._send_packet(auth_fail, client_address)
                    return
                
                # Store authentication info
                self.authenticated_clients[client_address] = {
                    'username': user['username'],
                    'user_id': user['id'],
                    'allowed_channels': user['allowed_channels'],
                    'funk_key': funk_key
                }
                
                # Log connection (in thread pool)
                await asyncio.to_thread(
                    self.db.log_connection, 
                    user['id'], channel_id, 'connect', client_address[0]
                )
                await asyncio.to_thread(self.db.update_last_seen, user['id'])
                
                print(f"✅ User {user['username']} authenticated for channel {channel_id}")
                
                # Send auth success
                auth_ok = build_auth_ok_packet(channel_id, user_id)
                self._send_packet(auth_ok, client_address)
            else:
                print(f"❌ Invalid funk key from {client_address}")
                auth_fail = build_auth_fail_packet(channel_id, user_id, b'Invalid funk key')
                self._send_packet(auth_fail, client_address)
                
        except Exception as e:
            print(f"Error handling auth: {e}")
            auth_fail = build_auth_fail_packet(channel_id, user_id, b'Auth error')
            self._send_packet(auth_fail, client_address)
    
    async def _cleanup_loop(self):
        """Background task for client cleanup"""
        while self.running:
            await asyncio.sleep(5)
            
            removed = self.client_registry.remove_stale_clients()
            if removed > 0:
                print(f"🧹 Removed {removed} stale clients")
                
                # Clean up authentication cache for removed clients
                stale_auth = []
                for addr in self.authenticated_clients:
                    if addr not in self.client_registry.clients:
                        stale_auth.append(addr)
                
                for addr in stale_auth:
                    username = self.authenticated_clients[addr]['username']
                    print(f"🔓 Logged out: {username}")
                    del self.authenticated_clients[addr]
                    
                    # Clean up jitter buffers
                    buffers_to_remove = [k for k in self.jitter_buffers if k[1] == addr]
                    for key in buffers_to_remove:
                        del self.jitter_buffers[key]
    
    async def _traffic_stats_loop(self):
        """Background task for traffic statistics"""
        while self.running:
            await asyncio.sleep(300)  # Every 5 minutes
            await self._save_traffic_stats()
    
    async def _save_traffic_stats(self):
        """Save traffic statistics to database"""
        from datetime import datetime
        
        if self.traffic_bytes_in > 0 or self.traffic_bytes_out > 0:
            try:
                await asyncio.to_thread(
                    self.db.record_traffic, 
                    self.traffic_bytes_in, 
                    self.traffic_bytes_out
                )
                print(f"📊 Traffic: ⬇️ {self._format_bytes(self.traffic_bytes_in)} | ⬆️ {self._format_bytes(self.traffic_bytes_out)}")
                self.traffic_bytes_in = 0
                self.traffic_bytes_out = 0
                self.last_traffic_save = datetime.now()
            except Exception as e:
                print(f"Fehler beim Speichern der Traffic-Statistiken: {e}")
    
    def _format_bytes(self, bytes_val):
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} TB"
    
    async def stop(self):
        """Stop server gracefully"""
        self.running = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._traffic_task:
            self._traffic_task.cancel()
        
        # Save remaining traffic stats
        if self.traffic_bytes_in > 0 or self.traffic_bytes_out > 0:
            await self._save_traffic_stats()
        
        if self.transport:
            self.transport.close()
        
        print("✅ AsyncIO Server stopped")
    
    def get_current_traffic(self):
        """Get current traffic counters"""
        return {
            "bytes_in": self.traffic_bytes_in,
            "bytes_out": self.traffic_bytes_out
        }
