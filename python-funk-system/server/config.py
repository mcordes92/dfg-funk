SERVER_HOST = '0.0.0.0'
SERVER_PORT = 50000
MAX_PACKET_SIZE = 8192  # Increased for Opus codec support (was 4096)
TIMEOUT_SECONDS = 30

# Jitter Buffer Settings
JITTER_BUFFER_SIZE = 5  # Number of packets to buffer (~100ms at 20ms/packet)
JITTER_MAX_AGE_MS = 200  # Maximum packet age before forced release

# Audio Codec Settings
AUDIO_CODEC = 'opus'  # 'opus' or 'pcm' (RAW)
OPUS_BITRATE = 24000  # 24 kbit/s (good quality for voice)
OPUS_FRAME_SIZE = 960  # 20ms at 48kHz sample rate
OPUS_SAMPLE_RATE = 48000
OPUS_CHANNELS = 1  # Mono
