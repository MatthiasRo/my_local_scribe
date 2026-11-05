"""Interactive transcript editor with synchronized audio playback.

The browser side lives in ``assets/transcript_editor.js`` and ``.css``. It is a
Streamlit v2 component, so it runs in the app page with no iframe and loads
nothing from the internet.

The audio itself is played by a normal ``st.audio`` element placed inside a
container with the key ``PLAYER_CONTAINER_KEY``. The component finds that player
in the page and connects to it. This avoids sending the audio through the
component, which would resend it on every rerun.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

PLAYER_CONTAINER_KEY = "scribe_player"

_ASSETS = Path(__file__).parent / "assets"

_editor_component = st.components.v2.component(
    "my_local_scribe_transcript_editor",
    html='<div class="scribe-editor"></div>',
    css=(_ASSETS / "transcript_editor.css").read_text(encoding="utf-8"),
    js=(_ASSETS / "transcript_editor.js").read_text(encoding="utf-8"),
    # Selection and caret handling inside a shadow root differs between browsers,
    # so the editor stays in the page and prefixes all of its CSS classes instead.
    isolate_styles=False,
)


def split_text_into_parts(
    text: str, words: list[dict[str, Any]]
) -> list[list[str | float | None]]:
    """Split segment text into ``[text, start, end]`` parts for word highlighting.

    Joining all the parts gives back ``text`` exactly. Spaces, and words that have
    no timestamp, become parts with ``None`` timings, so numbers and symbols the
    aligner could not place still display normally. The split happens here rather
    than in JavaScript because Python and JavaScript count some characters
    differently, which would make character offsets unreliable.
    """
    parts: list[list[str | float | None]] = []
    cursor = 0
    for word in words:
        token = str(word.get("word", "")).strip()
        start = word.get("start")
        end = word.get("end")
        if not token or start is None or end is None:
            continue
        position = text.find(token, cursor)
        if position < 0:
            continue
        if position > cursor:
            parts.append([text[cursor:position], None, None])
        parts.append([token, round(float(start), 3), round(float(end), 3)])
        cursor = position + len(token)
    if cursor < len(text):
        parts.append([text[cursor:], None, None])
    return parts


def build_editor_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert WhisperX segments into the compact form the editor displays."""
    items: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        speaker_id = segment.get("speaker") or "UNKNOWN"
        text = str(segment.get("text", "")).strip()
        start = float(segment.get("start", 0.0) or 0.0)
        items.append(
            {
                "id": str(index),
                "start": round(start, 3),
                "end": round(float(segment.get("end", start) or start), 3),
                "speakerId": speaker_id,
                "text": text,
                "parts": split_text_into_parts(text, segment.get("words") or []),
            }
        )
    return items


def build_speaker_options(
    items: list[dict[str, Any]], name_map: dict[str, str]
) -> list[dict[str, str]]:
    """List every speaker a passage can be assigned to, in display order.

    Segments with no speaker are labelled ``UNKNOWN``, which isn't always in
    ``name_map``. The editor's menus need an option for every passage's speaker.
    """
    speaker_ids = list(name_map)
    for item in items:
        if item["speakerId"] not in speaker_ids:
            speaker_ids.append(item["speakerId"])
    return [{"id": speaker_id, "name": name_map.get(speaker_id, speaker_id)} for speaker_id in speaker_ids]


def transcript_editor(
    segments: list[dict[str, Any]],
    name_map: dict[str, str],
    run_id: str,
    has_audio: bool,
) -> tuple[dict[str, str], dict[str, str]]:
    """Show the editor and return the user's changes.

    Returns ``(edits, speaker_changes)``. ``edits`` maps a segment's index to its
    corrected text, and ``speaker_changes`` maps it to a reassigned speaker ID.
    """
    items = build_editor_segments(segments)
    result = _editor_component(
        data={
            "runId": run_id,
            "hasAudio": has_audio,
            "playerSelector": f".st-key-{PLAYER_CONTAINER_KEY} audio",
            "speakers": build_speaker_options(items, name_map),
            "segments": items,
        },
        default={"edits": {}, "speaker_changes": {}},
        key=f"transcript_editor_{run_id}",
        on_edits_change=lambda: None,
        on_speaker_changes_change=lambda: None,
    )
    return dict(result.edits or {}), dict(result.speaker_changes or {})
