import { callable } from "@decky/api";

export interface PluginState {
  version: string;
  device: string | null;
}

export const getState = callable<[], PluginState>("get_state");
