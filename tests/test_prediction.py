"""Testes da previsão de gols via Poisson (PRD Seção 4.3)."""

import pytest
from scipy.stats import poisson

from copa2026.models import TeamRatings
from copa2026.prediction import expected_goals, score_matrix


def test_expected_goals_usa_ataque_de_um_contra_defesa_do_outro():
    a = TeamRatings(attack=1.5, defense=0.8)
    b = TeamRatings(attack=1.0, defense=1.2)
    mu = 1.3
    la, lb = expected_goals(a, b, mu)
    assert la == pytest.approx(1.3 * 1.5 * 1.2)  # mu * O_a * D_b
    assert lb == pytest.approx(1.3 * 1.0 * 0.8)  # mu * O_b * D_a


def test_score_matrix_tem_forma_correta():
    m = score_matrix(1.5, 1.2, max_goals=6)
    assert m.shape == (7, 7)


def test_score_matrix_soma_aproximadamente_um():
    m = score_matrix(1.5, 1.2, max_goals=12)
    assert m.sum() == pytest.approx(1.0, abs=1e-3)


def test_score_matrix_e_produto_das_marginais():
    la, lb = 1.7, 0.9
    m = score_matrix(la, lb, max_goals=8)
    # célula (2,1) = P(A=2) * P(B=1) sob independência
    esperado = poisson.pmf(2, la) * poisson.pmf(1, lb)
    assert m[2, 1] == pytest.approx(esperado)


def test_placar_mais_provavel_acompanha_os_gols_esperados():
    import numpy as np

    m = score_matrix(2.0, 0.4, max_goals=8)
    x, y = np.unravel_index(m.argmax(), m.shape)
    # com lambda_a alto e lambda_b baixo, placar mais provável favorece o mandante
    assert x > y
