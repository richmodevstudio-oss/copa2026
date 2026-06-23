"""Gera ``src/copa2026/pre_wc_data.py`` com os jogos pré-Copa das 48 seleções.

Fonte: API pública (não-oficial) de resultados da ESPN. Coleta, para cada
seleção da Copa, os jogos finalizados **anteriores** ao início da Copa
(2026-06-11), excluindo a própria Copa (esses vêm da football-data.org em tempo
real). O resultado é um arquivo Python com uma lista achatada e deduplicada.

Uso:
    python scripts/generate_pre_wc_data.py
"""

from __future__ import annotations

import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from copa2026.data_source import canonical_name  # noqa: E402

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
WC_START = date(2026, 6, 11)
WC_LEAGUE = "fifa.world"  # a própria Copa (excluída; vem da football-data)
MAX_PER_TEAM = 12
_LEAGUE_RE = re.compile(r"/leagues/([^/]+)/")


def espn_team_ids() -> dict[str, int]:
    """Mapa ``nome canônico -> espn id`` para as 48 seleções da Copa."""
    data = requests.get(f"{ESPN_BASE}/fifa.world/teams", timeout=30).json()
    teams = data["sports"][0]["leagues"][0]["teams"]
    return {canonical_name(t["team"]["displayName"]): int(t["team"]["id"]) for t in teams}


def team_matches(espn_id: int) -> list[tuple[str, str, str, int, int]]:
    """Jogos pré-Copa finalizados de um time: (data, casa, fora, gc, gf)."""
    url = f"{ESPN_BASE}/all/teams/{espn_id}/schedule?season=2026"
    events = requests.get(url, timeout=30).json().get("events", [])
    out = []
    for ev in events:
        comp = ev["competitions"][0]
        if not comp["status"]["type"].get("completed"):
            continue
        played_on = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).date()
        if played_on >= WC_START:
            continue
        sides = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in sides or "away" not in sides:
            continue
        league = _LEAGUE_RE.search(sides["home"]["score"].get("$ref", ""))
        if league and league.group(1) == WC_LEAGUE:
            continue
        try:
            gh = int(sides["home"]["score"]["value"])
            ga = int(sides["away"]["score"]["value"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append(
            (
                played_on.isoformat(),
                canonical_name(sides["home"]["team"]["displayName"]),
                canonical_name(sides["away"]["team"]["displayName"]),
                gh,
                ga,
            )
        )
    out.sort(reverse=True)  # mais recentes primeiro
    return out[:MAX_PER_TEAM]


def main() -> int:
    ids = espn_team_ids()
    print(f"Times resolvidos: {len(ids)}/48", file=sys.stderr)

    seen: set[tuple] = set()
    rows: list[tuple[str, str, str, int, int]] = []
    for team, espn_id in sorted(ids.items()):
        matches = team_matches(espn_id)
        print(f"  {team}: {len(matches)} jogos", file=sys.stderr)
        for m in matches:
            if m not in seen:
                seen.add(m)
                rows.append(m)
        time.sleep(0.3)  # gentileza com a API

    rows.sort(key=lambda r: r[0], reverse=True)

    out_path = Path(__file__).parent.parent / "src" / "copa2026" / "pre_wc_data.py"
    lines = [
        '"""Jogos pré-Copa das 48 seleções (gerado automaticamente).',
        "",
        "NÃO editar à mão. Regenerar com: python scripts/generate_pre_wc_data.py",
        f"Fonte: ESPN. Gerado em {date.today().isoformat()}. "
        f"Apenas jogos finalizados anteriores a {WC_START.isoformat()} "
        "(a Copa em si vem da football-data.org).",
        '"""',
        "",
        "# (data ISO, mandante, visitante, gols mandante, gols visitante)",
        "PRE_WC_MATCHES: list[tuple[str, str, str, int, int]] = [",
    ]
    for d, h, a, gh, ga in rows:
        lines.append(f'    ({d!r}, {h!r}, {a!r}, {gh}, {ga}),')
    lines.append("]")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Escrito {out_path} com {len(rows)} jogos.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
