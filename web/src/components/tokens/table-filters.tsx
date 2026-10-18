import { DraftInput } from "./draft-input.tsx";

export interface ColumnMeta {
  kind: "enum" | "number" | "object" | "text";
  values?: string[];
}

function NumberFilter({
  label,
  onRule,
  rule,
}: Readonly<{
  label: string;
  onRule: (rule: string) => void;
  rule: string;
}>): React.JSX.Element {
  const cut = rule.indexOf("..");
  const low = cut === -1 ? "" : rule.slice(0, cut);
  const high = cut === -1 ? "" : rule.slice(cut + 2);
  const commit = (lo: string, hi: string): void => {
    onRule(lo === "" && hi === "" ? "" : `${lo}..${hi}`);
  };
  return (
    <span className="range-filter">
      <DraftInput
        label={`${label} min`}
        onCommit={(value) => {
          commit(value, high);
        }}
        placeholder="min"
        value={low}
      />
      <DraftInput
        label={`${label} max`}
        onCommit={(value) => {
          commit(low, value);
        }}
        placeholder="max"
        value={high}
      />
    </span>
  );
}

function EnumFilter({
  label,
  onRule,
  rule,
  values,
}: Readonly<{
  label: string;
  onRule: (rule: string) => void;
  rule: string;
  values: string[];
}>): React.JSX.Element {
  const chosen = rule.startsWith("=") ? rule.slice(1).split("|") : [];
  return (
    <select
      aria-label={`${label} is one of`}
      className="table-input"
      multiple
      onChange={(event) => {
        const picked = [...event.target.selectedOptions].map((o) => o.value);
        onRule(picked.length === 0 ? "" : `=${picked.join("|")}`);
      }}
      size={Math.min(values.length, 3)}
      value={chosen}
    >
      {values.map((value) => {
        return (
          <option key={value} value={value}>
            {value}
          </option>
        );
      })}
    </select>
  );
}

// One column's filter control, by the column kind the backend reported.
export function FilterCell({
  label,
  meta,
  onRule,
  rule,
}: Readonly<{
  label: string;
  meta: ColumnMeta | undefined;
  onRule: (rule: string) => void;
  rule: string;
}>): null | React.JSX.Element {
  const kind = meta?.kind ?? "text";
  if (kind === "object") return null;
  if (kind === "number")
    return <NumberFilter label={label} onRule={onRule} rule={rule} />;
  if (kind === "enum") {
    return (
      <EnumFilter
        label={label}
        onRule={onRule}
        rule={rule}
        values={meta?.values ?? []}
      />
    );
  }
  return (
    <DraftInput
      label={`${label} contains`}
      onCommit={(value) => {
        onRule(value === "" ? "" : `~${value}`);
      }}
      placeholder="contains"
      value={rule.startsWith("~") ? rule.slice(1) : ""}
    />
  );
}
