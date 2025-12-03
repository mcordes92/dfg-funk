"""
Test tone generator for channel testing
"""
import numpy as np
import struct
from config import OPUS_SAMPLE_RATE, OPUS_FRAME_SIZE

def generate_test_tone(frequency=1000, duration=1.5, sample_rate=OPUS_SAMPLE_RATE, amplitude=0.2):
    """
    Generate a sine wave test tone
    
    Args:
        frequency: Tone frequency in Hz (default 1000Hz)
        duration: Duration in seconds (default 1.5s)
        sample_rate: Sample rate in Hz (default from config)
        amplitude: Amplitude 0.0-1.0 (default 0.2 for quieter tone)
    
    Returns:
        List of PCM frames (each frame is OPUS_FRAME_SIZE samples)
    """
    # Calculate total samples
    total_samples = int(sample_rate * duration)
    
    # Generate time array
    t = np.linspace(0, duration, total_samples, False)
    
    # Generate sine wave
    tone = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # Apply fade in/out to avoid clicks
    fade_samples = int(0.01 * sample_rate)  # 10ms fade
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    
    tone[:fade_samples] *= fade_in
    tone[-fade_samples:] *= fade_out
    
    # Convert to 16-bit PCM
    pcm_data = (tone * 32767).astype(np.int16)
    
    # Split into frames
    frames = []
    frame_size = OPUS_FRAME_SIZE
    
    for i in range(0, len(pcm_data), frame_size):
        frame = pcm_data[i:i + frame_size]
        
        # Pad last frame if necessary
        if len(frame) < frame_size:
            frame = np.pad(frame, (0, frame_size - len(frame)), 'constant')
        
        # Convert to bytes
        frame_bytes = frame.tobytes()
        frames.append(frame_bytes)
    
    return frames


def get_test_tone_info():
    """Get information about the test tone"""
    return {
        "frequency": 1000,
        "duration": 1.5,
        "amplitude": 0.2,
        "description": "1kHz sine wave, 1.5 seconds, 20% volume"
    }
