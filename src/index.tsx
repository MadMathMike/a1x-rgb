import { PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";
import { definePlugin } from "@decky/api";
import { useEffect, useState } from "react";
import { FaLightbulb } from "react-icons/fa";

import { getState, PluginState } from "./backend";

function Content() {
  const [state, setState] = useState<PluginState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getState()
      .then(setState)
      .catch((e) => setError(String(e)));
  }, []);

  let status: string;
  if (error) status = `Backend error: ${error}`;
  else if (!state) status = "Loading…";
  else if (!state.device) status = "AOKZOE A1X LED controller not found";
  else status = `Device: ${state.device}`;

  return (
    <PanelSection title="LEDs">
      <PanelSectionRow>
        <div>{status}</div>
      </PanelSectionRow>
      {state && (
        <PanelSectionRow>
          <div style={{ fontSize: "0.8em", opacity: 0.6 }}>
            v{state.version}
          </div>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}

export default definePlugin(() => ({
  name: "A1X RGB",
  titleView: <div className={staticClasses.Title}>A1X RGB</div>,
  content: <Content />,
  icon: <FaLightbulb />,
  onDismount() {},
}));
