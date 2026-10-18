import { useEffect, useState } from "react";

export const COMMIT_MS = 300;

// A text input that commits 300 ms after the last keystroke (and resyncs when
// the committed value changes from outside, e.g. a shared link).
export function DraftInput({
  label,
  onCommit,
  placeholder,
  value,
}: Readonly<{
  label: string;
  onCommit: (value: string) => void;
  placeholder?: string;
  value: string;
}>): React.JSX.Element {
  const [draft, setDraft] = useState(value);
  const [seen, setSeen] = useState(value);
  if (seen !== value) {
    setSeen(value);
    setDraft(value);
  }
  useEffect(() => {
    if (draft === value) return;
    const timer = setTimeout(() => {
      onCommit(draft);
    }, COMMIT_MS);
    return () => {
      clearTimeout(timer);
    };
    // Only a new draft restarts the timer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);
  return (
    <input
      aria-label={label}
      className="table-input"
      onChange={(event) => {
        setDraft(event.target.value);
      }}
      placeholder={placeholder}
      type="search"
      value={draft}
    />
  );
}
