import { GLYPH } from "../lib/glyphs.ts";

// Scroll glyph while closed, a cross while open (aria-expanded carries it too).
export function LogsToggle({
  name,
  onToggle,
  open,
}: Readonly<{
  name: string;
  onToggle: () => void;
  open: boolean;
}>): React.JSX.Element {
  return (
    <button
      aria-expanded={open}
      aria-label={`${open ? "Hide" : "Show"} logs for ${name}`}
      className="quiet"
      onClick={onToggle}
      type="button"
    >
      {open ? GLYPH.clear : GLYPH.logs}
    </button>
  );
}
