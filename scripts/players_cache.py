"""
Utility to fetch FPL bootstrap and export players (id, name, position) to CSV.
Produces data/players.csv by default.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, List

import requests

FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"


def fetch_bootstrap() -> Dict:
    resp = requests.get(FPL_BOOTSTRAP_URL, timeout=15)
    resp.raise_for_status()
    return resp.json()


def build_position_lookup(data: Dict) -> Dict[int, str]:
    types = data.get("element_types") or []
    return {t.get("id"): (t.get("singular_name_short") or "") for t in types}


def extract_players(data: Dict) -> List[Dict[str, str]]:
    pos_lookup = build_position_lookup(data)
    players = []
    for e in data.get("elements", []):
        players.append(
            {
                "element": str(e.get("id")),
                "web_name": e.get("web_name", ""),
                "position": pos_lookup.get(e.get("element_type"), ""),
            }
        )
    return players


def write_csv(rows: List[Dict[str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["element", "web_name", "position"])
        writer.writeheader()
        writer.writerows(rows)


def main(argv: List[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else Path("data/players.csv")
    data = fetch_bootstrap()
    rows = extract_players(data)
    write_csv(rows, out)
    print(f"Wrote {len(rows)} players to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


