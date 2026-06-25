"""Probabilidade de cada seleção ser campeã, por programação dinâmica sobre o
chaveamento (PRD §9 + §4.3).

Para cada jogo do mata-mata, a probabilidade de um time vencer é somada sobre a
distribuição de possíveis adversários (cada um ponderado pela sua probabilidade
de chegar àquele jogo). Empate no tempo normal é decidido nos pênaltis como
moeda justa (½ para cada lado).
"""

from __future__ import annotations

from .backtest import outcome_probabilities
from .bracket_data import MATCHES, STAGE_OF
from .models import TeamRatings
from .prediction import expected_goals, score_matrix

_NEUTRO = TeamRatings(1.0, 1.0)

_ROTULO = {
    "LAST_32": "R32",
    "LAST_16": "R16",
    "QUARTER_FINALS": "QF",
    "SEMI_FINALS": "SF",
    "FINAL": "Final",
}


def prob_vitoria(a: str, b: str, ratings: dict, mu: float, *, max_goals: int = 8) -> float:
    """P(``a`` avança contra ``b``) = P(a vence) + ½·P(empate)."""
    ra = ratings.get(a, _NEUTRO)
    rb = ratings.get(b, _NEUTRO)
    lambda_a, lambda_b = expected_goals(ra, rb, mu)
    matrix = score_matrix(lambda_a, lambda_b, max_goals)
    p_a, p_empate, _ = outcome_probabilities(matrix)
    return p_a + 0.5 * p_empate


def probabilidades_titulo(
    confrontos_r32: dict[int, tuple[str, str]],
    ratings: dict,
    mu: float,
    *,
    matches: dict = MATCHES,
    final: int = 104,
    stage_of: dict = STAGE_OF,
    max_goals: int = 8,
) -> dict[str, dict[str, float]]:
    """Probabilidade de cada time vencer cada rodada e ser campeão.

    ``confrontos_r32`` mapeia os jogos-folha (R32) aos dois times determinados.
    Os demais jogos referenciam vencedores via slots ``("WM", n)``.
    """
    win_dist: dict[int, dict[str, float]] = {}

    for no in sorted(m for m in matches if m != 103 and m <= final):
        if no in confrontos_r32:
            ta, tb = confrontos_r32[no]
            home_side = {ta: 1.0}
            away_side = {tb: 1.0}
        else:
            (_, na), (_, nb) = matches[no]
            home_side = win_dist[na]
            away_side = win_dist[nb]

        dist: dict[str, float] = {}
        for t, pr in home_side.items():
            s = sum(po * prob_vitoria(t, o, ratings, mu, max_goals=max_goals)
                    for o, po in away_side.items())
            dist[t] = pr * s
        for t, pr in away_side.items():
            s = sum(po * prob_vitoria(t, o, ratings, mu, max_goals=max_goals)
                    for o, po in home_side.items())
            dist[t] = pr * s
        win_dist[no] = dist

    por_time: dict[str, dict[str, float]] = {}
    for no, dist in win_dist.items():
        if no == final:
            continue
        rotulo = _ROTULO.get(stage_of.get(no), str(no))
        for t, p in dist.items():
            por_time.setdefault(t, {})[rotulo] = p
    for t, p in win_dist[final].items():
        por_time.setdefault(t, {})["CAMPEAO"] = p
    return por_time
