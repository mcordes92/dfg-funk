import struct

# Packet types
PACKET_TYPE_AUDIO = 0
PACKET_TYPE_PING = 1
PACKET_TYPE_PONG = 2
PACKET_TYPE_AUTH = 3
PACKET_TYPE_AUTH_OK = 4
PACKET_TYPE_AUTH_FAIL = 5


def build_header(channel_id, user_id, sequence_number, packet_type=PACKET_TYPE_AUDIO):
    return struct.pack('!BBBH', packet_type, channel_id, user_id, sequence_number)


def parse_header(data):
    if len(data) < 5:
        return None, None, None, None, None
    packet_type, channel_id, user_id, sequence_number = struct.unpack('!BBBH', data[:5])
    payload = data[5:]
    return packet_type, channel_id, user_id, sequence_number, payload


def build_packet(channel_id, user_id, sequence_number, audio_data, packet_type=PACKET_TYPE_AUDIO):
    header = build_header(channel_id, user_id, sequence_number, packet_type)
    return header + audio_data


def build_ping_packet(channel_id, user_id):
    return build_packet(channel_id, user_id, 0, b'', PACKET_TYPE_PING)


def build_pong_packet(channel_id, user_id):
    return build_packet(channel_id, user_id, 0, b'', PACKET_TYPE_PONG)


def build_auth_packet(channel_id, user_id, funk_key):
    """Build authentication packet with funk key"""
    funk_key_bytes = funk_key.encode('utf-8')
    return build_packet(channel_id, user_id, 0, funk_key_bytes, PACKET_TYPE_AUTH)


def build_auth_ok_packet(channel_id, user_id):
    """Build authentication success packet"""
    return build_packet(channel_id, user_id, 0, b'', PACKET_TYPE_AUTH_OK)


def build_auth_fail_packet(channel_id, user_id, reason=b''):
    """Build authentication failure packet"""
    return build_packet(channel_id, user_id, 0, reason, PACKET_TYPE_AUTH_FAIL)
