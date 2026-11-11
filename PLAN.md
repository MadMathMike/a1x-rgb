# A1X RGB — Decky Loader plugin plan

A small Decky Loader plugin that controls the LEDs on the
**AOKZOE A1X**. It supports the same lighting modes Handheld Daemon (HHD) offers
for this device, and nothing more. The UI borrows from
[HueSync](https://github.com/honjow/HueSync), with far fewer features.

---

## 1. Scope

**In scope**
- Three modes, the same as HHD's A1X modes (`RGB_MODES_STICKS_AOK` in
  `hhd/src/hhd/device/oxp/base.py`):
  | Mode | Controls |
  |---|---|
  | **Off** | — |
  | **Solid** | Hue (0–360), Saturation (0–100 %), Brightness (0–100 %) |
  | **AOKZOE** (built-in firmware effects) | Style (10 presets), Brightness (Low / Medium / High) |
- Save the settings so the panel shows the last choice. The LEDs are only
  written when the user changes something. The A1X firmware keeps the LED
  state across suspend and reboot (§2.4), so nothing is re-applied on plugin
  load or resume.
- A single global setting. No per-game profiles.

**Out of scope** (HueSync has these; we skip them): per-app profiles, AC-state
profiles, custom keyframe animations, power-LED control, multiple devices,
i18n, auto-updater.

**Device-agnostic where it's cheap:** the backend uses a small `LedDevice`
interface and a mode/capability description that the UI renders from. Only one
implementation is shipped (OneXPlayer/AOKZOE "HID v2"). Another device could be
added later without touching the UI.

---

## 2. Hardware protocol (taken from HHD)

Sources: `hhd/src/hhd/device/oxp/{const.py,base.py,hid_v2.py}`,
`hhd/src/hhd/plugins/rgb/{capabilities.yml,__init__.py}`, `hhd/src/hhd/utils.py`
(local HHD checkout at commit `7111e8e4`).

### 2.1 Device
- In HHD, the A1X uses protocol `hid_dual`. HHD opens two vendor HID devices, but
  **LED control is turned off on the V1 device** (`led_control=(protocol != "hid_dual")`).
  So the LEDs are driven **only through the V2 device**:
  - VID `0x1A2C`, PID `0xB001`, HID usage page `0xFF01`, usage `0x0001`.
- HHD writes through hidapi. hidapi's Linux hidraw backend just calls `write()`
  on `/dev/hidrawN`, so writing the same 64-byte buffer straight to the hidraw
  node is identical. **No hidapi dependency is needed**, which matters because
  Decky's embedded Python can't easily install native packages.
- The device exposes several hidraw interfaces. The right one is found by:
  1. Scanning `/sys/class/hidraw/hidraw*/device/uevent` for
     `HID_ID=0003:00001A2C:0000B001`.
  2. Then reading `.../device/report_descriptor` and picking the node whose
     descriptor declares usage page `0xFF01` (bytes `06 01 FF`) with usage
     `0x0001` (`09 01`).
- **Verified on the A1X (2026-11-11):** two hidraw nodes have ID `1A2C:B001`.
  `hidraw0` is the LED interface (descriptor starts `06 01 ff 09 01 a1 01`).
  `hidraw2` is a mouse interface (`05 01 09 02 …`), which discovery rejects.
  The nodes are `root:root 0600`, so the `root` flag is needed. The start of
  both descriptors is a regression test in `test_hidraw.py`.

### 2.2 Packet format
Every command is exactly **64 bytes**: `[cid, 0xFF, *payload]`, zero-padded.
All LED commands use `cid = 0x07`.

| Command | Payload after `07 FF` |
|---|---|
| Brightness / on-off | `FD, enabled(0/1), 05, level` — level: low `01`, medium `03`, high `04` |
| Solid colour | `FE, (R, G, B) × 20, 00` |
| Firmware effect | `effect_code` |

Firmware effect codes (style → code), from `gen_rgb_mode` in `hid_v2.py`:

| Key | Label | Code |
|---|---|---|
| `aok` | AOK Classic | `0x0E` |
| `monster_woke` | Monster Woke | `0x0D` |
| `flowing` | Flowing Light | `0x03` |
| `sunset` | Sunset Afterglow | `0x0B` |
| `neon` | Colorful Neon | `0x05` |
| `dreamy` | Dreamy | `0x07` |
| `cyberpunk` | Cyberpunk | `0x09` |
| `colorful` | Colorful | `0x0C` |
| `aurora` | Aurora | `0x01` |
| `sun` | Warm Sun | `0x08` |

### 2.3 Command sequences per mode (same behaviour as HHD)
| Mode | Sequence |
|---|---|
| Off | `brightness(enabled=0, level=high)` |
| Solid | `brightness(1, high)` → `solid(r, g, b)`, where `r, g, b = hsb_to_rgb(h, s, v)` (port of HHD's `utils.hsb_to_rgb`; the brightness slider scales the colour) |
| AOKZOE | `brightness(1, level)` → `effect(code)` |

- Leave **≥ 50 ms** between writes (`WRITE_DELAY` in HHD), and send brightness before colour/effect.
- HHD waits 4 s after opening the device before its first write (`INIT_DELAY`).
  We don't need that because we never write at startup or resume.
- Responses on the device (`cid 0xB8`) can be ignored. We only write, never read.

### 2.4 Verified on the A1X (2026-11-11, hand-written packets)
- Solid red/blue, AOK Classic at medium, Aurora at low, and Off all worked.
  The brightness level was visibly different between low and medium.
- Rumble still worked after LED writes (tested from Steam).
- **The LED state survives suspend/resume, restart, and shutdown + power on.**
  The firmware keeps it, so the plugin doesn't re-apply anything.

---

## 3. Architecture

```
a1x-rgb/
├── plugin.json            # name, author, flags: ["root"], api_version 1
├── package.json           # pnpm; @decky/ui, @decky/api, @decky/rollup, react-icons
├── rollup.config.js       # export default deckyPlugin()
├── tsconfig.json
├── main.py                # Decky entry: class Plugin (thin)
├── py_modules/
│   └── a1x_rgb/
│       ├── __init__.py
│       ├── color.py       # hsb_to_rgb (ported from HHD)
│       ├── modes.py       # mode/capability description helpers + validation
│       ├── settings.py    # load/save settings.json (atomic)
│       ├── controller.py  # Controller (state, set_settings) + latest-wins Applier
│       ├── device.py      # LedDevice ABC, OxpHidV2Device + its modes, detect_device()
│       ├── hidraw.py      # generic sysfs hidraw discovery (VID/PID + usage)
│       └── oxp_hid_v2.py  # packet builders, mode sequences, find_device()
├── src/
│   ├── index.tsx          # definePlugin
│   ├── backend.ts         # typed callable() wrappers
│   ├── color.ts           # hsbToRgb for the swatch (same as color.py)
│   └── components/
│       └── LedPanel.tsx   # mode dropdown + dynamic controls
├── tests/
│   ├── _util.py           # loads reference functions from a local HHD checkout
│   ├── test_packets.py    # byte-exact packet tests
│   ├── test_color.py
│   └── test_hidraw.py     # discovery against a fake sysfs tree
└── README.md
```

Start from the official `SteamDeckHomebrew/decky-plugin-template` so the build,
`decky.pyi` stubs and the CLI packaging match the current Decky API.

### 3.1 Backend (Python, runs as root)
- **`plugin.json` `flags: ["root"]`**. HueSync does this too. Hidraw nodes are
  `root:root 0600` unless a udev rule says otherwise, and running as root saves
  us from installing udev rules.
- **Settings:** a JSON file in `decky.DECKY_PLUGIN_SETTINGS_DIR/settings.json`:
  ```json
  { "mode": "solid", "hue": 30, "saturation": 100, "brightness": 50,
    "style": "aok", "level": "medium" }
  ```
  The defaults match HHD's (`capabilities.yml`). Keep all fields even when they
  don't apply to the current mode, so switching modes keeps the user's values.
- **`LedDevice` interface** (`device.py`):
  ```python
  class LedDevice(ABC):
      name: str
      def modes(self) -> dict: ...         # capability description for the UI
      def apply(self, settings: dict): ...  # build + write command sequence
  def detect_device() -> LedDevice | None   # returns OxpHidV2Device if found
  ```
  `OxpHidV2Device` opens the node with `os.open(path, os.O_WRONLY)` for each
  apply and closes it afterwards. It doesn't hold the fd, so it can't go stale
  across suspend.
- **Write serialisation:** one `asyncio.Lock` plus a "latest wins" coalescer.
  If a new request arrives while a sequence is being written, only the newest
  settings get applied next. This stops slider drags from flooding the MCU
  (HHD notes the colour slider is "too fast" for initialization).
- **Callable methods** (exposed to the frontend):
  | Method | Purpose |
  |---|---|
  | `get_state()` | `{version, python, device: {name, path}\|null, description, settings}`. Looks for the device again if it wasn't found yet |
  | `set_settings(partial)` | merge with saved → validate (strict) → save → apply (coalesced). Returns `{ok, error, settings}` |
- **Lifecycle:** `_main()` loads settings and detects the device. It doesn't
  write to the LEDs. `_unload()` does nothing (the LEDs keep their last state).
- The saved settings are what the panel shows. If something else changes the
  LEDs, the panel can be out of date until the user changes a setting. That's
  accepted (see §4).

### 3.2 Frontend (TypeScript / React)
- `definePlugin` with a `PanelSection` titled "A1X RGB" and a lightbulb icon.
- **No ring imagery.** The A1X's LEDs aren't joystick rings, so the UI uses no
  ring-shaped icons, graphics or previews. The only visual is a plain flat
  colour swatch (rectangle) for Solid mode.
- Controls (from `@decky/ui`), built from `description` from `get_state()`.
  Slider controls become `SliderField`s and choice controls become `DropdownItem`s:
  - `DropdownItem` **Mode**: Off / Solid / AOKZOE
  - Solid → `SliderField` Hue (step 5), Saturation (step 10), Brightness (step 10),
    plus a colour-swatch preview (shown for any mode with hue/saturation/brightness)
  - AOKZOE → `DropdownItem` Style (10 presets), `DropdownItem` Brightness (Low/Medium/High)
- Every change updates the panel straight away. Only the changed values are
  sent to `set_settings`:
  - Dropdowns send immediately.
  - Sliders send **at most every 150 ms** while dragging, and the final value
    is always sent.
  - Anything still unsent is sent when the panel closes.
  - Errors from the backend are shown under the controls.
- If `device` is null: show "AOKZOE A1X LED controller not found" and hide the controls.
- No suspend/resume hooks (unlike HueSync), because the firmware keeps the LED state.

---

## 4. Other software on the device

- **Handheld Daemon:** won't be installed on the target device. It's used only
  as the reference for the protocol, so the plugin doesn't detect or handle HHD.
- **InputPlumber:** `inputplumber.service` is running on the target device.
  Possible conflicts over the LEDs are **ignored for now**. The plugin doesn't
  detect or work around it.

---

## 5. Testing

**Unit (runs on any machine, no hardware):**
- `test_packets.py`: for each mode/style/level, check that the generated byte
  sequences are exactly what HHD's `gen_brightness`, `gen_rgb_solid` and
  `gen_rgb_mode` produce. Expected bytes are hard-coded from HHD. Optionally,
  cross-check by importing `hhd.device.oxp.hid_v2` when it's on `PYTHONPATH`.
- `test_color.py`: `hsb_to_rgb` matches HHD for a grid of inputs.
- Device discovery: point the scanner at a fake `/sys/class/hidraw` tree with
  sample `uevent`/`report_descriptor` files.

**On the A1X** (this dev machine is a desktop, so final checks have to run on the handheld):
Already done with hand-written packets (§2.1, §2.4): finding the node, solid
colours, two effects, off, brightness levels, rumble, suspend and reboot.
With the plugin installed:
1. The panel shows the detected device (`/dev/hidraw0`).
2. Go through each mode, each of the 10 styles, and each brightness level.
3. Drag the hue slider fast: the LEDs should keep up without freezing.
4. Suspend/resume and reboot: the LEDs keep their state, and the panel still
   shows the saved settings.
5. Rumble still works after changing LEDs from the panel.

---

## 6. Milestones

1. ✅ **Scaffold:** clone the Decky template, rename, set `flags: ["root"]`, build an empty panel.
2. ✅ **Protocol module + unit tests:** `color.py`, `oxp_hid_v2.py` packet builders, discovery.
3. ✅ **Backend:** settings persistence, `LedDevice`, coalesced apply, callables.
4. ✅ **Frontend:** mode dropdown, dynamic controls, throttled sends, colour swatch, not-found state.
5. **On-device testing** (checklist in §5), then write the README with install steps.

(The old "lifecycle: resume hook" milestone was dropped because the firmware
keeps the LED state; see §2.4.)

---

## 7. Risks / open questions

| Risk | Mitigation |
|---|---|
| Rumble stops working after LED writes (HHD comment in `hid_v2.py`) | Passed with hand-written packets. Check again with the plugin. Only write on real user changes. |
| The firmware keeps LED state across reboot, so it probably saves it to flash. Constant slider drags could mean many writes | Debounce in the UI plus "latest wins" in the backend. If needed, write only when the slider is released. |
| InputPlumber also touches the LEDs | Ignored for now (§4). |
| Other AOKZOE firmware revisions behave differently | Out of scope (single device). The protocol is isolated in one module. |
| Decky API changes | Pin `@decky/ui` / `@decky/api` versions from the template. |
