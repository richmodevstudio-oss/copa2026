"""Orquestração da tabela da Copa: real (API) + previsto até a final.

A força é calculada uma vez (``ratings``); cada jogo da fase de grupos usa o
placar real se disputado, senão o previsto; o mata-mata é montado pelo mapa
fixo (``bracket_data``) e propagado por lambda até a final (PRD §4).
"""

from __future__ import annotations

from dataclasses import dataclass

from .bracket_data import GROUPS, MATCHES, STAGE_OF
from .data_source import FootballDataSource, canonical_name
from .ratings import predict_scoreline, knockout_winner
from .standings import TeamRecord, compute_group_table, rank_third_places
from .third_place_data import BEST_THIRD_ALLOCATION


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


def finished_results(fixtures: list[FixtureMatch]) -> list[tuple[str, str, str, int, int]]:
    """Jogos da Copa já disputados como tuplas ``(data, mandante, visitante, gh, ga)``,
    no formato de ``HardcodedDataSource`` — permite calcular a força incluindo os
    resultados reais da Copa sem uma chamada de rede por seleção."""
    return [
        (f.utc_date[:10], f.home, f.away, f.home_goals, f.away_goals)
        for f in fixtures
        if f.status == "FINISHED"
        and f.home and f.away
        and f.home_goals is not None
        and f.away_goals is not None
    ]


# ---------------------------------------------------------------------------
# Dataclasses de resultado
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GroupResult:
    """Resultado da fase de grupos de um grupo."""
    group: str
    table: list[TeamRecord]


@dataclass(frozen=True)
class KnockoutResult:
    """Resultado de um jogo de mata-mata."""
    match_no: int
    stage: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    winner: str
    loser: str
    real: bool
    penalties: bool


@dataclass(frozen=True)
class TournamentResult:
    """Resultado completo do torneio (grupos + chaveamento + chave dos terceiros)."""
    groups: list[GroupResult]
    knockout: list[KnockoutResult]
    third_key: str


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _group_members(fixtures) -> dict[str, list[str]]:
    """Extrai os times de cada grupo a partir dos jogos da fase de grupos."""
    members: dict[str, list[str]] = {g: [] for g in GROUPS}
    for f in fixtures:
        if f.stage != "GROUP_STAGE":
            continue
        letter = f.group.removeprefix("GROUP_")
        for team in (f.home, f.away):
            if team and team not in members[letter]:
                members[letter].append(team)
    return members


def _group_scorelines(fixtures, ratings, mu, max_goals):
    """Retorna (grupo -> lista de (home, away, gh, ga)) com placar real ou previsto."""
    by_group: dict[str, list[tuple[str, str, int, int]]] = {g: [] for g in GROUPS}
    for f in fixtures:
        if f.stage != "GROUP_STAGE":
            continue
        letter = f.group.removeprefix("GROUP_")
        if f.status == "FINISHED" and f.home_goals is not None:
            gh, ga = f.home_goals, f.away_goals
        else:
            gh, ga = predict_scoreline(f.home, f.away, ratings, mu,
                                       max_goals=max_goals).palpite
        by_group[letter].append((f.home, f.away, gh, ga))
    return by_group


def _api_knockout_by_match(fixtures) -> dict[int, "FixtureMatch"]:
    """Casa jogos de mata-mata da API aos números de jogo por ordem cronológica
    dentro de cada fase (a API não liga jogo a slot — limitação documentada)."""
    mapping: dict[int, FixtureMatch] = {}
    for stage in {STAGE_OF[n] for n in MATCHES}:
        numbers = sorted(n for n in MATCHES if STAGE_OF[n] == stage)
        api = sorted(
            (f for f in fixtures if f.stage == stage),
            key=lambda f: f.utc_date,
        )
        for no, fx in zip(numbers, api):
            mapping[no] = fx
    return mapping


# ---------------------------------------------------------------------------
# Simulação principal
# ---------------------------------------------------------------------------

def simulate_tournament(fixtures, ratings, mu, *, max_goals: int = 8) -> TournamentResult:
    """Simula o torneio completo: fase de grupos + chaveamento até a final.

    Usa placar real se o jogo já foi disputado (status FINISHED), senão prevê
    via ``predict_scoreline``. Os jogos do mata-mata são iterados em ordem
    crescente de número (73→104) para garantir que dependências ``WM``/``LM``
    já estejam resolvidas. PRD §4.
    """
    members = _group_members(fixtures)
    scorelines = _group_scorelines(fixtures, ratings, mu, max_goals)

    tables = {g: compute_group_table(members[g], scorelines[g]) for g in GROUPS}
    groups = [GroupResult(g, tables[g]) for g in GROUPS]

    winner_of = {g: tables[g][0].team for g in GROUPS}
    runner_of = {g: tables[g][1].team for g in GROUPS}

    best_thirds = rank_third_places([(g, tables[g][2]) for g in GROUPS])
    third_key = "".join(sorted(g for g, _ in best_thirds))
    alloc = BEST_THIRD_ALLOCATION[third_key]  # {grupo do 1º: grupo do 3º}

    api_ko = _api_knockout_by_match(fixtures)
    results: dict[int, KnockoutResult] = {}

    def resolve(slot) -> str:
        tag, val = slot
        if tag == "W":
            return winner_of[val]
        if tag == "R":
            return runner_of[val]
        if tag == "3":
            return tables[alloc[val]][2].team
        if tag == "WM":
            return results[val].winner
        if tag == "LM":
            return results[val].loser
        raise ValueError(f"slot de chaveamento desconhecido: {slot}")

    for no in sorted(MATCHES):
        slot_a, slot_b = MATCHES[no]
        home, away = resolve(slot_a), resolve(slot_b)
        fx = api_ko.get(no)
        if fx and fx.status == "FINISHED" and fx.home_goals is not None and fx.home:
            home, away = fx.home, fx.away
            gh, ga = fx.home_goals, fx.away_goals
            winner = home if fx.winner == "HOME_TEAM" else away
            penalties = fx.winner not in ("HOME_TEAM", "AWAY_TEAM") and gh == ga
            real = True
        else:
            pred = predict_scoreline(home, away, ratings, mu, max_goals=max_goals)
            gh, ga = pred.palpite
            winner, penalties = knockout_winner(pred)
            real = False
        loser = away if winner == home else home
        results[no] = KnockoutResult(no, STAGE_OF[no], home, away, gh, ga,
                                     winner, loser, real, penalties)

    knockout = [results[no] for no in sorted(results)]
    return TournamentResult(groups, knockout, third_key)
