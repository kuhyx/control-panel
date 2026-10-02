// A button that flips a row's log panel open and shut. The panel itself is
// rendered by the row, in a full-width row of its own -- a 100-line log does
// not fit in a table cell.
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
      {open ? "Hide logs" : "Logs"}
    </button>
  );
}
