"""Previsão de gols via distribuição de Poisson (PRD Seção 4.3).

A partir dos ratings de força das duas seleções, estima os gols esperados de
cada lado e constrói a matriz de probabilidades de cada placar, assumindo dois
processos de Poisson independentes.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import poisson

from .models import TeamRatings


def expected_goals(
    home: TeamRatings, away: TeamRatings, mu: float
) -> tuple[float, float]:
    """Gols esperados (lambda) do mandante e do visitante.

    lambda_mandante = mu * O_mandante * D_visitante
    lambda_visitante = mu * O_visitante * D_mandante
    """
    lambda_home = mu * home.attack * away.defense
    lambda_away = mu * away.attack * home.defense
    return lambda_home, lambda_away


def score_matrix(
    lambda_home: float, lambda_away: float, max_goals: int = 8
) -> np.ndarray:
    """Matriz ``P`` em que ``P[x, y]`` é a probabilidade do placar x-y.

    ``x`` indexa os gols do mandante e ``y`` os do visitante, de 0 a
    ``max_goals``. Sob independência, ``P[x, y] = P(home=x) * P(away=y)``.
    """
    goals = np.arange(max_goals + 1)
    p_home = poisson.pmf(goals, lambda_home)
    p_away = poisson.pmf(goals, lambda_away)
    return np.outer(p_home, p_away)
