"""Testes do cálculo de força iterativo (PRD Seção 4.2)."""

import pytest

from copa2026.models import Match
from copa2026.strength import compute_ratings, league_mu


def test_league_mu_e_media_de_gols_por_time_por_jogo():
    matches = [Match("A", "B", 1, 1), Match("A", "C", 3, 0)]
    # total de gols = 5, jogos = 2 -> mu = 5 / (2*2) = 1.25
    assert league_mu(matches) == pytest.approx(1.25)


def test_retorna_ratings_para_os_times_da_copa_que_jogaram():
    matches = [Match("A", "B", 1, 1)]
    ratings = compute_ratings(matches, wc_teams={"A", "B", "Z"})
    assert set(ratings) == {"A", "B"}  # Z não jogou, fica de fora


def test_dados_balanceados_convergem_para_um():
    matches = [Match("A", "B", 1, 1)]
    ratings = compute_ratings(matches, wc_teams={"A", "B"})
    assert ratings["A"].attack == pytest.approx(1.0, abs=1e-4)
    assert ratings["A"].defense == pytest.approx(1.0, abs=1e-4)
    assert ratings["B"].attack == pytest.approx(1.0, abs=1e-4)
    assert ratings["B"].defense == pytest.approx(1.0, abs=1e-4)


def test_ponto_fixo_reconstroi_os_gols():
    # No ponto fixo: sum(mu * O_i * D_opp) == gols marcados por i.
    matches = [
        Match("A", "B", 3, 1),
        Match("A", "C", 3, 1),
        Match("B", "C", 2, 1),
    ]
    wc = {"A", "B", "C"}
    mu = league_mu(matches)
    r = compute_ratings(matches, wc_teams=wc)

    gols_marcados = {"A": 0.0, "B": 0.0, "C": 0.0}
    previsto = {"A": 0.0, "B": 0.0, "C": 0.0}
    for m in matches:
        gols_marcados[m.home] += m.home_goals
        gols_marcados[m.away] += m.away_goals
        previsto[m.home] += mu * r[m.home].attack * r[m.away].defense
        previsto[m.away] += mu * r[m.away].attack * r[m.home].defense

    for t in wc:
        assert previsto[t] == pytest.approx(gols_marcados[t], abs=1e-3)


def test_quem_marca_mais_e_sofre_menos_tem_ataque_maior_e_defesa_menor():
    matches = [
        Match("A", "B", 3, 1),
        Match("A", "C", 3, 1),
        Match("B", "C", 2, 1),
    ]
    r = compute_ratings(matches, wc_teams={"A", "B", "C"})
    # A marca mais e sofre menos; C marca menos e sofre mais
    assert r["A"].attack > r["B"].attack > r["C"].attack
    assert r["A"].defense < r["B"].defense < r["C"].defense


def test_regularizacao_encolhe_ratings_para_um():
    # A arrasa todo mundo; sem regularização o ataque dispara.
    matches = [Match("A", "B", 5, 0), Match("A", "C", 5, 0)]
    wc = {"A", "B", "C"}

    r0 = compute_ratings(matches, wc, reg=0.0)
    r2 = compute_ratings(matches, wc, reg=2.0)
    r_big = compute_ratings(matches, wc, reg=1000.0)

    # reg maior aproxima o ataque de A de 1
    assert abs(r2["A"].attack - 1) < abs(r0["A"].attack - 1)
    # reg gigante encolhe tudo para ~1
    assert r_big["A"].attack == pytest.approx(1.0, abs=0.05)
    assert r_big["A"].defense == pytest.approx(1.0, abs=0.05)


def test_adversario_externo_usa_forca_minima():
    # X não está na Copa: usa external_attack/defense fixos.
    matches = [Match("A", "X", 2, 0)]
    r = compute_ratings(
        matches,
        wc_teams={"A"},
        external_attack=0.5,
        external_defense=1.5,
    )
    assert "X" not in r
    # mu = 2/(2*1) = 1 ; O_A = 2 / (mu * D_X=1.5) = 1.3333
    assert r["A"].attack == pytest.approx(2 / (1 * 1.5), abs=1e-4)
    # A não sofreu gols -> defesa tende a 0
    assert r["A"].defense == pytest.approx(0.0, abs=1e-4)
