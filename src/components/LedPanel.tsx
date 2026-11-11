import { PanelSectionRow, SliderField } from "@decky/ui";
import { useCallback, useEffect, useRef, useState } from "react";

import { Control, Description, Settings, setSettings } from "../backend";
import { OptionButtons } from "./OptionButtons";

// Choice controls with up to this many options become a notched slider;
// larger ones become a button grid with GRID_COLUMNS columns.
const MAX_NOTCHES = 4;
const GRID_COLUMNS = 2;

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

  return (
    <>
      <PanelSectionRow>
        <OptionButtons
          label="Mode"
          options={description.modes}
          selected={mode.key}
          columns={description.modes.length}
          onSelect={(key) => update({ mode: key }, true)}
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
  if (control.options.length <= MAX_NOTCHES) {
    // Few options: a notched slider, e.g. Low / Medium / High.
    const index = Math.max(
      0,
      control.options.findIndex((o) => o.key === value),
    );
    return (
      <SliderField
        label={control.label}
        value={index}
        min={0}
        max={control.options.length - 1}
        step={1}
        notchCount={control.options.length}
        notchLabels={control.options.map((o, i) => ({ notchIndex: i, label: o.label, value: i }))}
        notchTicksVisible
        onChange={(i) => onChange(control.options[i].key, false)}
      />
    );
  }
  // Many options: an inline grid of buttons.
  return (
    <OptionButtons
      label={control.label}
      options={control.options}
      selected={String(value)}
      columns={GRID_COLUMNS}
      onSelect={(key) => onChange(key, true)}
    />
  );
}
