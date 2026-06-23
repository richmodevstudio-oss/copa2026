"""Orquestração da tabela da Copa: real (API) + previsto até a final.

A força é calculada uma vez (``ratings``); cada jogo da fase de grupos usa o
placar real se disputado, senão o previsto; o mata-mata é montado pelo mapa
fixo (``bracket_data``) e propagado por lambda até a final (PRD §4).
"""

from __future__ import annotations

from dataclasses import dataclass

from .data_source import FootballDataSource, canonical_name


@dataclass(frozen=True)
class FixtureMatch:
    stage: str
    group: str | None
    home: str | None
    away: str | None
    home_goals: int | None
    away_goals: int | None
    status: str
    winner: str | None
    utc_date: str


def _name(team: dict) -> str | None:
    raw = team.get("name")
    return canonical_name(raw) if raw else None


def parse_fixtures(payload: dict) -> list[FixtureMatch]:
    out: list[FixtureMatch] = []
    for m in payload.get("matches", []):
        full = m["score"]["fullTime"]
        out.append(
            FixtureMatch(
                stage=m["stage"],
                group=m.get("group"),
                home=_name(m["homeTeam"]),
                away=_name(m["awayTeam"]),
                home_goals=full["home"],
                away_goals=full["away"],
                status=m["status"],
                winner=m["score"].get("winner"),
                utc_date=m["utcDate"],
            )
        )
    return out


def fetch_wc_fixtures(source: FootballDataSource) -> list[FixtureMatch]:
    return parse_fixtures(source.competition_matches())
