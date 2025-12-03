import sounddevice as sd
import numpy as np
import threading
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

# Try WebRTC VAD first (best quality), fallback to Python VAD
try:
    import webrtcvad
    VAD_AVAILABLE = True
    VAD_TYPE = "WebRTC"
    print("✅ Using WebRTC VAD (best quality)")
except ImportError:
    try:
        import python_vad as webrtcvad
        VAD_AVAILABLE = True
        VAD_TYPE = "Python"
        print("✅ Using Python VAD (webrtcvad not available)")
    except ImportError:
        VAD_AVAILABLE = False
        VAD_TYPE = "None"
        print("⚠️ No VAD available, using simple noise gate")

from config import SAMPLE_RATE, FRAME_SIZE_MS, AUDIO_CODEC, OPUS_BITRATE, OPUS_FRAME_SIZE


class AudioInput:
    def __init__(self, callback, device=None, noise_gate_enabled=False, noise_gate_threshold=-40.0, 
                 use_vad=True, use_agc=True):
        self.callback = callback
        self.device = device
        self.sample_rate = SAMPLE_RATE
        self.frame_size = int(SAMPLE_RATE * FRAME_SIZE_MS / 1000)
        self.stream = None
        self.is_recording = False
        self.lock = threading.Lock()
        self.stream_started = False
        
        # Voice Activity Detection - Better than simple noise gate
        self.use_vad = use_vad and VAD_AVAILABLE
        if self.use_vad:
            try:
                self.vad = webrtcvad.Vad(2)  # Aggressiveness: 0-3 (2 = moderate)
                self.vad_frames = []  # Buffer for VAD processing
                print(f"✅ VAD enabled (type: {VAD_TYPE}, mode: 2)")
            except Exception as e:
                print(f"❌ VAD init failed: {e}, falling back to noise gate")
                self.use_vad = False
        else:
            self.vad = None
            if not VAD_AVAILABLE:
                print("🎯 Using simple noise gate (no VAD available)")
        
        # Fallback: Simple noise gate (if VAD disabled/unavailable)
        self.noise_gate_enabled = noise_gate_enabled or not self.use_vad
        self.noise_gate_threshold = noise_gate_threshold  # in dB
        self.gate_open = False
        self.gate_hold_time = 0.2  # seconds to keep gate open after signal drops
        self.gate_hold_samples = int(self.gate_hold_time * self.sample_rate)
        self.gate_hold_counter = 0
        
        # Automatic Gain Control (AGC)
        self.use_agc = use_agc
        self.agc_target_level = 0.3  # Target RMS level
        self.agc_gain = 1.0  # Current gain multiplier
        self.agc_attack = 0.01  # How fast to increase gain
        self.agc_release = 0.001  # How slow to decrease gain
        if self.use_agc:
            print("✅ Automatic Gain Control (AGC) enabled")
        
        # Level monitoring for UI
        self.current_level_db = -100.0
        self.level_callback = None
        
        # Opus encoder initialization
        self.use_opus = AUDIO_CODEC == 'opus' and OPUS_AVAILABLE
        if self.use_opus:
            try:
                self.opus_encoder = opuslib.Encoder(SAMPLE_RATE, 1, opuslib.APPLICATION_VOIP)
                self.opus_encoder.bitrate = OPUS_BITRATE
                print(f"✅ Opus Encoder initialized (bitrate: {OPUS_BITRATE/1000}kbps)")
            except Exception as e:
                print(f"❌ Opus encoder init failed: {e}, falling back to PCM")
                self.use_opus = False
        else:
            self.opus_encoder = None
            print("📡 Using RAW PCM audio format")
        
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
            
            # Process audio for recording
            if self.is_recording:
                filtered, self.zi = signal.sosfilt(self.sos, audio, zi=self.zi)
                
                # Apply Automatic Gain Control (AGC)
                if self.use_agc:
                    filtered = self._apply_agc(filtered)
                
                compressed = np.tanh(filtered * 2.0) * 0.9
                
                # Convert to PCM int16
                pcm_data = (compressed * 32767).astype(np.int16).tobytes()
                
                # Voice Activity Detection
                should_send = True
                if self.use_vad:
                    # WebRTC VAD requires 16kHz/32kHz/48kHz and specific frame sizes
                    # Convert to int16 for VAD processing
                    pcm_int16 = (compressed * 32767).astype(np.int16).tobytes()
                    
                    # WebRTC VAD expects 10/20/30ms frames at 8/16/32/48kHz
                    # We use 20ms at 48kHz (960 samples)
                    try:
                        pcm_int16_vad = pcm_data  # Use already converted data
                        is_speech = self.vad.is_speech(pcm_int16_vad, self.sample_rate)
                        should_send = is_speech
                    except Exception as e:
                        # Fallback to noise gate on VAD error
                        should_send = level_db > self.noise_gate_threshold
                
                elif self.is_recording and self.noise_gate_enabled:
                    # Simple noise gate fallback
                    if level_db > self.noise_gate_threshold:
                        self.gate_open = True
                        self.gate_hold_counter = self.gate_hold_samples
                    elif self.gate_hold_counter > 0:
                        self.gate_hold_counter -= len(compressed)
                        self.gate_open = True
                    else:
                        self.gate_open = False
                    
                    should_send = self.gate_open
                
                # Send audio if gate is open (or noise gate disabled) AND recording is active
                if should_send and self.is_recording and self.callback:
                    # Encode with Opus if enabled
                    if self.use_opus and self.opus_encoder:
                        try:
                            opus_data = self.opus_encoder.encode(pcm_data, OPUS_FRAME_SIZE)
                            self.callback(opus_data)
                        except Exception as e:
                            print(f"❌ Opus encoding failed: {e}")
                            # Fallback to PCM
                            try:
                                self.callback(pcm_data)
                            except Exception as e2:
                                print(f"❌ Callback failed: {e2}")
                    else:
                        # Send RAW PCM
                        try:
                            self.callback(pcm_data)
                        except Exception as e:
                            print(f"❌ Callback failed: {e}")

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

    def _apply_agc(self, audio):
        """Apply Automatic Gain Control to normalize audio levels
        
        Args:
            audio: Input audio samples (float32)
            
        Returns:
            AGC-processed audio samples
        """
        # Calculate current RMS level
        rms = np.sqrt(np.mean(audio**2))
        
        if rms > 0.001:  # Avoid division by zero
            # Calculate required gain to reach target level
            required_gain = self.agc_target_level / rms
            
            # Smooth gain changes
            if required_gain > self.agc_gain:
                # Attack: increase gain quickly for quiet signals
                self.agc_gain += (required_gain - self.agc_gain) * self.agc_attack
            else:
                # Release: decrease gain slowly for loud signals
                self.agc_gain += (required_gain - self.agc_gain) * self.agc_release
            
            # Limit gain to reasonable range (0.1x to 10x)
            self.agc_gain = np.clip(self.agc_gain, 0.1, 10.0)
            
            # Apply gain
            audio = audio * self.agc_gain
        
        return audio
    
    def set_vad_aggressiveness(self, mode):
        """Set WebRTC VAD aggressiveness (0-3)
        
        Args:
            mode: 0 (least aggressive) to 3 (most aggressive)
        """
        if self.use_vad and self.vad:
            try:
                self.vad.set_mode(mode)
                print(f"⚙️ VAD aggressiveness set to {mode}")
            except Exception as e:
                print(f"Failed to set VAD mode: {e}")
    
    def set_agc_target(self, target_level):
        """Set AGC target level (0.0 - 1.0)
        
        Args:
            target_level: Target RMS level (default: 0.3)
        """
        if self.use_agc:
            self.agc_target_level = np.clip(target_level, 0.1, 0.9)
            print(f"⚙️ AGC target level set to {self.agc_target_level}")

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
