"""
Quick test to verify VAD loading priority
"""

print("=== VAD Loading Test ===\n")

# Test 1: Try WebRTC VAD
print("1. Testing WebRTC VAD import...")
try:
    import webrtcvad
    print("   ✅ WebRTC VAD available")
    VAD_TYPE = "WebRTC"
except ImportError as e:
    print(f"   ❌ WebRTC VAD not available: {e}")
    VAD_TYPE = None

# Test 2: Try Python VAD fallback
if VAD_TYPE is None:
    print("\n2. Testing Python VAD fallback...")
    try:
        import python_vad
        webrtcvad = python_vad  # Use module as webrtcvad
        print("   ✅ Python VAD available (fallback)")
        VAD_TYPE = "Python"
    except ImportError as e:
        print(f"   ❌ Python VAD not available: {e}")
        VAD_TYPE = None

# Test 3: Create VAD instance
if VAD_TYPE:
    print(f"\n3. Creating {VAD_TYPE} VAD instance...")
    try:
        vad = webrtcvad.Vad(2)
        print(f"   ✅ {VAD_TYPE} VAD created successfully")
        
        # Test with dummy audio
        import numpy as np
        sample_rate = 48000
        duration = 0.02
        samples = int(sample_rate * duration)
        
        # Test speech
        t = np.linspace(0, duration, samples)
        speech = (np.sin(2 * np.pi * 500 * t) * 10000).astype(np.int16)
        
        result = vad.is_speech(speech.tobytes(), sample_rate)
        print(f"   ✅ VAD test passed: is_speech = {result}")
        
    except Exception as e:
        print(f"   ❌ VAD creation failed: {e}")
else:
    print("\n❌ No VAD available - would fall back to Noise Gate")

print("\n" + "="*40)
print(f"Final VAD Type: {VAD_TYPE if VAD_TYPE else 'Noise Gate'}")
print("="*40)
