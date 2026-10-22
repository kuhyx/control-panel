import { useEffect, useState } from "react";

// How long the armed "Confirm delete" waits for its second click.
const ARMED_MS = 5000;

// Two-step Delete, in-page (never a browser confirm()): the first click arms
// it and says what deleting means, the second within five seconds sends.
export function ConfirmDelete({
  count,
  isDisabled = false,
  label,
  onConfirm,
}: Readonly<{
  count: number;
  isDisabled?: boolean;
  // Accessible name of the idle button, e.g. "Delete alpha".
  label: string;
  onConfirm: () => void;
}>): React.JSX.Element {
  const [isArmed, setArmed] = useState(false);

  useEffect(() => {
    if (!isArmed) return;
    const timer = setTimeout(() => {
      setArmed(false);
    }, ARMED_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [isArmed]);

  if (!isArmed) {
    return (
      <button
        aria-label={label}
        className="quiet"
        disabled={isDisabled}
        onClick={() => {
          setArmed(true);
        }}
        type="button"
      >
        Delete
      </button>
    );
  }
  return (
    <>
      <button
        className="danger"
        disabled={isDisabled}
        onClick={() => {
          setArmed(false);
          onConfirm();
        }}
        type="button"
      >
        Confirm delete {count}?
      </button>
      <span className="confirm-note">
        Transcripts move to ~/.claude/projects-trash/; sessions active in the
        last 10 minutes are refused.
      </span>
    </>
  );
}
