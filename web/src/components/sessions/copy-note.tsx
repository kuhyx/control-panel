import { GLYPH } from "../../lib/glyphs.ts";

// Spoken outcomes of a clipboard copy; the note paints ✓ or ✕ (and, for a
// bulk copy, how many commands went to the clipboard).
export const COPIED = "Copied";
export const COPY_FAILED = "Copy failed";

export function CopyNote({
  copied,
  count = null,
}: Readonly<{ copied: string; count?: null | number }>): React.JSX.Element {
  const isFailed = copied === COPY_FAILED;
  return (
    <span aria-label={copied} className="category" role="status">
      {isFailed ? GLYPH.fail : GLYPH.ok}
      {!isFailed && count !== null && ` ${String(count)}`}
    </span>
  );
}
