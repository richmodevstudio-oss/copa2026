"""Otimização do palpite (PRD Seção 4.4).

Dado o palpite, calcula-se o valor esperado de pontos sobre toda a matriz de
probabilidades de placares. O palpite ótimo é aquele que maximiza esse valor
esperado — avaliando a grade completa de placares plausíveis, e não apenas a
janela em torno dos gols esperados.
"""

from __future__ import annotations

import numpy as np

from .scoring import score

Placar = tuple[int, int]


def expected_points(palpite: Placar, prob_matrix: np.ndarray) -> float:
    """Valor esperado de pontos do ``palpite`` sobre a matriz de placares."""
    total = 0.0
    n_home, n_away = prob_matrix.shape
    for x in range(n_home):
        for y in range(n_away):
            p = prob_matrix[x, y]
            if p:
                total += p * score(palpite, (x, y))
    return total


def best_guess(prob_matrix: np.ndarray) -> tuple[Placar, float]:
    """Palpite que maximiza os pontos esperados e o valor esperado obtido."""
    n_home, n_away = prob_matrix.shape
    melhor: Placar = (0, 0)
    melhor_pontos = -1.0
    for px in range(n_home):
        for py in range(n_away):
            pontos = expected_points((px, py), prob_matrix)
            if pontos > melhor_pontos:
                melhor_pontos = pontos
                melhor = (px, py)
    return melhor, melhor_pontos
