SERVER_IP = 'srv01.dus.cordesm.de'
SERVER_PORT = 5000
SAMPLE_RATE = 48000
FRAME_SIZE_MS = 20
CHANNEL_ID = 41
USER_ID = 1
HOTKEY_PRIMARY = 'f7'
HOTKEY_SECONDARY = 'f8'
JITTER_BUFFER_SIZE = 3

# Audio Codec Settings
AUDIO_CODEC = 'opus'  # 'opus' or 'pcm' (opus.dll is bundled in EXE)
OPUS_BITRATE = 24000  # 24 kbit/s (good quality for voice)
OPUS_FRAME_SIZE = 960  # 20ms at 48kHz sample rate
