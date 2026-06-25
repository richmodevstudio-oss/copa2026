"""Verificação regressiva (backtest walk-forward) do previsor.

Para cada jogo já disputado, prevê o resultado (Vitória casa / Empate / Vitória
fora) usando apenas dados anteriores ao jogo e compara com o real. O grau de
confiança empírico é a taxa de acerto. Probabilidades de resultado vêm da matriz
de placares de Poisson (PRD §4.3); aqui não importa o placar exato.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from .models import Match
from .strength import compute_ratings, league_mu
from .teams import WORLD_CUP_2026_TEAMS_SET


def outcome_probabilities(matrix: np.ndarray) -> tuple[float, float, float]:
    """(p_casa, p_empate, p_fora) somando a matriz de placares por região.

    ``P[x, y]`` com ``x`` = gols da casa (linha): casa vence abaixo da diagonal,
    empate na diagonal, fora vence acima.
    """
    p_empate = float(np.trace(matrix))
    p_casa = float(np.tril(matrix, -1).sum())
    p_fora = float(np.triu(matrix, 1).sum())
    return p_casa, p_empate, p_fora


def ratings_asof(
    corte: date,
    partidas: list[Match],
    *,
    janela: int = 90,
    reg: float = 2.0,
) -> tuple[dict, float]:
    """Força (ataque/defesa) e mu calculados com a janela ``[corte-janela, corte)``.

    Função pura: depende só de ``corte`` e ``partidas`` (sem ``date.today()``),
    o que torna o backtest walk-forward isento de viés de futuro.
    """
    inicio = corte - timedelta(days=janela)
    janela_partidas = [
        m for m in partidas
        if m.played_on is not None and inicio <= m.played_on < corte
    ]
    if not janela_partidas:
        raise ValueError(f"janela vazia até {corte.isoformat()}")
    mu = league_mu(janela_partidas)
    ratings = compute_ratings(janela_partidas, WORLD_CUP_2026_TEAMS_SET, reg=reg)
    return ratings, mu
