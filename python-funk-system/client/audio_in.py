import sounddevice as sd
import numpy as np
import threading
from scipy import signal
from config import SAMPLE_RATE, FRAME_SIZE_MS


class AudioInput:
    def __init__(self, callback, device=None, noise_gate_enabled=False, noise_gate_threshold=-40.0):
        self.callback = callback
        self.device = device
        self.sample_rate = SAMPLE_RATE
        self.frame_size = int(SAMPLE_RATE * FRAME_SIZE_MS / 1000)
        self.stream = None
        self.is_recording = False
        self.lock = threading.Lock()
        self.stream_started = False
        
        # Noise gate settings
        self.noise_gate_enabled = noise_gate_enabled
        self.noise_gate_threshold = noise_gate_threshold  # in dB
        self.gate_open = False
        self.gate_hold_time = 0.2  # seconds to keep gate open after signal drops
        self.gate_hold_samples = int(self.gate_hold_time * self.sample_rate)
        self.gate_hold_counter = 0
        
        # Level monitoring for UI
        self.current_level_db = -100.0
        self.level_callback = None
        
        sos = signal.butter(4, [300, 3400], btype='bandpass', fs=self.sample_rate, output='sos')
        self.sos = sos
        self.zi = signal.sosfilt_zi(sos)

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio input status: {status}")
        
        with self.lock:
            audio = indata[:, 0].copy()
            
            # Calculate current audio level in dB
            rms = np.sqrt(np.mean(audio**2))
            if rms > 0:
                level_db = 20 * np.log10(rms)
            else:
                level_db = -100.0
            self.current_level_db = level_db
            
            # Send level to UI callback if registered
            if self.level_callback:
                self.level_callback(level_db)
            
            if self.is_recording and self.callback:
                filtered, self.zi = signal.sosfilt(self.sos, audio, zi=self.zi)
                
                compressed = np.tanh(filtered * 2.0) * 0.9
                
                # Apply noise gate if enabled
                if self.noise_gate_enabled:
                    if level_db > self.noise_gate_threshold:
                        self.gate_open = True
                        self.gate_hold_counter = self.gate_hold_samples
                    elif self.gate_hold_counter > 0:
                        self.gate_hold_counter -= len(compressed)
                        self.gate_open = True
                    else:
                        self.gate_open = False
                    
                    # Only send audio if gate is open
                    if self.gate_open:
                        audio_data = (compressed * 32767).astype(np.int16).tobytes()
                        self.callback(audio_data)
                else:
                    # No noise gate, always send
                    audio_data = (compressed * 32767).astype(np.int16).tobytes()
                    self.callback(audio_data)

    def start_recording(self):
        with self.lock:
            if not self.stream_started:
                try:
                    self.stream = sd.InputStream(
                        device=self.device,
                        samplerate=self.sample_rate,
                        channels=1,
                        dtype=np.float32,
                        blocksize=self.frame_size,
                        callback=self.audio_callback
                    )
                    self.stream.start()
                    self.stream_started = True
                    print(f"Audio-Stream gestartet (Device: {self.device}, Sample Rate: {self.sample_rate})")
                except Exception as e:
                    print(f"Fehler beim Starten des Audio-Streams: {e}")
                    return
            
            if not self.is_recording:
                self.is_recording = True
                print("Recording gestartet (Taste gedrückt)")

    def stop_recording(self):
        with self.lock:
            if self.is_recording:
                self.is_recording = False
                print("Recording gestoppt (Taste losgelassen)")

    def set_noise_gate(self, enabled, threshold_db):
        """Update noise gate settings"""
        with self.lock:
            self.noise_gate_enabled = enabled
            self.noise_gate_threshold = threshold_db
    
    def set_level_callback(self, callback):
        """Set callback for level monitoring (for UI)"""
        with self.lock:
            self.level_callback = callback
    
    def get_current_level(self):
        """Get current audio level in dB"""
        with self.lock:
            return self.current_level_db

    def close(self):
        with self.lock:
            self.is_recording = False
            self.stream_started = False
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except:
                    pass
                self.stream = None
