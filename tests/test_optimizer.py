"""Testes da otimização do palpite (PRD Seção 4.4)."""

import numpy as np
import pytest

from copa2026.optimizer import best_guess, expected_points


def _matriz_degenerada(x, y, n=6):
    """Matriz com toda a probabilidade concentrada no placar (x, y)."""
    m = np.zeros((n, n))
    m[x, y] = 1.0
    return m


def test_expected_points_em_distribuicao_degenerada_e_a_pontuacao_do_placar():
    m = _matriz_degenerada(2, 1)
    # palpite exato -> 8
    assert expected_points((2, 1), m) == pytest.approx(8.0)
    # acerta vencedor e diferença, não o placar -> 5
    assert expected_points((1, 0), m) == pytest.approx(5.0)
    # erra o resultado -> 0
    assert expected_points((0, 1), m) == pytest.approx(0.0)


def test_expected_points_e_media_ponderada():
    m = np.zeros((4, 4))
    m[2, 1] = 0.5  # palpite (2,1): 8 pontos
    m[0, 0] = 0.5  # palpite (2,1) vs (0,0): resultado errado -> 0
    assert expected_points((2, 1), m) == pytest.approx(0.5 * 8 + 0.5 * 0)


def test_best_guess_em_distribuicao_degenerada_acerta_o_placar_exato():
    m = _matriz_degenerada(3, 1)
    palpite, pontos = best_guess(m)
    assert palpite == (3, 1)
    assert pontos == pytest.approx(8.0)


def test_best_guess_e_consistente_com_expected_points():
    rng = np.random.default_rng(42)
    m = rng.random((6, 6))
    m /= m.sum()
    palpite, pontos = best_guess(m)
    assert expected_points(palpite, m) == pytest.approx(pontos)


def test_best_guess_nao_e_pior_que_o_placar_mais_provavel():
    rng = np.random.default_rng(7)
    m = rng.random((6, 6))
    m /= m.sum()

    placar_modal = tuple(int(i) for i in np.unravel_index(m.argmax(), m.shape))
    _, pontos_otimos = best_guess(m)

    assert pontos_otimos >= expected_points(placar_modal, m) - 1e-9
