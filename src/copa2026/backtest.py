"""Verificação regressiva (backtest walk-forward) do previsor.

Para cada jogo já disputado, prevê o resultado (Vitória casa / Empate / Vitória
fora) usando apenas dados anteriores ao jogo e compara com o real. O grau de
confiança empírico é a taxa de acerto. Probabilidades de resultado vêm da matriz
de placares de Poisson (PRD §4.3); aqui não importa o placar exato.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from .models import Match, TeamRatings
from .prediction import expected_goals, score_matrix
from .strength import compute_ratings, league_mu
from .teams import WORLD_CUP_2026_TEAMS_SET
from .tournament import FixtureMatch


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


_LABELS = ("CASA", "EMPATE", "FORA")
_NEUTRO = TeamRatings(1.0, 1.0)


@dataclass(frozen=True)
class GameBacktest:
    played_on: date
    home: str
    away: str
    p_home: float
    p_draw: float
    p_away: float
    previsto: str
    real: str
    acertou: bool


@dataclass(frozen=True)
class BacktestResult:
    jogos: list
    acertos: int
    total: int
    confianca: float


def _resultado(gh: int, ga: int) -> str:
    if gh > ga:
        return "CASA"
    if gh < ga:
        return "FORA"
    return "EMPATE"


def walk_forward_backtest(
    jogos_copa: list[FixtureMatch],
    partidas_base: list[Match],
    *,
    janela: int = 90,
    reg: float = 2.0,
) -> BacktestResult:
    """Backtest sem lookahead: prevê cada jogo real com dados anteriores a ele."""
    reais = sorted(
        (f for f in jogos_copa
         if f.status == "FINISHED" and f.home and f.away
         and f.home_goals is not None and f.away_goals is not None),
        key=lambda f: f.utc_date,
    )
    copa_matches = [
        Match(f.home, f.away, f.home_goals, f.away_goals,
              date.fromisoformat(f.utc_date[:10]))
        for f in reais
    ]

    jogos: list[GameBacktest] = []
    for i, f in enumerate(reais):
        d = date.fromisoformat(f.utc_date[:10])
        base = partidas_base + [m for m in copa_matches if m.played_on < d]
        try:
            ratings, mu = ratings_asof(d, base, janela=janela, reg=reg)
        except ValueError:
            continue
        hr = ratings.get(f.home, _NEUTRO)
        ar = ratings.get(f.away, _NEUTRO)
        lambda_home, lambda_away = expected_goals(hr, ar, mu)
        matrix = score_matrix(lambda_home, lambda_away)
        p_home, p_draw, p_away = outcome_probabilities(matrix)
        # Normalize probabilities to sum to 1.0
        total_prob = p_home + p_draw + p_away
        p_home /= total_prob
        p_draw /= total_prob
        p_away /= total_prob
        previsto = _LABELS[int(np.argmax((p_home, p_draw, p_away)))]
        real = _resultado(f.home_goals, f.away_goals)
        jogos.append(GameBacktest(d, f.home, f.away, p_home, p_draw, p_away,
                                  previsto, real, previsto == real))

    acertos = sum(1 for j in jogos if j.acertou)
    total = len(jogos)
    confianca = acertos / total if total else 0.0
    return BacktestResult(jogos, acertos, total, confianca)
