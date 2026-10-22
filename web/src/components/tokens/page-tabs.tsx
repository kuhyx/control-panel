// The tab strip above the token pages. Plain links rather than role=tab:
// each tab is its own URL (bookmarkable, back-button friendly), so the
// active one is marked the way a nav marks the current page.
const TABS = [
  { href: "#/tokens", label: "Spend", name: "spend" },
  { href: "#/tokens/sessions", label: "Sessions", name: "sessions" },
] as const;

export function PageTabs({
  active,
}: Readonly<{ active: (typeof TABS)[number]["name"] }>): React.JSX.Element {
  return (
    <nav aria-label="Token views" className="page-tabs">
      {TABS.map((tab) => {
        return (
          <a
            aria-current={tab.name === active ? "page" : undefined}
            href={tab.href}
            key={tab.name}
          >
            {tab.label}
          </a>
        );
      })}
    </nav>
  );
}
