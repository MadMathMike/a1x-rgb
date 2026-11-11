# A1X RGB

A [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin for
controlling the LEDs on the AOKZOE A1X. See [PLAN.md](PLAN.md) for the design.

**Status:** feature-complete (milestone 4). Modes: Off, Solid (hue,
saturation, brightness) and AOKZOE (10 firmware effects, 3 brightness
levels). On-device testing is next.

## Package

```sh
./scripts/package.sh
```

This builds the frontend, runs the tests and writes `out/a1x-rgb.zip`. Install
it on the handheld with Decky → Settings → Developer → *Install Plugin from
ZIP File*. The script uses a local `pnpm` if there is one, otherwise a
throwaway Node container (podman or docker).

## Build

Requires Node.js 22+ and pnpm. Without a local Node install, use a container:

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
