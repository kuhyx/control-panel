import { GLYPH } from "../lib/glyphs.ts";

// A failed read or action: a warning glyph in the danger tone, the error
// itself spoken only (it is a sentence built by the client or the server).
export function ErrorNote({
  error,
}: Readonly<{ error: string }>): React.JSX.Element {
  return (
    <span aria-label={error} className="empty error-note" role="alert">
      {GLYPH.error}
    </span>
  );
}
