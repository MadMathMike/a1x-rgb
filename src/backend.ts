import { callable } from "@decky/api";

export interface SliderControl {
  type: "slider";
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  default: number;
}

export interface ChoiceControl {
  type: "choice";
  label: string;
  options: { key: string; label: string }[];
  default: string;
}

export type Control = SliderControl | ChoiceControl;

export interface ModeInfo {
  key: string;
  label: string;
  controls: string[];
}

export interface Description {
  default_mode: string;
  modes: ModeInfo[];
  controls: Record<string, Control>;
}

export type Settings = { mode: string } & Record<string, string | number>;

export interface PluginState {
  version: string;
  python: string;
  device: { name: string; path: string } | null;
  description: Description | null;
  settings: Settings | null;
}

export interface SetResult {
  ok: boolean;
  error: string | null;
  settings: Settings | null;
}

export const getState = callable<[], PluginState>("get_state");
export const setSettings = callable<[settings: Partial<Settings>], SetResult>(
  "set_settings",
);
