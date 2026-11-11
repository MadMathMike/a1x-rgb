// Same conversion as py_modules/a1x_rgb/color.py (ported from HHD), so the
// preview swatch shows exactly the RGB values sent to the LEDs.
export function hsbToRgb(h: number, s: number, v: number): [number, number, number] {
  if (h >= 360) h = 359;
  s = s / 100;
  v = v / 100;

  const c = v * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = v - c;

  let rgb: [number, number, number];
  if (h < 60) rgb = [c, x, 0];
  else if (h < 120) rgb = [x, c, 0];
  else if (h < 180) rgb = [0, c, x];
  else if (h < 240) rgb = [0, x, c];
  else if (h < 300) rgb = [x, 0, c];
  else rgb = [c, 0, x];

  return rgb.map((ch) => Math.trunc((ch + m) * 255)) as [number, number, number];
}
