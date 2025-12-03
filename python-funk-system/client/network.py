import socket
import threading
import logging
from protocol import (build_packet, parse_header, build_ping_packet, build_auth_packet,
                     PACKET_TYPE_PONG, PACKET_TYPE_AUDIO, PACKET_TYPE_AUTH_OK, PACKET_TYPE_AUTH_FAIL)

logger = logging.getLogger('DFG-Funk')


class NetworkClient:
    def __init__(self, server_ip, server_port, channel_id, user_id, audio_callback, connection_callback=None, disconnect_callback=None, funk_key=None):
        self.server_ip = server_ip
        self.server_port = server_port
        self.channel_id = channel_id
        self.user_id = user_id
        self.audio_callback = audio_callback
        self.connection_callback = connection_callback
        self.disconnect_callback = disconnect_callback
        self.funk_key = funk_key
        self.socket = None
        self.running = False
        self.receive_thread = None
        self.sequence_number = 0
        self.lock = threading.Lock()
        self.connection_confirmed = False
        self.authenticated = False
        self.auth_error = None
        self.last_packet_time = None
        self.watchdog_thread = None
        self.keepalive_thread = None

    def connect(self):
        import time
        logger.info(f"Verbinde zu {self.server_ip}:{self.server_port}...")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)
        self.running = True
        self.connection_confirmed = False
        self.authenticated = False
        self.last_packet_time = time.time()
        
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        
        # Start watchdog thread to detect connection loss
        self.watchdog_thread = threading.Thread(target=self._connection_watchdog, daemon=True)
        self.watchdog_thread.start()
        
        # Start keepalive thread to send periodic packets
        self.keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        self.keepalive_thread.start()
        
        # Send authentication packet
        if self.funk_key:
            self._send_auth()
            logger.debug(f"Warte auf AUTH_OK vom Server... (Socket: {self.socket.getsockname()})")
        else:
            logger.error("⚠️ Kein Funk-Schlüssel vorhanden!")
        
        # Notify immediate connection (will be confirmed when auth succeeds)
        if self.connection_callback:
            self.connection_callback(True)
    
    def _send_auth(self):
        """Send authentication packet to server"""
        try:
            auth_packet = build_auth_packet(self.channel_id, self.user_id, self.funk_key)
            bytes_sent = self.socket.sendto(auth_packet, (self.server_ip, self.server_port))
            logger.info(f"🔑 Authentifizierung gesendet für Kanal {self.channel_id} ({bytes_sent} bytes an {self.server_ip}:{self.server_port})")
        except Exception as e:
            logger.error(f"Fehler bei Authentifizierung: {e}", exc_info=True)

    def disconnect(self):
        self.running = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def send_audio(self, audio_data):
        if not self.running or not self.socket:
            return
        
        # Only send audio if authenticated
        if not self.authenticated:
            logger.debug("Audio nicht gesendet - nicht authentifiziert")
            return
        
        with self.lock:
            packet = build_packet(self.channel_id, self.user_id, self.sequence_number, audio_data)
            self.sequence_number = (self.sequence_number + 1) % 65536
        
        try:
            self.socket.sendto(packet, (self.server_ip, self.server_port))
        except Exception as e:
            logger.error(f"Fehler beim Audio-Senden: {e}")

    def _receive_loop(self):
        print(f"Empfangs-Thread gestartet, warte auf Pakete...")
        packet_count = 0
        while self.running:
            try:
                if not self.socket:
                    break
                data, addr = self.socket.recvfrom(4096)
                packet_type, channel_id, user_id, sequence_number, payload = parse_header(data)
                
                logger.debug(f"Paket empfangen: type={packet_type}, channel={channel_id}, addr={addr}")
                
                if channel_id is not None:
                    import time
                    self.last_packet_time = time.time()
                    
                    # Handle AUTH_OK packets
                    if packet_type == PACKET_TYPE_AUTH_OK:
                        self.authenticated = True
                        self.connection_confirmed = True
                        logger.info("✅ Authentifizierung erfolgreich!")
                        continue
                    
                    # Handle AUTH_FAIL packets
                    if packet_type == PACKET_TYPE_AUTH_FAIL:
                        reason = payload.decode('utf-8') if payload else 'Unbekannter Fehler'
                        self.auth_error = f"Auth-Fehler: {reason}"
                        logger.error(f"❌ Authentifizierung fehlgeschlagen: {reason}")
                        if self.disconnect_callback:
                            self.disconnect_callback()
                        self.running = False
                        continue
                    
                    # Handle PONG packets (heartbeat response)
                    if packet_type == PACKET_TYPE_PONG:
                        logger.debug("PONG empfangen")
                        if not self.connection_confirmed:
                            self.connection_confirmed = True
                            logger.info("Heartbeat bestätigt - Verbindung aktiv")
                        continue
                    
                    # Handle AUDIO packets
                    if packet_type == PACKET_TYPE_AUDIO and payload:
                        packet_count += 1
                        if packet_count == 1:
                            print(f"Erste Audio-Pakete empfangen...")
                        if self.audio_callback:
                            self.audio_callback(payload)
                        
            except socket.timeout:
                continue
            except OSError as e:
                logger.debug(f"Socket closed: {e}")
                break
            except Exception as e:
                if self.running:
                    logger.error(f"Fehler beim Empfangen: {e}")
                break
        logger.info("Empfangs-Thread beendet")

    def _keepalive_loop(self):
        """Send PING packets every second to detect connection loss"""
        import time
        while self.running:
            time.sleep(1.0)
            if self.running and self.socket:
                try:
                    ping_packet = build_ping_packet(self.channel_id, self.user_id)
                    self.socket.sendto(ping_packet, (self.server_ip, self.server_port))
                    logger.debug(f"PING gesendet (last_packet: {time.time() - self.last_packet_time:.1f}s ago)")
                except Exception as e:
                    if self.running:
                        logger.error(f"Keepalive fehlgeschlagen: {e}")
    
    def _connection_watchdog(self):
        """Monitor connection and disconnect if no packets received for 3 seconds"""
        import time
        while self.running:
            time.sleep(1.0)
            if self.last_packet_time:
                time_since_last_packet = time.time() - self.last_packet_time
                if time_since_last_packet > 3.0:  # 3 seconds timeout
                    logger.warning(f"⚠️ Verbindung zum Server verloren (Timeout: {time_since_last_packet:.1f}s ohne Paket)")
                    logger.warning(f"   Letztes Paket: {time.strftime('%H:%M:%S', time.localtime(self.last_packet_time))}")
                    logger.warning(f"   Authenticated: {self.authenticated}, Connection confirmed: {self.connection_confirmed}")
                    if self.disconnect_callback:
                        self.disconnect_callback()
                    break
                elif time_since_last_packet > 1.5:
                    logger.debug(f"⏱️ Kein Paket seit {time_since_last_packet:.1f}s...")
    
    def set_channel(self, channel_id):
        with self.lock:
            old_channel = self.channel_id
            self.channel_id = channel_id
            # Re-authenticate for new channel
            if self.funk_key and old_channel != channel_id:
                logger.info(f"Kanal gewechselt: {old_channel} → {channel_id}, authentifiziere neu...")
                self.authenticated = False
                self._send_auth()
