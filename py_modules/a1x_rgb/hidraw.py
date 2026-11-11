"""Find /dev/hidraw* nodes by USB VID/PID and top-level HID usage.

Uses only sysfs, so it needs no native libraries (hidapi etc.).
"""

from __future__ import annotations

import os
import re
from typing import Iterator

SYSFS_HIDRAW = "/sys/class/hidraw"

_HID_ID = re.compile(r"^HID_ID=([0-9A-Fa-f]+):([0-9A-Fa-f]+):([0-9A-Fa-f]+)$", re.M)


def parse_hid_id(uevent: str) -> tuple[int, int, int] | None:
    """Return (bus, vid, pid) from a hidraw device uevent file's contents."""
    m = _HID_ID.search(uevent)
    if not m:
        return None
    return int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)


def _items(desc: bytes) -> Iterator[tuple[int, int, int]]:
    """Yield (type, tag, value) for each short item in a report descriptor."""
    i = 0
    while i < len(desc):
        prefix = desc[i]
        if prefix == 0xFE:  # long item: FE, size, tag, data...
            if i + 1 >= len(desc):
                return
            i += 3 + desc[i + 1]
            continue
        size = (0, 1, 2, 4)[prefix & 0x03]
        data = desc[i + 1 : i + 1 + size]
        if len(data) < size:
            return
        yield (prefix >> 2) & 0x03, prefix >> 4, int.from_bytes(data, "little")
        i += 1 + size


def top_level_usages(desc: bytes) -> list[tuple[int, int]]:
    """Return (usage_page, usage) for every top-level collection."""
    out = []
    page = 0
    usage = None
    depth = 0
    for typ, tag, val in _items(desc):
        if typ == 1 and tag == 0x0:  # Global: Usage Page
            page = val
        elif typ == 2 and tag == 0x0:  # Local: Usage
            usage = val
        elif typ == 0 and tag == 0xA:  # Main: Collection
            if depth == 0 and usage is not None:
                # A 4-byte usage carries its own page in the high word.
                if usage > 0xFFFF:
                    out.append((usage >> 16, usage & 0xFFFF))
                else:
                    out.append((page, usage))
            depth += 1
            usage = None
        elif typ == 0 and tag == 0xC:  # Main: End Collection
            depth = max(0, depth - 1)
            usage = None
        elif typ == 0:  # other Main items clear locals
            usage = None
    return out


def _read(path: str, mode: str = "r"):
    with open(path, mode) as f:
        return f.read()


def find_hidraw(
    vid: int,
    pid: int,
    usage_page: int | None = None,
    usage: int | None = None,
    sysfs_root: str = SYSFS_HIDRAW,
    dev_root: str = "/dev",
) -> list[str]:
    """Return sorted /dev paths of hidraw nodes matching VID/PID (and usage)."""
    try:
        names = os.listdir(sysfs_root)
    except OSError:
        return []

    found = []
    for name in sorted(names):
        devdir = os.path.join(sysfs_root, name, "device")
        try:
            ids = parse_hid_id(_read(os.path.join(devdir, "uevent")))
        except OSError:
            continue
        if not ids or ids[1] != vid or ids[2] != pid:
            continue

        if usage_page is not None or usage is not None:
            try:
                desc = _read(os.path.join(devdir, "report_descriptor"), "rb")
            except OSError:
                continue
            if not any(
                (usage_page is None or p == usage_page)
                and (usage is None or u == usage)
                for p, u in top_level_usages(desc)
            ):
                continue

        found.append(os.path.join(dev_root, name))
    return found
