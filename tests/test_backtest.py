from datetime import date

import numpy as np

from copa2026.backtest import outcome_probabilities, ratings_asof
from copa2026.models import Match


def test_outcome_probabilities_buckets_and_sum():
    # P[x,y], x=gols casa (linha). Massa: (2,0)=casa, (1,1)=empate, (0,2)=fora.
    m = np.zeros((3, 3))
    m[2, 0] = 0.5   # casa vence
    m[1, 1] = 0.3   # empate
    m[0, 2] = 0.2   # fora vence
    p_casa, p_empate, p_fora = outcome_probabilities(m)
    assert abs(p_casa - 0.5) < 1e-9
    assert abs(p_empate - 0.3) < 1e-9
    assert abs(p_fora - 0.2) < 1e-9
    assert abs((p_casa + p_empate + p_fora) - 1.0) < 1e-9


def _amistosos(n, d):
    # n jogos no mesmo dia d entre seleções da Copa, com placares variados.
    jogos = []
    times = ["Brazil", "France", "Spain", "England"]
    for i in range(n):
        h, a = times[i % 4], times[(i + 1) % 4]
        jogos.append(Match(h, a, (i % 3) + 1, i % 2, d))
    return jogos


def test_ratings_asof_ignores_future_matches():
    corte = date(2026, 6, 1)
    passado = _amistosos(8, date(2026, 5, 1))
    futuro = [Match("Brazil", "Spain", 5, 0, date(2026, 6, 2))]  # após o corte
    r1, mu1 = ratings_asof(corte, passado)
    r2, mu2 = ratings_asof(corte, passado + futuro)
    assert mu1 == mu2
    assert r1 == r2


def test_ratings_asof_empty_window_raises():
    corte = date(2026, 6, 1)
    antigo = _amistosos(4, date(2026, 1, 1))  # fora da janela de 90 dias
    try:
        ratings_asof(corte, antigo)
        assert False, "esperava ValueError"
    except ValueError:
        pass
