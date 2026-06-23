"""Testes da função de pontuação (PRD Seção 3)."""

from copa2026.scoring import score


def test_resultado_errado_nao_pontua():
    # palpite vitória do mandante, resultado vitória do visitante
    assert score((1, 0), (0, 1)) == 0


def test_acerta_so_o_resultado_rende_3_pontos():
    # mesmo vencedor, mas nenhum critério de bônus coincide
    assert score((5, 1), (2, 0)) == 3


def test_placar_exato_rende_3_mais_5():
    assert score((2, 1), (2, 1)) == 8


def test_acerta_gols_do_vencedor_rende_3_mais_3():
    # mandante vence em ambos; gols do vencedor (2) coincidem; placar não é exato
    assert score((2, 0), (2, 1)) == 6


def test_acerta_diferenca_de_gols_rende_3_mais_2():
    # diferença 2 em ambos; gols do vencedor (3 vs 2) não coincidem
    assert score((3, 1), (2, 0)) == 5


def test_acerta_gols_do_perdedor_rende_3_mais_1():
    # perdedor faz 1 em ambos; vencedor e diferença não coincidem
    assert score((5, 1), (3, 1)) == 4


def test_goleada_em_ambos_rende_3_mais_1():
    # diferença > 3 em ambos, mas diferença exata, vencedor e perdedor diferem
    assert score((6, 1), (8, 2)) == 4


def test_empate_exato_rende_3_mais_5():
    assert score((1, 1), (1, 1)) == 8


def test_empate_correto_sem_placar_exato_rende_3_mais_2():
    # acerta empate; diferença (0) coincide; placar não exato
    assert score((0, 0), (2, 2)) == 5


def test_vale_o_maior_bonus():
    # placar exato implica vários critérios, mas só conta o maior (+5)
    assert score((3, 0), (3, 0)) == 8
