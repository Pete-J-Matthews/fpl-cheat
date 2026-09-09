"""Rendering FPL team picks as pitch HTML."""

from app.assets import get_jersey_b64
from app.comparison import iter_creator_players

LINES = ("GKP", "DEF", "MID", "FWD")
PLACEHOLDER = (
    '<p class="team-box-placeholder">👆 Select a creator team above to compare</p>'
)


def creator_team_to_picks(
    creator_team: dict, element_lookup: dict[int, dict[str, str]]
) -> list[dict]:
    """Convert a creator team's player_1..player_15 strings into pick dicts."""
    return [
        {
            "element": element_id,
            "position": slot,
            "multiplier": 1 if slot <= 11 else 0,  # Starters have multiplier > 0
            "is_captain": is_captain,
            "is_vice_captain": is_vice,
        }
        for slot, element_id, is_captain, is_vice in iter_creator_players(
            creator_team, element_lookup
        )
    ]


def _card_html(
    pick: dict,
    element_lookup: dict[int, dict[str, str]],
    team_lookup: dict[int, dict[str, str]],
    common_player_ids: set[int] | None,
) -> str:
    """One player card: name on the first row, position and captaincy on the second."""
    element_id = int(pick.get("element"))
    meta = element_lookup.get(element_id, {})
    name = meta.get("name", "")
    position = meta.get("position", "")
    team = team_lookup.get(int(meta.get("team_id", 0)), {})

    b64 = get_jersey_b64(team.get("short_name", ""), position == "GKP")
    img = (
        f'<img src="data:image/png;base64,{b64}" alt="{name}" />'
        if b64
        else f"<span>shirt {team.get('code', '')}</span>"  # Placeholder if the jersey isn't available
    )

    labels = [position] if position else []
    if pick.get("is_captain"):
        labels.append("C")
    elif pick.get("is_vice_captain"):
        labels.append("V")

    cls = "player-card player-card--small"
    if common_player_ids and element_id in common_player_ids:
        cls += " player-card--common"
    meta_line = f'<p class="player-meta">{" · ".join(labels)}</p>' if labels else ""
    return (
        f'<div class="player-cell"><div class="{cls}">{img}</div>'
        f'<p class="player-label">{name}</p>{meta_line}</div>'
    )


def pitch_as_html(
    picks: list[dict],
    element_lookup: dict[int, dict[str, str]],
    team_lookup: dict[int, dict[str, str]],
    title: str | None = None,
    common_player_ids: set[int] | None = None,
) -> str:
    """HTML for a team pitch (starters by line, then bench), for embedding in a team-box."""

    def row(row_picks: list[dict]) -> str:
        cards = "".join(
            _card_html(p, element_lookup, team_lookup, common_player_ids)
            for p in row_picks
        )
        return f'<div class="pitch-row">{cards}</div>'

    lines: dict[str, list[dict]] = {pos: [] for pos in LINES}
    for p in picks:
        if int(p.get("multiplier", 0)) > 0 and int(p.get("position", 0)) <= 11:
            pos = element_lookup.get(int(p.get("element")), {}).get("position", "")
            lines.setdefault(pos, []).append(p)
    bench = sorted(
        (p for p in picks if int(p.get("position", 0)) >= 12),
        key=lambda p: int(p.get("position", 0)),
    )

    parts = [f'<p class="team-box-title"><strong>{title}</strong></p>'] if title else []
    parts += [row(lines[pos]) for pos in LINES if lines[pos]]
    if bench:
        parts.append('<p class="team-box-bench"><strong>Bench:</strong></p>')
        parts.append(row(bench))
    return "".join(parts)
