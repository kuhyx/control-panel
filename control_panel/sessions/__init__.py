"""Live index of Claude Code sessions, classified by their final status tag.

Every interactive session ends its last assistant message on a status tag
(``DONE:``, ``NEEDS ACTION:``, ...). Reading that tag is what turns a
1000-row ``/resume`` list into "these three still need me".

Deliberately independent of :mod:`control_panel.tokens`: that package reads a
SQLite store refreshed every 30 minutes, and a session list that lags half an
hour behind the terminal is wrong in exactly the case it exists for. This one
reads the JSONL transcripts directly, cached per file version.

This package only reads. The three mutations that act on sessions (resume in
a terminal, manual mark-done, move to a recoverable trash) live in
:mod:`control_panel.mutations`, like every other write; the delete only asks
the scanner to forget its in-memory parse of what it moved.
"""
