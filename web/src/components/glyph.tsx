// A pictogram in place of a word: painted glyph, spoken label, optional tooltip
// (a title attribute paints the one-word name on hover; max 20 chars, no punctuation).
export function Glyph({
  glyph,
  label,
  title,
}: Readonly<{ glyph: string; label: string; title?: string }>): React.JSX.Element {
  return (
    <span aria-label={label} className="glyph" role="img" title={title}>
      {glyph}
    </span>
  );
}
