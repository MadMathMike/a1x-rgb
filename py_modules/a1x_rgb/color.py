"""Colour conversion, ported from Handheld Daemon (hhd/src/hhd/utils.py).

Kept behaviourally identical to HHD so a given hue/saturation/brightness
produces exactly the same RGB bytes on the LEDs.
"""


def hsb_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Convert hue (0-360), saturation (0-100) and brightness (0-100) to RGB.

    Each channel is 0-255 (truncated, not rounded, as HHD does).
    """
    if h >= 360:
        h = 359
    s = s / 100
    v = v / 100

    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c

    if h < 60:
        rgb = (c, x, 0)
    elif h < 120:
        rgb = (x, c, 0)
    elif h < 180:
        rgb = (0, c, x)
    elif h < 240:
        rgb = (0, x, c)
    elif h < 300:
        rgb = (x, 0, c)
    else:
        rgb = (c, 0, x)

    r, g, b = (int((ch + m) * 255) for ch in rgb)
    return r, g, b
