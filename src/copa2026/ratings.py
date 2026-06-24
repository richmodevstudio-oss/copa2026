"""Força global das 48 seleções e previsão de placar para simulações em lote.

Diferente de ``pipeline.predict_match`` (que recalcula a força por par de times),
aqui a força é calculada **uma única vez** sobre o histórico de todas as
seleções, permitindo prever as ~100 partidas do torneio sem repetir rede ou
otimização. PRD Seções 4.2–4.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain

from .data_source import MatchDataSource
from .models import TeamRatings
from .optimizer import best_guess
from .prediction import expected_goals, score_matrix
from .strength import compute_ratings, league_mu
from .teams import WORLD_CUP_2026_TEAMS, WORLD_CUP_2026_TEAMS_SET

_NEUTRO = TeamRatings(1.0, 1.0)


def compute_global_ratings(
    source: MatchDataSource,
    *,
    teams=WORLD_CUP_2026_TEAMS,
    days: int = 90,
    reg: float = 2.0,
) -> tuple[dict[str, TeamRatings], float]:
    """Coleta o histórico de todas as seleções e calcula força + mu uma vez."""
    history = list(
        dict.fromkeys(
            chain.from_iterable(source.recent_matches(t, days) for t in teams)
        )
    )
    if not history:
        raise ValueError("Sem histórico de partidas para calcular a força.")
    mu = league_mu(history)
    ratings = compute_ratings(history, WORLD_CUP_2026_TEAMS_SET, reg=reg)
    return ratings, mu


@dataclass(frozen=True)
class ScorePrediction:
    home: str
    away: str
    palpite: tuple[int, int]
    lambda_home: float
    lambda_away: float
    home_ratings: TeamRatings
    away_ratings: TeamRatings


def predict_scoreline(
    home: str,
    away: str,
    ratings: dict[str, TeamRatings],
    mu: float,
    *,
    max_goals: int = 8,
) -> ScorePrediction:
    """Palpite ótimo (max pontos esperados) a partir de ratings já calculados."""
    hr = ratings.get(home, _NEUTRO)
    ar = ratings.get(away, _NEUTRO)
    lambda_home, lambda_away = expected_goals(hr, ar, mu)
    matrix = score_matrix(lambda_home, lambda_away, max_goals)
    palpite, _ = best_guess(matrix)
    return ScorePrediction(home, away, palpite, lambda_home, lambda_away, hr, ar)


def _quality(r: TeamRatings) -> float:
    """Qualidade escalar p/ desempatar quem avança (ataque sobre fragilidade)."""
    return r.attack / r.defense if r.defense else r.attack


def knockout_winner(pred: ScorePrediction) -> tuple[str, bool]:
    """Time que avança e se a decisão foi nos pênaltis (palpite empatado).

    Palpite com vencedor -> avança quem marcou mais (sem pênaltis). Palpite
    empatado -> avança o de maior lambda; se lambda empatar, o de maior
    qualidade; rótulo 'pênaltis'.
    """
    gh, ga = pred.palpite
    if gh != ga:
        return (pred.home if gh > ga else pred.away), False
    if pred.lambda_home != pred.lambda_away:
        return (pred.home if pred.lambda_home > pred.lambda_away else pred.away), True
    if _quality(pred.home_ratings) >= _quality(pred.away_ratings):
        return pred.home, True
    return pred.away, True
