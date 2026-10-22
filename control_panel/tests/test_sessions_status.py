from __future__ import annotations

import pytest

from control_panel.sessions import _status


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("All green.\nDONE: committed abc123, 12 passed", "done"),
        ("NEEDS ACTION: run `! sudo x`", "needs_action"),
        ("QUESTION: which branch?", "question"),
        ("RUNNING: CI on abc123, next check 5 min", "running"),
        ("just some prose, no tag", "untagged"),
        ("", "untagged"),
        # The tag is often followed by a NOTE line; every line is scanned.
        ("DONE: 3 tests pass\nNOTE: other dirty files in web/", "done"),
        ("  **DONE:** shipped", "done"),
        ("**NEEDS ACTION:** approve the push", "needs_action"),
        # A tag mid-sentence is prose, not a tag.
        ("I am not DONE: yet", "untagged"),
    ],
)
def test_classifies_the_status_tag(text: str, expected: str) -> None:
    assert _status.classify(text) == expected


def test_continuing_matches_anywhere_and_case_insensitively() -> None:
    text = "Handed off.\nNEEDS ACTION: open it -- continuing In New Session abc"
    assert _status.classify(text) == "continuing"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("RUNNING: x\nQUESTION: y", "question"),
        ("QUESTION: y\nNEEDS ACTION: z", "needs_action"),
        ("NEEDS ACTION: z\nDONE: w", "done"),
        ("DONE: w\nCONTINUING in new session", "continuing"),
    ],
)
def test_precedence_when_several_tags_appear(text: str, expected: str) -> None:
    assert _status.classify(text) == expected


@pytest.mark.parametrize(
    "content",
    [
        "<command-name>/model</command-name>",
        "<local-command-stdout>Set model</local-command-stdout>",
        "<task-notification>agent finished</task-notification>",
        "<bash-input>ls</bash-input>",
        "<bash-stdout>x</bash-stdout>",
        [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}],
    ],
)
def test_generated_user_content_is_not_a_prompt(content: object) -> None:
    record = {"type": "user", "message": {"role": "user", "content": content}}
    assert _status.prompt_text(record) is None


def test_meta_and_compact_summary_records_are_not_prompts() -> None:
    message = {"role": "user", "content": "hi"}
    assert _status.prompt_text({"message": message, "isMeta": True}) is None
    assert _status.prompt_text({"message": message, "isCompactSummary": True}) is None
    assert _status.prompt_text({"message": message, "isSidechain": True}) is None


def test_prompt_text_reads_strings_and_text_blocks() -> None:
    assert _status.prompt_text({"message": {"content": "  hi  "}}) == "hi"
    blocks = [
        {"type": "text", "text": "<system-reminder>ctx</system-reminder>"},
        {"type": "text", "text": "real ask"},
    ]
    assert _status.prompt_text({"message": {"content": blocks}}) == "real ask"


def test_assistant_text_joins_only_text_blocks() -> None:
    blocks = [
        {"type": "thinking", "thinking": "secret"},
        {"type": "text", "text": "a"},
        {"type": "tool_use", "name": "Bash"},
        {"type": "text", "text": "b"},
    ]
    assert _status.assistant_text({"message": {"content": blocks}}) == "a\nb"
    assert _status.assistant_text({"message": {"content": [blocks[0]]}}) is None
    assert _status.assistant_text({"message": {"content": "x"}}) is None


def test_a_record_without_a_message_is_not_a_prompt() -> None:
    assert _status.prompt_text({"type": "user"}) is None
    image = [{"type": "image", "source": {}}]
    assert _status.prompt_text({"message": {"content": image}}) == "[image]"
