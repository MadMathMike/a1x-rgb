import { DialogButton, Field, Focusable } from "@decky/ui";

export interface Option {
  key: string;
  label: string;
}

interface Props {
  label: string;
  options: Option[];
  selected: string;
  columns: number;
  onSelect: (key: string) => void;
}

// Steam's accent blue, used to mark the selected option.
const SELECTED = { backgroundColor: "#1a9fff", color: "#ffffff" };

/**
 * Inline single-choice picker: a row (or grid) of buttons with the selected
 * one highlighted. Unlike DropdownItem it doesn't open a context menu, so the
 * Quick Access panel stays visible. D-pad left/right moves within a row,
 * up/down between rows.
 */
export function OptionButtons({ label, options, selected, columns, onSelect }: Props) {
  const rows: Option[][] = [];
  for (let i = 0; i < options.length; i += columns) {
    rows.push(options.slice(i, i + columns));
  }

  return (
    <Field label={label} childrenLayout="below" childrenContainerWidth="max">
      <div style={{ display: "flex", flexDirection: "column", gap: "6px", width: "100%" }}>
        {rows.map((row, r) => (
          <Focusable
            key={r}
            flow-children="horizontal"
            style={{ display: "flex", gap: "6px" }}
          >
            {row.map((o) => (
              <DialogButton
                key={o.key}
                onClick={() => onSelect(o.key)}
                style={{
                  flex: `0 0 calc((100% - ${(columns - 1) * 6}px) / ${columns})`,
                  minWidth: 0,
                  padding: "6px 4px",
                  fontSize: "0.85em",
                  lineHeight: "1.2",
                  whiteSpace: "normal",
                  ...(o.key === selected ? SELECTED : {}),
                }}
              >
                {o.label}
              </DialogButton>
            ))}
          </Focusable>
        ))}
      </div>
    </Field>
  );
}
