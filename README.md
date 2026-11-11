# A1X RGB

A [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin for
controlling the LEDs on the AOKZOE A1X. See [PLAN.md](PLAN.md) for the design.

Modes:
- **Off**
- **Solid:** hue, saturation and brightness
- **AOKZOE:** 10 firmware effects, with Low, Medium and High brightness

Your choice is saved, and the LEDs keep it through suspend and reboot.

## Install

1. **Download the zip.** Open the
   [latest release](https://github.com/MadMathMike/a1x-rgb/releases/latest)
   and download `a1x-rgb.zip` under **Assets**. (All versions are on the
   [Releases page](https://github.com/MadMathMike/a1x-rgb/releases).)
   Leave it zipped.
2. **Copy it to the handheld,** for example into `~/Downloads`. You can skip
   this step if you downloaded it on the handheld in Desktop Mode.
3. **Turn on Decky's developer mode** (only needed once). In Game Mode, open the
   Quick Access menu, go to Decky → ⚙ Settings → **General**,
   and turn on **Developer mode**.
4. **Install the zip.** In Decky's settings, open the new **Developer** section,
   choose **Install Plugin from ZIP File**, browse to `a1x-rgb.zip` and confirm.
5. **Open the plugin.** It's listed as **A1X RGB** (lightbulb icon) in the
   Decky menu.

To update, install the newer zip the same way. It replaces the old version.
Your settings are kept, because Decky stores them outside the plugin folder
(`~/homebrew/settings/`).

The plugin runs as root because the LED controller (`/dev/hidraw*`) is only
accessible to root.

### Troubleshooting

- **"AOKZOE A1X LED controller not found":** the LED interface (USB
  `1A2C:B001`, HID usage page `0xFF01`) wasn't detected.
- **Logs:** the plugin's log is under `~/homebrew/logs/` on the handheld.

## Releases (for maintainers)

[`.github/workflows/build.yml`](.github/workflows/build.yml) builds and tests
the plugin on every push and pull request. The zip is attached to each run
as the `a1x-rgb` artifact.

To publish a release:

1. Bump the version in **both** `package.json` and
   `py_modules/a1x_rgb/__init__.py` (a test checks they match), then commit.
2. Tag and push:
   ```sh
   git tag v0.4.0
   git push origin main v0.4.0
   ```
   The workflow checks that the tag matches the version, then creates a
   GitHub Release named after the tag with `a1x-rgb.zip` attached.

## Package locally

```sh
./scripts/package.sh
```

This builds the frontend, runs the tests and writes `out/a1x-rgb.zip`. It
uses a local `pnpm` if there is one, otherwise a throwaway Node container
(podman or docker).

## Build

Requires Node.js 22+ and pnpm (the version is pinned in `package.json`;
`corepack enable` picks it up). Without a local Node install, use a container:

```sh
podman run --rm -v "$PWD":/src:Z -w /src docker.io/library/node:22-alpine \
  sh -c 'corepack enable && pnpm i --frozen-lockfile && pnpm build'
```

The frontend bundle is written to `dist/index.js`.

## Test

```sh
python3 -m unittest discover -s tests -v
```

If a Handheld Daemon checkout is at `../hhd` (or `HHD_SRC` points at its
`src/hhd` directory), the tests also compare our packets and colours
byte-for-byte against HHD's own code. Otherwise those tests are skipped.

## Layout

| Path | Purpose |
|---|---|
| `plugin.json` | Decky metadata (`root` flag: needed for hidraw access) |
| `main.py` | Backend entry point (`Plugin` class) |
| `py_modules/a1x_rgb/` | Backend package (protocol, device, settings) |
| `src/` | Frontend (React / `@decky/ui`) |
| `tests/` | Python unit tests |
| `scripts/package.sh` | Build + test + zip |
| `.github/workflows/build.yml` | CI build and GitHub Releases |
