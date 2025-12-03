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
        self.channel_id = channel_id  # Primary channel (for sending)
        self.secondary_channel = 41  # Always connected to channel 41
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
        self.authenticated = False  # Primary channel auth status
        self.secondary_authenticated = False  # Secondary channel auth status
        self.auth_error = None
        self.last_packet_time = None
        self.watchdog_thread = None
        self.keepalive_thread = None
        
        # Auto-Reconnect with exponential backoff
        self.auto_reconnect_enabled = True
        self.reconnect_attempts = 0
        self.max_reconnect_delay = 30  # seconds
        self.reconnect_thread = None
        self.intentional_disconnect = False
        
        # Connection Quality Monitoring
        self.ping_sent_time = None
        self.latency_ms = 0
        self.packet_loss_rate = 0.0
        self.packets_sent = 0
        self.packets_received = 0
        self.signal_strength = 100  # 0-100%
        self.jitter_ms = 0  # Jitter in milliseconds
        self.last_latencies = []  # Store last 10 latencies for jitter calculation
        self.quality_callback = None  # Callback for UI updates

    def connect(self):
        import time
        self.intentional_disconnect = False
        logger.info(f"Verbinde zu {self.server_ip}:{self.server_port}...")
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(2.0)  # Increased from 1.0 to reduce blocking
            self.running = True
            self.connection_confirmed = False
            self.authenticated = False
            self.last_packet_time = time.time()
            
            # Reset connection quality metrics
            self.packets_sent = 0
            self.packets_received = 0
            self.latency_ms = 0
            self.packet_loss_rate = 0.0
            self.signal_strength = 100
            
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # Start watchdog thread to detect connection loss
            self.watchdog_thread = threading.Thread(target=self._connection_watchdog, daemon=True)
            self.watchdog_thread.start()
            
            # Start keepalive thread to send periodic packets
            self.keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            self.keepalive_thread.start()
            
            # Send authentication packets for both channels
            if self.funk_key:
                self._send_auth_primary()
                self._send_auth_secondary()
                logger.debug(f"Warte auf AUTH_OK vom Server... (Primär: {self.channel_id}, Sekundär: {self.secondary_channel})")
            else:
                logger.error("⚠️ Kein Funk-Schlüssel vorhanden!")
            
            # Notify immediate connection (will be confirmed when auth succeeds)
            if self.connection_callback:
                self.connection_callback(True)
            
            # Reset reconnect counter on successful connect
            self.reconnect_attempts = 0
            
        except Exception as e:
            logger.error(f"Verbindungsfehler: {e}")
            if self.auto_reconnect_enabled:
                self._schedule_reconnect()
    
    def _send_auth_primary(self):
        """Send authentication packet for primary channel"""
        try:
            auth_packet = build_auth_packet(self.channel_id, self.user_id, self.funk_key)
            bytes_sent = self.socket.sendto(auth_packet, (self.server_ip, self.server_port))
            logger.info(f"🔑 Authentifizierung gesendet für Primär-Kanal {self.channel_id} ({bytes_sent} bytes)")
        except Exception as e:
            logger.error(f"Fehler bei Authentifizierung (Primär): {e}", exc_info=True)
    
    def _send_auth_secondary(self):
        """Send authentication packet for secondary channel 41"""
        try:
            auth_packet = build_auth_packet(self.secondary_channel, self.user_id, self.funk_key)
            bytes_sent = self.socket.sendto(auth_packet, (self.server_ip, self.server_port))
            logger.info(f"🔑 Authentifizierung gesendet für Sekundär-Kanal {self.secondary_channel} ({bytes_sent} bytes)")
        except Exception as e:
            logger.error(f"Fehler bei Authentifizierung (Sekundär): {e}", exc_info=True)

    def disconnect(self, intentional=True):
        """Disconnect from server
        
        Args:
            intentional: If True, disables auto-reconnect. If False, triggers reconnect.
        """
        self.intentional_disconnect = intentional
        self.running = False
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Trigger auto-reconnect if disconnect was unintentional
        if not intentional and self.auto_reconnect_enabled:
            logger.warning("🔄 Unbeabsichtigte Trennung erkannt, starte Auto-Reconnect...")
            self._schedule_reconnect()

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
            self.packets_sent += 1
        except Exception as e:
            logger.error(f"Fehler beim Audio-Senden: {e}")
            self.signal_strength = max(0, self.signal_strength - 10)

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
                    self.packets_received += 1
                    
                    # Handle AUTH_OK packets
                    if packet_type == PACKET_TYPE_AUTH_OK:
                        # Check which channel was authenticated
                        if channel_id == self.channel_id:
                            self.authenticated = True
                            logger.info(f"✅ Authentifizierung erfolgreich für Primär-Kanal {channel_id}!")
                        elif channel_id == self.secondary_channel:
                            self.secondary_authenticated = True
                            logger.info(f"✅ Authentifizierung erfolgreich für Sekundär-Kanal {channel_id}!")
                        
                        # Connection is confirmed when both channels are authenticated
                        if self.authenticated and self.secondary_authenticated:
                            self.connection_confirmed = True
                            logger.info("🎉 Beide Kanäle verbunden!")
                        
                        self.signal_strength = 100
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
                    
                    # Handle PONG packets (heartbeat response with latency calculation)
                    if packet_type == PACKET_TYPE_PONG:
                        # Calculate latency
                        if self.ping_sent_time:
                            latency = (time.time() - self.ping_sent_time) * 1000  # Convert to ms
                            self.latency_ms = int(latency)
                            
                            # Calculate jitter (variation in latency)
                            self.last_latencies.append(self.latency_ms)
                            if len(self.last_latencies) > 10:
                                self.last_latencies.pop(0)
                            if len(self.last_latencies) >= 2:
                                jitter_values = [abs(self.last_latencies[i] - self.last_latencies[i-1]) 
                                               for i in range(1, len(self.last_latencies))]
                                self.jitter_ms = int(sum(jitter_values) / len(jitter_values))
                            
                            logger.debug(f"PONG empfangen (Latenz: {self.latency_ms}ms, Jitter: {self.jitter_ms}ms)")
                            
                            # Update signal strength based on latency
                            if latency < 50:
                                self.signal_strength = min(100, self.signal_strength + 2)
                            elif latency > 200:
                                self.signal_strength = max(50, self.signal_strength - 5)
                        
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
                            # Pass sender's channel_id to callback
                            self.audio_callback(payload, channel_id)
                        
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
        """Send PING packets every 5 seconds with latency measurement"""
        import time
        keepalive_interval = 5.0  # Reduced from 1s to 5s (80% less server load)
        
        while self.running:
            time.sleep(keepalive_interval)
            if self.running and self.socket:
                try:
                    # Record ping send time for latency calculation
                    self.ping_sent_time = time.time()
                    
                    ping_packet = build_ping_packet(self.channel_id, self.user_id)
                    self.socket.sendto(ping_packet, (self.server_ip, self.server_port))
                    self.packets_sent += 1
                    
                    logger.debug(f"PING gesendet (last_packet: {time.time() - self.last_packet_time:.1f}s ago, latency: {self.latency_ms}ms)")
                    
                    # Update connection quality
                    self._update_connection_quality()
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"Keepalive fehlgeschlagen: {e}")
                        self.signal_strength = max(0, self.signal_strength - 20)
    
    def _connection_watchdog(self):
        """Monitor connection and disconnect if no packets received for 10 seconds"""
        import time
        timeout_threshold = 10.0  # Increased from 3s to 10s (prevents false positives)
        warning_threshold = 7.0   # Warning at 7s
        
        while self.running:
            time.sleep(1.0)
            if self.last_packet_time:
                time_since_last_packet = time.time() - self.last_packet_time
                
                # Update signal strength based on response time
                if time_since_last_packet < 2.0:
                    self.signal_strength = min(100, self.signal_strength + 5)
                elif time_since_last_packet > 5.0:
                    self.signal_strength = max(0, self.signal_strength - 10)
                
                # Warning at 7 seconds
                if time_since_last_packet > warning_threshold and time_since_last_packet < timeout_threshold:
                    logger.debug(f"⚠️ Schwache Verbindung: {time_since_last_packet:.1f}s ohne Paket")
                    self.signal_strength = max(20, self.signal_strength)
                
                # Timeout at 10 seconds
                if time_since_last_packet > timeout_threshold:
                    logger.warning(f"❌ Verbindung zum Server verloren (Timeout: {time_since_last_packet:.1f}s ohne Paket)")
                    logger.warning(f"   Letztes Paket: {time.strftime('%H:%M:%S', time.localtime(self.last_packet_time))}")
                    logger.warning(f"   Authenticated: {self.authenticated}, Connection confirmed: {self.connection_confirmed}")
                    
                    self.signal_strength = 0
                    
                    if self.disconnect_callback:
                        self.disconnect_callback()
                    
                    # Trigger auto-reconnect
                    self.disconnect(intentional=False)
                    break
    
    def set_channel(self, channel_id):
        """Change primary channel with re-authentication (used for settings change)"""
        with self.lock:
            old_channel = self.channel_id
            self.channel_id = channel_id
            # Re-authenticate for new primary channel (secondary stays connected)
            if self.funk_key and old_channel != channel_id:
                logger.info(f"Primär-Kanal gewechselt: {old_channel} → {channel_id}, authentifiziere neu...")
                self.authenticated = False
                self._send_auth_primary()
                # Secondary channel 41 bleibt verbunden, keine neue Auth nötig
    
    def set_transmit_channel(self, channel_id):
        """Switch transmit channel without re-authentication (for hotkeys)"""
        with self.lock:
            old_channel = self.channel_id
            self.channel_id = channel_id
            logger.debug(f"Sende-Kanal gewechselt: {old_channel} → {channel_id} (ohne Re-Auth)")
    
    def _schedule_reconnect(self):
        """Schedule reconnect with exponential backoff"""
        if not self.auto_reconnect_enabled or self.intentional_disconnect:
            return
        
        # Calculate backoff delay: 1s, 2s, 4s, 8s, 16s, max 30s
        delay = min(2 ** self.reconnect_attempts, self.max_reconnect_delay)
        self.reconnect_attempts += 1
        
        logger.info(f"🔄 Reconnect geplant in {delay}s (Versuch {self.reconnect_attempts})")
        
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
        
        self.reconnect_thread = threading.Thread(
            target=self._reconnect_with_delay, 
            args=(delay,), 
            daemon=True
        )
        self.reconnect_thread.start()
    
    def _reconnect_with_delay(self, delay):
        """Wait and then reconnect"""
        import time
        time.sleep(delay)
        
        if not self.intentional_disconnect and self.auto_reconnect_enabled:
            logger.info(f"🔄 Reconnect-Versuch {self.reconnect_attempts}...")
            try:
                self.connect()
            except Exception as e:
                logger.error(f"Reconnect fehlgeschlagen: {e}")
                # Schedule next reconnect attempt
                self._schedule_reconnect()
    
    def _update_connection_quality(self):
        """Update connection quality metrics and notify UI"""
        # Calculate packet loss rate
        if self.packets_sent > 0:
            expected_received = self.packets_sent
            self.packet_loss_rate = max(0.0, 1.0 - (self.packets_received / expected_received))
        
        # Adjust signal strength based on packet loss
        if self.packet_loss_rate > 0.1:  # > 10% loss
            self.signal_strength = max(30, self.signal_strength - 15)
        elif self.packet_loss_rate < 0.01:  # < 1% loss
            self.signal_strength = min(100, self.signal_strength + 3)
        
        # Notify UI if callback is set
        if self.quality_callback:
            quality_data = {
                'latency_ms': self.latency_ms,
                'packet_loss': self.packet_loss_rate * 100,  # as percentage
                'signal_strength': self.signal_strength,
                'packets_sent': self.packets_sent,
                'packets_received': self.packets_received
            }
            self.quality_callback(quality_data)
    
    def get_connection_quality(self):
        """Get current connection quality metrics
        
        Returns:
            dict: Connection quality data with latency, packet loss, signal strength
        """
        return {
            'latency_ms': self.latency_ms,
            'packet_loss_percent': round(self.packet_loss_rate * 100, 2),
            'signal_strength': self.signal_strength,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'jitter_ms': self.jitter_ms,
            'status': self._get_connection_status(),
            'authenticated': self.authenticated,
            'connected': self.connection_confirmed
        }
    
    def _get_connection_status(self):
        """Get human-readable connection status"""
        if not self.connection_confirmed:
            return "Verbinde..."
        elif not self.authenticated:
            return "Authentifiziere..."
        elif self.signal_strength >= 80:
            return "Ausgezeichnet"
        elif self.signal_strength >= 60:
            return "Gut"
        elif self.signal_strength >= 40:
            return "Mittel"
        elif self.signal_strength >= 20:
            return "Schwach"
        else:
            return "Sehr schwach"
    
    def set_quality_callback(self, callback):
        """Set callback for connection quality updates
        
        Args:
            callback: Function that receives quality_data dict
        """
        self.quality_callback = callback
    
    def enable_auto_reconnect(self, enabled=True):
        """Enable or disable auto-reconnect
        
        Args:
            enabled: True to enable, False to disable
        """
        self.auto_reconnect_enabled = enabled
        logger.info(f"Auto-Reconnect: {'aktiviert' if enabled else 'deaktiviert'}")
