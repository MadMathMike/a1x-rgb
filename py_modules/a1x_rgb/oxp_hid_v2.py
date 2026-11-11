"""OneXPlayer / AOKZOE "HID v2" LED protocol.

Ported from Handheld Daemon (hhd/src/hhd/device/oxp/hid_v2.py). On the
AOKZOE A1X, HHD drives the LEDs only through this interface.

Packets are pure byte strings; writing them to the device (with WRITE_DELAY
between packets) is handled by the device layer.
"""

from typing import Literal

from .hidraw import find_hidraw

VID = 0x1A2C
PID = 0xB001
USAGE_PAGE = 0xFF01
USAGE = 0x0001

PACKET_SIZE = 64
LED_CID = 0x07

# Timing used by HHD.
WRITE_DELAY = 0.05  # seconds between packets
INIT_DELAY = 4.0  # seconds to wait after the device appears

Level = Literal["low", "medium", "high"]

LEVELS: dict[str, int] = {
    "low": 0x01,
    "medium": 0x03,
    "high": 0x04,
}

# Firmware effects HHD offers for AOKZOE devices: key -> (label, code).
# Order matches HHD's capabilities.yml, with AOK Classic first as the default.
STYLES: dict[str, tuple[str, int]] = {
    "aok": ("AOK Classic", 0x0E),
    "monster_woke": ("Monster Woke", 0x0D),
    "flowing": ("Flowing Light", 0x03),
    "sunset": ("Sunset Afterglow", 0x0B),
    "neon": ("Colorful Neon", 0x05),
    "dreamy": ("Dreamy", 0x07),
    "cyberpunk": ("Cyberpunk", 0x09),
    "colorful": ("Colorful", 0x0C),
    "aurora": ("Aurora", 0x01),
    "sun": ("Warm Sun", 0x08),
}


# --- Packet builders (byte-identical to HHD's gen_* functions) ---------------


def gen_cmd(cid: int, payload: bytes | list[int]) -> bytes:
    """Build a 64-byte command: [cid, 0xFF, *payload], zero padded."""
    base = bytes([cid, 0xFF, *payload])
    if len(base) > PACKET_SIZE:
        raise ValueError(f"payload too long: {len(base)} > {PACKET_SIZE}")
    return base + bytes(PACKET_SIZE - len(base))


def gen_brightness(enabled: bool, level: Level) -> bytes:
    """Turn the LEDs on/off and set the firmware brightness level."""
    if level not in LEVELS:
        raise ValueError(f"unknown brightness level: {level!r}")
    return gen_cmd(LED_CID, [0xFD, int(bool(enabled)), 0x05, LEVELS[level]])


def gen_solid(r: int, g: int, b: int) -> bytes:
    """Set all LEDs to one colour (20 RGB triplets)."""
    for ch in (r, g, b):
        if not 0 <= ch <= 255:
            raise ValueError(f"colour channel out of range: {ch}")
    return gen_cmd(LED_CID, [0xFE] + 20 * [r, g, b] + [0x00])


def gen_effect(style: str) -> bytes:
    """Start one of the firmware's built-in effects."""
    if style not in STYLES:
        raise ValueError(f"unknown style: {style!r}")
    return gen_cmd(LED_CID, [STYLES[style][1]])


# --- Command sequences per mode (same order as HHD) --------------------------


def sequence_off() -> list[bytes]:
    return [gen_brightness(False, "high")]


def sequence_solid(r: int, g: int, b: int) -> list[bytes]:
    return [gen_brightness(True, "high"), gen_solid(r, g, b)]


def sequence_effect(style: str, level: Level) -> list[bytes]:
    return [gen_brightness(True, level), gen_effect(style)]


# --- Discovery ----------------------------------------------------------------


def find_device(**kwargs) -> str | None:
    """Return the /dev/hidraw* path of the LED interface, or None."""
    paths = find_hidraw(VID, PID, USAGE_PAGE, USAGE, **kwargs)
    return paths[0] if paths else None
