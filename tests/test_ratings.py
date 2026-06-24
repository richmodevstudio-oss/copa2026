"""Testes para ratings.py — força global e previsão de placar."""

from copa2026.data_source import SyntheticDataSource
from copa2026.models import TeamRatings
from copa2026.ratings import (
    compute_global_ratings,
    knockout_winner,
    predict_scoreline,
)


def _ratings():
    return {"Brazil": TeamRatings(1.6, 0.7), "Chile": TeamRatings(0.8, 1.4)}


def test_predict_scoreline_favors_stronger_team():
    pred = predict_scoreline("Brazil", "Chile", _ratings(), mu=1.3)
    assert pred.lambda_home > pred.lambda_away
    assert pred.palpite[0] >= pred.palpite[1]


def test_knockout_winner_from_decisive_palpite():
    pred = predict_scoreline("Brazil", "Chile", _ratings(), mu=1.3)
    winner, penalties = knockout_winner(pred)
    assert winner == "Brazil"
    assert penalties is False


def test_knockout_winner_draw_resolved_by_lambda_with_penalties():
    # palpite empatado com lambdas diferentes -> desempata por lambda
    # Home "A" tem lambda maior (1.3 > 1.0), então avança
    from copa2026.ratings import ScorePrediction
    pred = ScorePrediction(
        home="A",
        away="B",
        palpite=(1, 1),  # empate
        lambda_home=1.3,  # home lambda mais alto
        lambda_away=1.0,  # away lambda mais baixo
        home_ratings=TeamRatings(1.2, 0.9),
        away_ratings=TeamRatings(1.2, 0.9),
    )
    winner, penalties = knockout_winner(pred)
    assert winner == "A"
    assert penalties is True


def test_knockout_winner_draw_resolved_by_quality_when_lambda_ties():
    # palpite empatado com lambdas iguais -> desempata por qualidade
    # Away "B" tem qualidade maior (1.875 > 0.833), então avança
    from copa2026.ratings import ScorePrediction
    pred = ScorePrediction(
        home="A",
        away="B",
        palpite=(0, 0),  # empate
        lambda_home=1.1,  # lambdas iguais
        lambda_away=1.1,
        home_ratings=TeamRatings(1.0, 1.2),  # qualidade = 1.0/1.2 ≈ 0.833
        away_ratings=TeamRatings(1.5, 0.8),  # qualidade = 1.5/0.8 = 1.875
    )
    winner, penalties = knockout_winner(pred)
    assert winner == "B"
    assert penalties is True


def test_unknown_team_uses_neutral_rating():
    pred = predict_scoreline("Brazil", "Narnia", _ratings(), mu=1.3)
    assert pred.away_ratings == TeamRatings(1.0, 1.0)


def test_compute_global_ratings_covers_played_teams():
    ratings, mu = compute_global_ratings(SyntheticDataSource(seed=1), days=120)
    assert mu > 0
    assert len(ratings) > 30           # maioria das seleções tem histórico
    assert all(r.attack > 0 and r.defense > 0 for r in ratings.values())
