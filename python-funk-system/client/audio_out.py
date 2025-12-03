import sounddevice as sd
import numpy as np
import queue
import threading
from scipy import signal
from config import SAMPLE_RATE, FRAME_SIZE_MS, JITTER_BUFFER_SIZE


class AudioOutput:
    def __init__(self, device=None):
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
        
        sos = signal.butter(4, [300, 3400], btype='bandpass', fs=self.sample_rate, output='sos')
        self.sos = sos
        self.zi = signal.sosfilt_zi(sos)

    def audio_callback(self, outdata, frames, time_info, status):
        if status:
            print(f"Audio output status: {status}")
        
        if self.buffering:
            if self.audio_queue.qsize() >= JITTER_BUFFER_SIZE:
                self.buffering = False
                self.squelch_playing = True
                print(f"Jitter-Buffer gefüllt ({JITTER_BUFFER_SIZE} Frames), starte Wiedergabe")
            else:
                outdata.fill(0)
                return
        
        try:
            audio_data = self.audio_queue.get_nowait()
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
