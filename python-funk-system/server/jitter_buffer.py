from collections import deque
import time


class JitterBuffer:
    """
    Jitter Buffer for audio packet reordering
    
    Solves UDP out-of-order packet delivery problem:
    - Buffers incoming packets
    - Sorts by sequence number
    - Releases packets in correct order
    - Handles sequence number wraparound (0-65535)
    
    Trade-off: Adds ~50-100ms latency for stable audio playback
    """
    
    def __init__(self, buffer_size=5, max_age_ms=200):
        """
        Initialize jitter buffer
        
        Args:
            buffer_size: Number of packets to buffer (5 = ~100ms at 20ms/packet)
            max_age_ms: Maximum age of packet before forced release (prevents stalling)
        """
        self.buffer_size = buffer_size
        self.max_age_ms = max_age_ms
        self.buffer = {}  # {sequence_number: (data, timestamp)}
        self.next_sequence = None  # Next expected sequence number
        self.ready_queue = deque()  # Ordered packets ready for delivery
    
    def add_packet(self, sequence_number, data):
        """
        Add packet to jitter buffer
        
        Args:
            sequence_number: Packet sequence number (0-65535, wraps around)
            data: Raw packet data
        """
        timestamp = time.time()
        
        # Initialize next_sequence on first packet
        if self.next_sequence is None:
            self.next_sequence = sequence_number
        
        # Store packet with timestamp
        self.buffer[sequence_number] = (data, timestamp)
        
        # Try to release ordered packets
        self._process_buffer()
    
    def get_ready_packets(self):
        """
        Get packets ready for forwarding (in correct order)
        
        Returns:
            List of packet data ready to send
        """
        ready = list(self.ready_queue)
        self.ready_queue.clear()
        return ready
    
    def _process_buffer(self):
        """Process buffer and move ordered packets to ready queue"""
        current_time = time.time()
        
        while True:
            # Check if next expected packet is available
            if self.next_sequence in self.buffer:
                data, timestamp = self.buffer.pop(self.next_sequence)
                self.ready_queue.append(data)
                self.next_sequence = self._increment_sequence(self.next_sequence)
            else:
                # Next packet not available yet
                break
        
        # Force-release old packets to prevent buffer stalling
        self._release_old_packets(current_time)
        
        # Prevent buffer overflow
        self._trim_buffer()
    
    def _release_old_packets(self, current_time):
        """Force release packets that are too old (prevents stalling)"""
        old_packets = []
        
        for seq, (data, timestamp) in self.buffer.items():
            age_ms = (current_time - timestamp) * 1000
            if age_ms > self.max_age_ms:
                old_packets.append((seq, data))
        
        if old_packets:
            # Sort by sequence number and release
            old_packets.sort(key=lambda x: x[0])
            for seq, data in old_packets:
                self.ready_queue.append(data)
                del self.buffer[seq]
                print(f"⚠️ Jitter buffer: Force-released old packet {seq} (age: {self.max_age_ms}ms)")
            
            # Update next_sequence to after released packets
            if old_packets:
                self.next_sequence = self._increment_sequence(old_packets[-1][0])
    
    def _trim_buffer(self):
        """Prevent buffer overflow by releasing oldest packets"""
        if len(self.buffer) > self.buffer_size * 2:
            # Buffer is too full - release oldest packets
            sorted_packets = sorted(self.buffer.items(), key=lambda x: x[1][1])  # Sort by timestamp
            
            excess_count = len(self.buffer) - self.buffer_size
            for i in range(excess_count):
                seq, (data, _) = sorted_packets[i]
                self.ready_queue.append(data)
                del self.buffer[seq]
            
            print(f"⚠️ Jitter buffer overflow: Released {excess_count} packets")
    
    def _increment_sequence(self, seq):
        """Increment sequence number with wraparound (0-65535)"""
        return (seq + 1) % 65536
    
    def get_stats(self):
        """Get buffer statistics for monitoring"""
        return {
            "buffer_size": len(self.buffer),
            "ready_queue_size": len(self.ready_queue),
            "next_sequence": self.next_sequence,
            "max_buffer_size": self.buffer_size
        }
