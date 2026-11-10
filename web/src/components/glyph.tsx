// A pictogram in place of a word: painted glyph, spoken label, no tooltip
// (a title attribute paints the word back on hover).
export function Glyph({
  glyph,
  label,
}: Readonly<{ glyph: string; label: string }>): React.JSX.Element {
  return (
    <span aria-label={label} className="glyph" role="img">
      {glyph}
    </span>
  );
}
