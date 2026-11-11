import { PanelSection, PanelSectionRow, staticClasses } from "@decky/ui";
import { definePlugin } from "@decky/api";
import { useEffect, useState } from "react";
import { FaLightbulb } from "react-icons/fa";

import { getState, PluginState } from "./backend";
import { LedPanel } from "./components/LedPanel";

const small = { fontSize: "0.8em", opacity: 0.6 };

function Content() {
  const [state, setState] = useState<PluginState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getState()
      .then(setState)
      .catch((e) => setError(String(e)));
  }, []);

  let body;
  if (error) body = <div>Backend error: {error}</div>;
  else if (!state) body = <div>Loading…</div>;
  else if (!state.device || !state.description || !state.settings)
    body = <div>AOKZOE A1X LED controller not found</div>;

  return (
    <PanelSection title={state?.device?.name ?? "LEDs"}>
      {body ? (
        <PanelSectionRow>{body}</PanelSectionRow>
      ) : (
        <LedPanel description={state!.description!} initial={state!.settings!} />
      )}
      {state && (
        <PanelSectionRow>
          <div style={small}>
            v{state.version}
            {state.device && ` · ${state.device.path}`}
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
