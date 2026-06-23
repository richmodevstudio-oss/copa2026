"""Teste de integração do pipeline (as quatro etapas juntas)."""

from datetime import date

import numpy as np

from copa2026.data_source import SyntheticDataSource
from copa2026.models import Match, TeamRatings
from copa2026.pipeline import predict_match


class _OneTeamSource:
    """Fonte em que só o Brasil tem histórico (simula plano gratuito esparso)."""

    def recent_matches(self, team, days=90):
        if team == "Brazil":
            return [Match("Brazil", "Morocco", 1, 1, date(2026, 6, 13))]
        return []


def test_predict_match_degrada_com_time_sem_historico():
    pred = predict_match("Brazil", "Argentina", _OneTeamSource())
    # time sem histórico recebe rating neutro em vez de quebrar
    assert pred.away_ratings == TeamRatings(1.0, 1.0)
    assert pred.away_matches == 0
    assert pred.home_matches == 1


def test_predict_match_produz_palpite_coerente():
    source = SyntheticDataSource(seed=2026)
    result = predict_match("Brazil", "Argentina", source)

    # placar com valores não-negativos
    assert result.palpite[0] >= 0 and result.palpite[1] >= 0
    # gols esperados positivos
    assert result.lambda_home > 0 and result.lambda_away > 0
    # matriz de probabilidades válida
    assert np.isclose(result.prob_matrix.sum(), 1.0, atol=1e-2)
    # pontos esperados dentro do intervalo possível (0 a 8)
    assert 0.0 <= result.expected_points <= 8.0
    # histórico não-vazio para ambos
    assert len(result.history) > 0


def test_predict_match_e_deterministico():
    source = SyntheticDataSource(seed=2026)
    r1 = predict_match("France", "Spain", source)
    r2 = predict_match("France", "Spain", source)
    assert r1.palpite == r2.palpite
    assert r1.expected_points == r2.expected_points
