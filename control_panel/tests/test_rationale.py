from __future__ import annotations

import json
from typing import TYPE_CHECKING

from control_panel import _rationale, _systemctl
from control_panel._types import Level, Scope
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok

if TYPE_CHECKING:
    from pathlib import Path

UNIT_TEXT = """# /home/kuhy/.config/systemd/user/leetcode-guard.timer
[Unit]
Description=Fire the LeetCode gate

[Timer]
OnCalendar=*-*-* 09:00:00
# Persistent=true on purpose (flipped 2026-08-12). A missed slot was
# silently dropped for the whole day.
Persistent=true
"""


def cat_argv(unit: str, *, user: bool = True) -> tuple[str, ...]:
    scope = ("--user",) if user else ()
    return ("systemctl", *scope, "cat", unit, "--no-pager")


def test_comments_are_collected_from_inside_sections_not_just_the_header() -> None:
    # The reasoning in this fleet is written beside the directive it justifies,
    # so stopping at the first `[` header drops the richest rationale there is.
    extracted = _rationale._leading_comment(UNIT_TEXT)
    assert "Persistent=true on purpose" in extracted
    # The `# /path` provenance line is not rationale.
    assert "/home/kuhy" not in extracted


def test_unit_comment_artifacts_are_built_per_unit() -> None:
    entry = fleet.entry(units=(fleet.timer("leetcode-guard.timer"),))
    argv = cat_argv("leetcode-guard.timer")
    runner = FakeRunner({argv: ok(argv, UNIT_TEXT)})
    artifacts = _rationale.unit_comment(runner, entry)
    assert artifacts[0].kind == "unit-comment"
    assert artifacts[0].label == "leetcode-guard.timer"


def test_units_without_comments_contribute_nothing() -> None:
    entry = fleet.entry(units=(fleet.timer("bare.timer"),))
    argv = cat_argv("bare.timer")
    runner = FakeRunner({argv: ok(argv, "[Unit]\nDescription=x\n")})
    assert _rationale.unit_comment(runner, entry) == []


def test_a_long_excerpt_is_clipped() -> None:
    clipped = _rationale._clip("x" * (_rationale.MAX_EXCERPT_CHARS + 500))
    assert clipped.endswith("[...]")
    assert len(clipped) < _rationale.MAX_EXCERPT_CHARS + 20


def test_a_short_excerpt_is_untouched() -> None:
    assert _rationale._clip("  hello  ") == "hello"


def test_missing_sidecar_is_the_normal_case(tmp_path: Path) -> None:
    loaded = _rationale.load_sidecar("nothing", tmp_path)
    assert loaded.rules == ()
    assert loaded.signals == ()


def test_malformed_sidecar_warns_rather_than_raising(tmp_path: Path) -> None:
    (tmp_path / "x.json").write_text("{{{ not json")
    loaded = _rationale.load_sidecar("x", tmp_path)
    assert loaded.rules == ()
    assert loaded.signals[0].code == "rationale-unreadable"
    assert loaded.signals[0].level is Level.WARN


def test_sidecar_without_rules_warns(tmp_path: Path) -> None:
    (tmp_path / "x.json").write_text(json.dumps({"schema_version": 1}))
    loaded = _rationale.load_sidecar("x", tmp_path)
    assert loaded.signals[0].code == "rationale-malformed"


def test_sidecar_rules_parse(tmp_path: Path) -> None:
    (tmp_path / "x.json").write_text(
        json.dumps(
            {
                "rules": {
                    "a.rule": {
                        "why": "because",
                        "ratchet": "earlier only",
                        "cost_of_bypass": "chattr -i",
                        "added": "2026-01-01",
                        "supersedes": ["old.timer"],
                    },
                    "junk": "not an object",
                }
            }
        )
    )
    loaded = _rationale.load_sidecar("x", tmp_path)
    assert [rule.id for rule in loaded.rules] == ["a.rule"]
    assert loaded.rules[0].supersedes == ("old.timer",)


def test_audit_reasons_quote_the_reason_column(sysroot: Path) -> None:
    audit = sysroot / "etc/audit.log"
    audit.write_text("2026-05-31 | APPROVED | app_id=880940 | reason='party game'\n")
    found = _rationale.audit_reasons("/etc/audit.log", "approvals")
    assert found is not None
    assert "party game" in found.excerpt


def test_an_empty_audit_file_says_so_rather_than_rendering_blank(
    sysroot: Path,
) -> None:
    # /etc/shutdown-schedule-overrides.conf is 0 bytes on the real machine.
    (sysroot / "etc/empty.conf").write_text("")
    found = _rationale.audit_reasons("/etc/empty.conf", "overrides")
    assert found is not None
    assert found.excerpt == "no entries recorded"


def test_a_missing_audit_file_contributes_nothing() -> None:
    assert _rationale.audit_reasons("/etc/absent.log", "x") is None


def test_doc_excerpts_resolve_home_and_absolute_paths(sysroot: Path) -> None:
    (sysroot / "home/tester/DOCS-x.md").write_text("# Why\nBecause.")
    (sysroot / "etc/policy.md").write_text("# Policy")
    assert _rationale.doc_excerpt("~/DOCS-x.md", "x") is not None
    assert _rationale.doc_excerpt("/etc/policy.md", "p") is not None


def test_a_missing_doc_contributes_nothing() -> None:
    assert _rationale.doc_excerpt("/etc/absent.md", "x") is None


def test_build_merges_artifacts_and_sidecar_rules(sysroot: Path) -> None:
    (sysroot / "etc/policy.md").write_text("# Policy\nBecause.")
    (sysroot / "etc/audit.log").write_text("reason='x'\n")
    entry = fleet.entry(
        units=(fleet.timer("leetcode-guard.timer"),),
        docs=(_manifest_source("/etc/policy.md", "policy"),),
        audits=(_manifest_source("/etc/audit.log", "audit"),),
    )
    argv = cat_argv("leetcode-guard.timer")
    runner = FakeRunner({argv: ok(argv, UNIT_TEXT)})
    built = _rationale.build(runner, entry)
    kinds = [artifact.kind for artifact in built.artifacts]
    assert kinds == ["unit-comment", "doc", "audit-log"]


def test_payload_is_json_serialisable(sysroot: Path) -> None:
    entry = fleet.entry()
    built = _rationale.build(FakeRunner({}), entry)
    assert json.dumps(_rationale.to_payload(built))


def _manifest_source(path: str, label: str) -> object:
    from control_panel._manifest import ManifestSource

    return ManifestSource(path=path, label=label)


def test_the_shipped_sidecars_all_parse() -> None:
    # These are data, and data rots.
    for name in ("shutdown", "kuhytrack", "phone-focus-mode"):
        loaded = _rationale.load_sidecar(name)
        assert loaded.rules, name
        assert loaded.signals == (), name


def test_the_shutdown_sidecar_records_the_inverted_ratchet() -> None:
    # The one fact most likely to be got wrong in Phase 2.
    loaded = _rationale.load_sidecar("shutdown")
    morning = next(r for r in loaded.rules if r.id == "shutdown.morning-end-hour")
    assert "opposite direction" in morning.ratchet


def test_scope_flag_is_passed_to_cat() -> None:
    entry = fleet.entry(units=(fleet.timer("s.timer", Scope.SYSTEM),))
    argv = cat_argv("s.timer", user=False)
    runner = FakeRunner({argv: ok(argv, "# note\n[Unit]\n")})
    assert _rationale.unit_comment(runner, entry)
    assert runner.calls == [argv]
    assert _systemctl.SHOW_PROPERTIES  # module is wired, not shadowed


def test_a_declared_doc_that_is_missing_is_skipped_not_fatal(sysroot: Path) -> None:
    entry = fleet.entry(
        docs=(_manifest_source("/etc/absent.md", "gone"),),
        audits=(_manifest_source("/etc/absent.log", "gone"),),
    )
    built = _rationale.build(FakeRunner({}), entry)
    assert built.artifacts == ()
