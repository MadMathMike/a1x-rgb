import { DropdownItem, PanelSectionRow, SliderField } from "@decky/ui";
import { useCallback, useEffect, useRef, useState } from "react";

import { Control, Description, Settings, setSettings } from "../backend";
import { hsbToRgb } from "../color";

// Slider changes are sent at most this often while dragging; the final value
// is always sent. The backend also drops superseded writes.
const SEND_INTERVAL_MS = 150;

interface Props {
  description: Description;
  initial: Settings;
}

export function LedPanel({ description, initial }: Props) {
  const [values, setValues] = useState<Settings>(initial);
  const [error, setError] = useState<string | null>(null);

  const pending = useRef<Partial<Settings>>({});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const seq = useRef(0);

  const flush = useCallback(async () => {
    timer.current = null;
    const changes = pending.current;
    pending.current = {};
    if (Object.keys(changes).length === 0) return;

    const mine = ++seq.current;
    try {
      const r = await setSettings(changes);
      if (mine !== seq.current) return; // a newer send owns the UI state
      setError(r.ok ? null : r.error);
      // Adopt the backend's normalized values unless the user has moved on.
      if (r.settings && timer.current === null) setValues(r.settings);
    } catch (e) {
      if (mine === seq.current) setError(String(e));
    }
  }, []);

  const update = (changes: Partial<Settings>, immediate = false) => {
    setValues((v) => ({ ...v, ...changes }) as Settings);
    pending.current = { ...pending.current, ...changes };
    if (immediate) {
      if (timer.current !== null) clearTimeout(timer.current);
      void flush();
    } else if (timer.current === null) {
      timer.current = setTimeout(flush, SEND_INTERVAL_MS);
    }
  };

  // Send anything still pending when the panel closes.
  useEffect(
    () => () => {
      if (timer.current !== null) {
        clearTimeout(timer.current);
        void flush();
      }
    },
    [flush],
  );

  const mode = description.modes.find((m) => m.key === values.mode) ?? description.modes[0];
  const hasColor = ["hue", "saturation", "brightness"].every((k) => mode.controls.includes(k));

  return (
    <>
      <PanelSectionRow>
        <DropdownItem
          label="Mode"
          rgOptions={description.modes.map((m) => ({ data: m.key, label: m.label }))}
          selectedOption={mode.key}
          onChange={(o) => update({ mode: o.data }, true)}
        />
      </PanelSectionRow>

      {mode.controls.map((key) => (
        <PanelSectionRow key={key}>
          <ControlField
            control={description.controls[key]}
            value={values[key]}
            onChange={(v, immediate) => update({ [key]: v }, immediate)}
          />
        </PanelSectionRow>
      ))}

      {hasColor && (
        <PanelSectionRow>
          <ColorSwatch
            rgb={hsbToRgb(
              Number(values.hue),
              Number(values.saturation),
              Number(values.brightness),
            )}
          />
        </PanelSectionRow>
      )}

      {error && (
        <PanelSectionRow>
          <div style={{ color: "#ff6b6b", fontSize: "0.85em" }}>{error}</div>
        </PanelSectionRow>
      )}
    </>
  );
}

function ControlField({
  control,
  value,
  onChange,
}: {
  control: Control;
  value: string | number;
  onChange: (value: string | number, immediate: boolean) => void;
}) {
  if (control.type === "slider") {
    return (
      <SliderField
        label={control.label}
        value={Number(value)}
        min={control.min}
        max={control.max}
        step={control.step}
        showValue
        valueSuffix={control.unit}
        resetValue={control.default}
        onChange={(v) => onChange(v, false)}
      />
    );
  }
  return (
    <DropdownItem
      label={control.label}
      rgOptions={control.options.map((o) => ({ data: o.key, label: o.label }))}
      selectedOption={value}
      onChange={(o) => onChange(o.data, true)}
    />
  );
}

// A plain flat rectangle: the A1X's LEDs aren't rings, so no ring imagery.
function ColorSwatch({ rgb: [r, g, b] }: { rgb: [number, number, number] }) {
  return (
    <div
      style={{
        height: "24px",
        borderRadius: "4px",
        background: `rgb(${r}, ${g}, ${b})`,
        border: "1px solid rgba(255, 255, 255, 0.2)",
      }}
    />
  );
}
