import sounddevice as sd
import numpy as np
import queue
import threading
import time
from scipy import signal
import os
import sys

# Add current directory and libs directory to DLL search path for opus.dll
# Must be done BEFORE importing opuslib
current_dir = os.path.dirname(os.path.abspath(__file__))
libs_dir = os.path.join(current_dir, 'libs')

# Method 1: Add to Windows DLL search path (Python 3.8+)
if hasattr(os, 'add_dll_directory'):
    if os.path.exists(current_dir):
        os.add_dll_directory(current_dir)
    if os.path.exists(libs_dir):
        os.add_dll_directory(libs_dir)

# Method 2: Add to PATH environment variable (fallback)
if os.path.exists(libs_dir):
    os.environ['PATH'] = libs_dir + os.pathsep + current_dir + os.pathsep + os.environ.get('PATH', '')

try:
    import opuslib
    OPUS_AVAILABLE = True
except (ImportError, Exception) as e:
    OPUS_AVAILABLE = False
    print(f"⚠️ opuslib not available ({e}), using RAW PCM mode")
from config import SAMPLE_RATE, FRAME_SIZE_MS, JITTER_BUFFER_SIZE, AUDIO_CODEC, OPUS_FRAME_SIZE


class AudioOutput:
    def __init__(self, device=None, adaptive_jitter_buffer=True):
        self.device = device
        self.sample_rate = SAMPLE_RATE
        self.frame_size = int(SAMPLE_RATE * FRAME_SIZE_MS / 1000)
        self.audio_queue = queue.Queue(maxsize=20)
        self.stream = None
        self.running = False
        self.lock = threading.Lock()
        self.buffering = True
        self.buffer_count = 0
        self.squelch_playing = False
        self.volume = 1.0  # Volume multiplier (0.0 to 1.0)
        
        # Adaptive Jitter Buffer
        self.adaptive_jitter_buffer = adaptive_jitter_buffer
        self.jitter_buffer_size = JITTER_BUFFER_SIZE  # Start with config default
        self.min_jitter_buffer = 3   # Minimum buffer size
        self.max_jitter_buffer = 20  # Maximum buffer size
        self.underrun_count = 0      # Track buffer underruns
        self.last_adjust_time = time.time()
        if self.adaptive_jitter_buffer:
            print(f"✅ Adaptive Jitter Buffer enabled (initial: {self.jitter_buffer_size} frames)")
        
        # Opus decoder initialization
        self.use_opus = AUDIO_CODEC == 'opus' and OPUS_AVAILABLE
        if self.use_opus:
            try:
                self.opus_decoder = opuslib.Decoder(SAMPLE_RATE, 1)
                print("✅ Opus Decoder initialized")
            except Exception as e:
                print(f"❌ Opus decoder init failed: {e}, falling back to PCM")
                self.use_opus = False
        else:
            self.opus_decoder = None
            print("📡 Using RAW PCM audio format")
        
        sos = signal.butter(4, [300, 3400], btype='bandpass', fs=self.sample_rate, output='sos')
        self.sos = sos
        self.zi = signal.sosfilt_zi(sos)

    def audio_callback(self, outdata, frames, time_info, status):
        if status:
            print(f"Audio output status: {status}")
        
        if self.buffering:
            # Use adaptive buffer size
            current_buffer_target = self.jitter_buffer_size if self.adaptive_jitter_buffer else JITTER_BUFFER_SIZE
            
            if self.audio_queue.qsize() >= current_buffer_target:
                self.buffering = False
                self.squelch_playing = True
                print(f"Jitter-Buffer gefüllt ({current_buffer_target} Frames), starte Wiedergabe")
            else:
                outdata.fill(0)
                return
        
        try:
            audio_data = self.audio_queue.get_nowait()
            
            # Adaptive Jitter Buffer: Monitor queue health
            if self.adaptive_jitter_buffer:
                self._adjust_jitter_buffer()
            
            # Decode Opus if enabled
            if self.use_opus and self.opus_decoder:
                try:
                    pcm_data = self.opus_decoder.decode(audio_data, OPUS_FRAME_SIZE)
                    audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32767.0
                except Exception as e:
                    # Fallback: try as RAW PCM
                    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32767.0
            else:
                # RAW PCM
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32767.0
            
            if len(audio_array) < frames:
                audio_array = np.pad(audio_array, (0, frames - len(audio_array)))
            elif len(audio_array) > frames:
                audio_array = audio_array[:frames]
            
            if self.squelch_playing:
                t = np.linspace(0, len(audio_array) / self.sample_rate, len(audio_array))
                squelch = np.sin(2 * np.pi * 1000 * t) * 0.15 * np.exp(-t * 20)
                audio_array[:len(squelch)] += squelch
                self.squelch_playing = False
            
            filtered, self.zi = signal.sosfilt(self.sos, audio_array, zi=self.zi)
            
            # Apply volume
            filtered = filtered * self.volume
            
            outdata[:, 0] = filtered
        except queue.Empty:
            outdata.fill(0)
            # Track underruns for adaptive buffer
            if self.adaptive_jitter_buffer:
                self.underrun_count += 1

    def start(self):
        with self.lock:
            if not self.stream:
                self.buffering = True
                self.buffer_count = 0
                self.stream = sd.OutputStream(
                    device=self.device,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype=np.float32,
                    blocksize=self.frame_size,
                    callback=self.audio_callback
                )
                self.stream.start()
                self.running = True
                print(f"Audio-Output gestartet (Sample Rate: {self.sample_rate}, Block Size: {self.frame_size})")

    def play_audio(self, audio_data):
        if self.running:
            try:
                self.audio_queue.put_nowait(audio_data)
            except queue.Full:
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(audio_data)
                except:
                    pass
    
    def set_volume(self, volume_percent):
        """Set output volume (0-100)"""
        self.volume = max(0.0, min(1.0, volume_percent / 100.0))

    def _adjust_jitter_buffer(self):
        """Adjust jitter buffer size based on network conditions"""
        current_time = time.time()
        
        # Only adjust every 5 seconds
        if current_time - self.last_adjust_time < 5.0:
            return
        
        self.last_adjust_time = current_time
        queue_size = self.audio_queue.qsize()
        
        # If queue is running low, increase buffer
        if queue_size <= 2:
            if self.jitter_buffer_size < self.max_jitter_buffer:
                self.jitter_buffer_size = min(self.jitter_buffer_size + 2, self.max_jitter_buffer)
                print(f"📈 Jitter buffer increased to {self.jitter_buffer_size} frames (low queue)")
        
        # If queue is consistently full, decrease buffer
        elif queue_size >= self.max_jitter_buffer - 2:
            if self.jitter_buffer_size > self.min_jitter_buffer:
                self.jitter_buffer_size = max(self.jitter_buffer_size - 1, self.min_jitter_buffer)
                print(f"📉 Jitter buffer decreased to {self.jitter_buffer_size} frames (high queue)")
    
    def get_jitter_buffer_stats(self):
        """Get current jitter buffer statistics
        
        Returns:
            dict: Buffer stats with size, queue, underruns
        """
        return {
            'buffer_size': self.jitter_buffer_size,
            'queue_size': self.audio_queue.qsize(),
            'underruns': self.underrun_count,
            'adaptive': self.adaptive_jitter_buffer
        }

    def stop(self):
        with self.lock:
            self.running = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            self.buffering = True
            self.buffer_count = 0
