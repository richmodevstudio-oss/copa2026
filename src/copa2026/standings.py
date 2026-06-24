"""Classificação de grupo pelos critérios oficiais FIFA (PRD Apêndice).

Ordem dos critérios: pontos -> saldo geral -> gols pró geral; entre times
empatados nesses três: pontos, saldo e gols pró **apenas nos confrontos
diretos**; persistindo o empate, desempate determinístico por nome (stand-in
para fair-play/sorteio, indisponíveis sem dados de cartões).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TeamRecord:
    team: str
    played: int = 0
    won: int = 0
    draw: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return 3 * self.won + self.draw

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


def _tally(teams, matches) -> dict[str, TeamRecord]:
    rec = {t: TeamRecord(t) for t in teams}
    for home, away, gh, ga in matches:
        if home not in rec or away not in rec:
            continue
        rh, ra = rec[home], rec[away]
        rh.played += 1
        ra.played += 1
        rh.goals_for += gh
        rh.goals_against += ga
        ra.goals_for += ga
        ra.goals_against += gh
        if gh > ga:
            rh.won += 1
            ra.lost += 1
        elif gh < ga:
            ra.won += 1
            rh.lost += 1
        else:
            rh.draw += 1
            ra.draw += 1
    return rec


def compute_group_table(teams, matches) -> list[TeamRecord]:
    rec = _tally(teams, matches)

    def overall(t):
        r = rec[t]
        return (r.points, r.goal_diff, r.goals_for)

    order = sorted(teams, key=lambda t: (*[-v for v in overall(t)], t))

    final: list[str] = []
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and overall(order[j + 1]) == overall(order[i]):
            j += 1
        tied = order[i : j + 1]
        if len(tied) > 1:
            tied = _resolve_tied(tied, matches)
        final.extend(tied)
        i = j + 1
    return [rec[t] for t in final]


def _resolve_tied(tied, matches) -> list[str]:
    tset = set(tied)
    sub = [m for m in matches if m[0] in tset and m[1] in tset]
    subrec = _tally(tied, sub)

    def h2h(t):
        r = subrec[t]
        return (r.points, r.goal_diff, r.goals_for)

    return sorted(tied, key=lambda t: (*[-v for v in h2h(t)], t))


def rank_third_places(thirds) -> list[tuple[str, TeamRecord]]:
    """Os 8 melhores terceiros, por pontos -> saldo -> gols pró -> grupo."""
    return sorted(
        thirds,
        key=lambda gr: (-gr[1].points, -gr[1].goal_diff, -gr[1].goals_for, gr[0]),
    )[:8]
