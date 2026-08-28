r"""Add a domain to the hosts blocklist. Add only -- removal is impossible here.

Add-only is not enforced by this file either. ``hosts-blocker``'s
``check_custom_entries_protection`` diffs the entry set against a root-owned,
immutable state file and aborts the install if anything disappeared. Appending
is therefore the only edit that can survive, whoever makes it.

The ``# @rule`` comment written above each entry is metadata in a channel the
guard provably ignores: ``hosts_protect_custom.sh`` greps
``^0\\.0\\.0\\.0[[:space:]]+`` and takes field 2, so comments cannot affect the
diff. That is what lets the rationale panel attach a reason to a blocked domain
without weakening the protection.
"""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import TYPE_CHECKING

from control_panel.mutations import _repos
from control_panel.mutations._types import MutationResult

if TYPE_CHECKING:
    from pathlib import Path

    from control_panel._runner import CommandRunner

REPO = "hosts-blocker"
ENTRIES = "custom_entries.hosts"
INSTALLER = "install.sh"
# Rebuilding /etc/hosts concatenates a 4.6 MB upstream blocklist and re-applies
# the guard, so this is slow by nature rather than by accident.
TIMEOUT = 180.0

# Deliberately strict: this string is written into a file that a root-owned
# installer parses, so anything that is not obviously a hostname is refused
# rather than escaped.
_DOMAIN = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$")
_MAX_DOMAIN = 253
# Long enough that the reason is a sentence rather than a shrug.
MIN_REASON = 10


def _valid_domain(raw: object) -> str | None:
    """Return a normalised hostname, or None when it is not one."""
    if not isinstance(raw, str):
        return None
    domain = raw.strip().lower().rstrip(".")
    if not domain or len(domain) > _MAX_DOMAIN or not _DOMAIN.match(domain):
        return None
    return domain


def _already_blocked(entries: Path, domain: str) -> bool:
    """Report whether the domain is already an active entry."""
    try:
        text = entries.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    pattern = re.compile(rf"^0\.0\.0\.0\s+{re.escape(domain)}\s*$", re.MULTILINE)
    return pattern.search(text) is not None


def _block(domain: str, why: str) -> str:
    """Render the entry, with its reason in the ignored comment channel."""
    added = datetime.now(UTC).date().isoformat()
    reason = why.replace("\n", " ").replace('"', "'").strip()
    slug = f"dns.{domain}"
    return f'\n# @rule {slug} added={added} why="{reason}"\n0.0.0.0 {domain}\n'


def _parse_request(body: object) -> tuple[str, str] | MutationResult:
    """Validate the request, returning the failure rather than raising it."""
    if not isinstance(body, dict):
        return MutationResult.failure("Expected a JSON object.")
    domain = _valid_domain(body.get("domain"))
    if domain is None:
        return MutationResult.failure(
            "Expected 'domain' to be a hostname such as example.com."
        )
    why = str(body.get("why", "")).strip()
    if len(why) < MIN_REASON:
        return MutationResult.failure(
            f"Expected 'why' to be at least {MIN_REASON} characters: an entry "
            "whose reason was never written down is one you cannot review later."
        )
    return domain, why


def _locate_files(runner: CommandRunner) -> tuple[Path, Path] | MutationResult:
    """Find the entries file and the installer, or say why we cannot."""
    repo = _repos.locate(runner, REPO)
    if repo.path is None:
        return MutationResult.failure(f"Cannot find the {REPO} checkout: {repo.detail}")
    entries = repo.path / ENTRIES
    installer = repo.path / INSTALLER
    if not entries.is_file() or not installer.is_file():
        return MutationResult.failure(f"{entries} or {installer} is missing")
    return entries, installer


def apply(runner: CommandRunner, body: object) -> MutationResult:
    """Append one blocked domain and rebuild /etc/hosts."""
    parsed = _parse_request(body)
    if isinstance(parsed, MutationResult):
        return parsed
    domain, why = parsed

    located = _locate_files(runner)
    if isinstance(located, MutationResult):
        return located
    entries, installer = located
    if _already_blocked(entries, domain):
        return MutationResult.success(f"{domain} is already blocked.")

    try:
        with entries.open("a", encoding="utf-8") as handle:
            handle.write(_block(domain, why))
    except OSError as exc:
        return MutationResult.failure(f"Could not append to {entries}: {exc}")

    argv = ("/usr/bin/sudo", str(installer))
    result = runner.run(argv, timeout=TIMEOUT)
    if result.ok:
        return MutationResult.success(
            f"{domain} blocked and /etc/hosts rebuilt.",
            stdout=result.stdout[-4000:],
            argv=argv,
        )
    # The entry stays in the file: it is an addition, which the protection
    # check permits, and re-running the installer will pick it up. Removing it
    # here to "clean up" would be this dashboard performing the one edit the
    # whole guard exists to prevent.
    return MutationResult.refusal(
        f"{domain} was appended, but rebuilding /etc/hosts failed. "
        "The entry is still queued for the next install.",
        stderr=result.stderr.strip()[-4000:],
        argv=argv,
    )
