"""Orquestração das quatro etapas do algoritmo (PRD Seção 4.5)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data_source import MatchDataSource
from .models import Match, TeamRatings
from .optimizer import best_guess
from .prediction import expected_goals, score_matrix
from .strength import compute_ratings, league_mu
from .teams import WORLD_CUP_2026_TEAMS_SET

Placar = tuple[int, int]


@dataclass
class MatchPrediction:
    """Resultado completo da previsão de uma partida."""

    home: str
    away: str
    home_ratings: TeamRatings
    away_ratings: TeamRatings
    lambda_home: float
    lambda_away: float
    mu: float
    prob_matrix: np.ndarray
    palpite: Placar
    expected_points: float
    history: list[Match]
    home_matches: int
    away_matches: int

    @property
    def low_confidence(self) -> bool:
        """Indica histórico escasso demais para uma previsão confiável."""
        return min(self.home_matches, self.away_matches) < 3


def predict_match(
    home: str,
    away: str,
    source: MatchDataSource,
    *,
    wc_teams=WORLD_CUP_2026_TEAMS_SET,
    days: int = 90,
    max_goals: int = 8,
    reg: float = 2.0,
) -> MatchPrediction:
    """Executa coleta -> força -> previsão -> otimização para ``home`` x ``away``."""
    # Etapa 1: coleta (histórico combinado, sem duplicatas).
    history = list(
        dict.fromkeys(
            source.recent_matches(home, days) + source.recent_matches(away, days)
        )
    )
    if not history:
        raise ValueError("Sem histórico de partidas para os times selecionados.")

    # Etapa 2: força. Times sem histórico recebem rating neutro (1, 1) — o
    # limite do encolhimento — em vez de inviabilizar a previsão.
    mu = league_mu(history)
    ratings = compute_ratings(history, wc_teams, reg=reg)
    neutro = TeamRatings(1.0, 1.0)
    home_ratings = ratings.get(home, neutro)
    away_ratings = ratings.get(away, neutro)

    home_matches = sum(1 for m in history if home in (m.home, m.away))
    away_matches = sum(1 for m in history if away in (m.home, m.away))

    # Etapa 3: gols esperados e matriz de placares.
    lambda_home, lambda_away = expected_goals(home_ratings, away_ratings, mu)
    prob_matrix = score_matrix(lambda_home, lambda_away, max_goals)

    # Etapa 4: palpite ótimo.
    palpite, exp_points = best_guess(prob_matrix)

    return MatchPrediction(
        home=home,
        away=away,
        home_ratings=home_ratings,
        away_ratings=away_ratings,
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        mu=mu,
        prob_matrix=prob_matrix,
        palpite=palpite,
        expected_points=exp_points,
        history=history,
        home_matches=home_matches,
        away_matches=away_matches,
    )
