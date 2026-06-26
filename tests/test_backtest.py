from datetime import date

import numpy as np

from copa2026.backtest import outcome_probabilities, ratings_asof, walk_forward_backtest, GameBacktest
from copa2026.models import Match
from copa2026.tournament import FixtureMatch


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


def _fx(home, away, gh, ga, dia):
    return FixtureMatch("GROUP_STAGE", "GROUP_A", home, away, gh, ga,
                        "FINISHED", None, f"2026-{dia}T18:00:00Z")


def _base_forte_fraca():
    # Brazil claramente mais forte que Bolivia no histórico pré-Copa.
    from copa2026.models import Match
    from datetime import date
    jogos = []
    for k in range(6):
        jogos.append(Match("Brazil", "Bolivia", 3, 0, date(2026, 5, 10 + k)))
        jogos.append(Match("France", "Bolivia", 2, 0, date(2026, 5, 10 + k)))
        jogos.append(Match("Brazil", "France", 1, 1, date(2026, 5, 10 + k)))
    return jogos


def test_walk_forward_hitrate_and_fields():
    base = _base_forte_fraca()
    jogos = [_fx("Brazil", "Bolivia", 2, 0, "06-12"),   # casa vence (previsível)
             _fx("Bolivia", "Brazil", 0, 3, "06-15")]   # fora vence
    res = walk_forward_backtest(jogos, base)
    assert res.total == 2
    assert res.empates == 0
    assert res.decididos == 2
    assert res.confianca == res.acertos / res.decididos
    assert res.jogos[0].previsto == "CASA" and res.jogos[0].real == "CASA"
    assert res.jogos[0].acertou is True
    # soma das probabilidades ~ 1
    g = res.jogos[0]
    assert abs((g.p_home + g.p_draw + g.p_away) - 1.0) < 1e-9


def test_walk_forward_exclui_empates_reais():
    # Empates reais não entram no denominador da confiança (o método quase nunca
    # prevê empate); ainda assim aparecem na tabela jogo-a-jogo.
    base = _base_forte_fraca()
    jogos = [_fx("Brazil", "Bolivia", 2, 0, "06-12"),   # decidido
             _fx("Brazil", "France", 1, 1, "06-15")]    # EMPATE real -> excluído
    res = walk_forward_backtest(jogos, base)
    assert res.total == 2          # ambos contam na tabela
    assert res.empates == 1
    assert res.decididos == 1      # só o jogo decidido entra na confiança
    assert res.confianca == res.acertos / res.decididos
    assert any(j.real == "EMPATE" for j in res.jogos)


def test_walk_forward_has_no_lookahead():
    base = _base_forte_fraca()
    g1 = _fx("Brazil", "Bolivia", 2, 0, "06-12")
    g2 = _fx("Bolivia", "France", 0, 1, "06-14")
    g3 = _fx("Brazil", "France", 2, 1, "06-18")
    # a previsão de g1/g2 não pode depender de jogos posteriores
    sem_g3 = walk_forward_backtest([g1, g2], base).jogos
    com_g3 = walk_forward_backtest([g1, g2, g3], base).jogos
    assert sem_g3 == com_g3[:2]


def test_walk_forward_skips_games_without_base():
    base = _base_forte_fraca()
    # jogo muito depois -> janela ainda tem base; jogo de seleções sem história
    # ainda é previsto (rating neutro), então total conta os FINISHED com janela.
    jogos = [_fx("Brazil", "Bolivia", 1, 0, "06-12")]
    res = walk_forward_backtest(jogos, base)
    assert res.total == 1
