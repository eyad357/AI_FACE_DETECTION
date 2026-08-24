"""
Campus Map -- presentation-only, deterministic navigator widget.

This module is UI-only: a small, hard-coded university floor/campus
map (rendered as inline SVG) plus a deterministic keyword -> destination
matcher and hand-written route instructions. It does NOT call, wrap,
or replace ``app.navigation`` (the real ``NavigationService`` /
pathfinder) or any other core module -- see ``app/ui/demo.py``'s
"University Assistant" dashboard section for how it's used.

Everything here is intentionally static and deterministic, by design:

  - A fixed coordinate layout for exactly five destinations plus a
    single "you are here" origin -- not a real GIS/map, no geographic
    accuracy implied.
  - Fixed keyword -> destination matching (case-insensitive substring
    check against a small hard-coded phrase list) -- no LLM, no
    embeddings, no vector search, no fuzzy matching.
  - Fixed, hand-written route instructions -- no real pathfinding.

Rendering ``render_map_svg`` twice with the same argument always
produces byte-identical output: pure string formatting over static
data, no randomness, no network calls, no external assets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Fixed location data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CampusDestination:
    """One of the five fixed, known destinations on the campus map."""

    id: str
    label: str
    keywords: Tuple[str, ...]
    instruction: str
    room: Tuple[int, int, int, int]  # x, y, width, height
    marker: Tuple[int, int]  # top-center of the room; where corridors meet it


DESTINATIONS: Tuple[CampusDestination, ...] = (
    CampusDestination(
        id="ai_lab",
        label="AI Lab",
        keywords=("ai lab", "artificial intelligence lab", "ai laboratory"),
        instruction="Head down the main corridor, then turn right. The AI Lab is on your left.",
        room=(40, 150, 150, 90),
        marker=(115, 150),
    ),
    CampusDestination(
        id="robotics_lab",
        label="Robotics Lab",
        keywords=("robotics lab", "robot lab", "robotics"),
        instruction="Follow the main corridor and turn left at the science wing.",
        room=(410, 150, 150, 90),
        marker=(485, 150),
    ),
    CampusDestination(
        id="library",
        label="Library",
        keywords=("library", "books"),
        instruction="Continue straight through the central corridor. The Library is ahead.",
        room=(225, 150, 150, 90),
        marker=(300, 150),
    ),
    CampusDestination(
        id="ta_office",
        label="Teaching Assistant Office",
        keywords=(
            "teaching assistant office",
            "teaching assistant",
            "ta office",
            "assistant office",
        ),
        instruction="Walk toward the administration wing. The Teaching Assistant Office is on the right.",
        room=(225, 300, 150, 80),
        marker=(300, 300),
    ),
    CampusDestination(
        id="cafeteria",
        label="Cafeteria",
        keywords=("cafeteria", "canteen", "food", "dining"),
        instruction="Follow the main corridor toward the east wing. The Cafeteria is ahead.",
        room=(225, 420, 150, 80),
        marker=(300, 420),
    ),
)

_BY_ID: Dict[str, CampusDestination] = {d.id: d for d in DESTINATIONS}

UNKNOWN_DESTINATION_MESSAGE = (
    "I can currently help you find: AI Lab, Robotics Lab, Library, "
    "Teaching Assistant Office, and Cafeteria."
)

ORIGIN_LABEL = "You are here"
ORIGIN_POINT = (300, 40)
_JUNCTION = (300, 120)


def all_destinations() -> Tuple[CampusDestination, ...]:
    """All five fixed destinations, in the order they should be listed/buttoned."""
    return DESTINATIONS


def get_destination(destination_id: str) -> Optional[CampusDestination]:
    """Look up a destination by its canonical id, or None if unknown."""
    return _BY_ID.get(destination_id)


# ---------------------------------------------------------------------------
# Deterministic keyword matching (no LLM / embeddings / vector store)
# ---------------------------------------------------------------------------


def resolve_destination(text: str) -> Optional[str]:
    """
    Resolve free-text like "Where is the AI Lab?" to a destination id
    using a small, fixed, case-insensitive substring match against each
    destination's hard-coded keyword list.

    When more than one keyword matches, the longest (most specific)
    keyword wins, so e.g. "teaching assistant office" is preferred
    over the shorter "teaching assistant" when both are substrings of
    the same phrase.

    Returns None if nothing matches -- callers should show
    ``UNKNOWN_DESTINATION_MESSAGE`` rather than guessing.
    """
    if not text:
        return None
    haystack = text.strip().lower()
    if not haystack:
        return None

    best_match: Optional[Tuple[int, str]] = None
    for dest in DESTINATIONS:
        for keyword in dest.keywords:
            if keyword in haystack:
                candidate = (len(keyword), dest.id)
                if best_match is None or candidate[0] > best_match[0]:
                    best_match = candidate
    return best_match[1] if best_match else None


# ---------------------------------------------------------------------------
# Static SVG floor-plan rendering
# ---------------------------------------------------------------------------

# Corridor segments that always exist, dim, regardless of selection.
_BASE_CORRIDOR_SEGMENTS: Tuple[Tuple[int, int, int, int], ...] = (
    (*ORIGIN_POINT, *_JUNCTION),
    (120, 120, 480, 120),
    (300, 120, 300, 460),
)


def _route_segments(selected_id: Optional[str]) -> List[Tuple[int, int, int, int]]:
    """The ordered corridor segments making up the highlighted route to
    ``selected_id``, from the origin. Empty if nothing is selected."""
    dest = _BY_ID.get(selected_id) if selected_id else None
    if dest is None:
        return []

    jx, jy = _JUNCTION
    mx, my = dest.marker
    segments = [(*ORIGIN_POINT, jx, jy)]

    if dest.id in ("ai_lab", "robotics_lab"):
        segments.append((jx, jy, mx, jy))
        segments.append((mx, jy, mx, my))
    elif dest.id == "library":
        segments.append((jx, jy, mx, my))
    elif dest.id == "ta_office":
        lib = _BY_ID["library"]
        segments.append((jx, jy, *lib.marker))
        segments.append((*lib.marker, mx, my))
    elif dest.id == "cafeteria":
        lib = _BY_ID["library"]
        ta = _BY_ID["ta_office"]
        segments.append((jx, jy, *lib.marker))
        segments.append((*lib.marker, *ta.marker))
        segments.append((*ta.marker, mx, my))
    return segments


def _label_lines(label: str) -> List[str]:
    """Wrap a destination label onto one or two lines so it fits its room."""
    if len(label) <= 12:
        return [label]
    words = label.split(" ")
    mid = len(words) // 2 + len(words) % 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def render_map_svg(selected_id: Optional[str] = None) -> str:
    """
    Build the static campus floor-plan as an inline SVG string.

    Purely deterministic string formatting over the fixed data above --
    calling this twice with the same ``selected_id`` always returns the
    same string. No randomness, no network calls, no external assets.
    """
    parts: List[str] = []
    parts.append(
        '<svg viewBox="0 0 600 500" xmlns="http://www.w3.org/2000/svg" '
        'style="width:100%;height:auto;display:block;" '
        'role="img" aria-label="University campus map">'
    )
    parts.append(
        '<defs><pattern id="campusGrid" width="24" height="24" patternUnits="userSpaceOnUse">'
        '<path d="M 24 0 L 0 0 0 24" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>'
        "</pattern></defs>"
    )
    parts.append('<rect x="0" y="0" width="600" height="500" rx="20" fill="#10162c" />')
    parts.append('<rect x="0" y="0" width="600" height="500" rx="20" fill="url(#campusGrid)" />')

    for x1, y1, x2, y2 in _BASE_CORRIDOR_SEGMENTS:
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            'stroke="rgba(151,162,201,0.35)" stroke-width="6" stroke-linecap="round" />'
        )

    for x1, y1, x2, y2 in _route_segments(selected_id):
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            'stroke="#7c9dff" stroke-width="6" stroke-linecap="round" />'
        )

    for dest in DESTINATIONS:
        x, y, w, h = dest.room
        is_selected = dest.id == selected_id
        fill = "rgba(91,227,171,0.16)" if is_selected else "rgba(255,255,255,0.045)"
        stroke = "#5be3ab" if is_selected else "rgba(255,255,255,0.16)"
        stroke_width = 2.5 if is_selected else 1.5
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" />'
        )

        # Door opening: a small gap-marker on the wall facing the corridor.
        door_x = dest.marker[0] - 12
        door_y = y - 1 if dest.marker[1] <= y else y + h - 1
        parts.append(
            f'<rect x="{door_x}" y="{door_y}" width="24" height="3" rx="1.5" fill="#10162c" />'
        )

        label_x = x + w / 2
        lines = _label_lines(dest.label)
        weight = "700" if is_selected else "600"
        color = "#eef1ff" if is_selected else "#c3cbef"
        base_y = y + h / 2 + (4 if len(lines) == 1 else -3)
        for i, line in enumerate(lines):
            parts.append(
                f'<text x="{label_x}" y="{base_y + i * 18}" text-anchor="middle" '
                f'font-size="13" font-weight="{weight}" fill="{color}" '
                f'font-family="Inter, sans-serif">{line}</text>'
            )

        marker_color = "#5be3ab" if is_selected else "#7c9dff"
        mx, my = dest.marker
        parts.append(f'<circle cx="{mx}" cy="{my}" r="5" fill="{marker_color}" />')

    ox, oy = ORIGIN_POINT
    parts.append(f'<circle cx="{ox}" cy="{oy}" r="9" fill="#ffc16b" stroke="#10162c" stroke-width="3" />')
    parts.append(
        f'<text x="{ox}" y="{oy - 16}" text-anchor="middle" font-size="13" font-weight="700" '
        f'fill="#ffc16b" font-family="Inter, sans-serif">{ORIGIN_LABEL}</text>'
    )

    parts.append("</svg>")
    return "".join(parts)
