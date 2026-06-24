from copa2026.bracket_data import GROUPS, STAGE_OF
from copa2026.models import TeamRatings
from copa2026.tournament import FixtureMatch, finished_results, knockout_rows, parse_fixtures, simulate_tournament


SAMPLE = {
    "matches": [
        {
            "stage": "GROUP_STAGE", "group": "GROUP_A", "status": "FINISHED",
            "utcDate": "2026-06-11T20:00:00Z",
            "homeTeam": {"name": "Mexico"}, "awayTeam": {"name": "South Africa"},
            "score": {"winner": "HOME_TEAM", "duration": "REGULAR",
                      "fullTime": {"home": 2, "away": 0}},
        },
        {
            "stage": "LAST_32", "group": None, "status": "TIMED",
            "utcDate": "2026-06-28T19:00:00Z",
            "homeTeam": {"name": None}, "awayTeam": {"name": None},
            "score": {"winner": None, "duration": "REGULAR",
                      "fullTime": {"home": None, "away": None}},
        },
    ]
}


def test_parse_fixtures_group_match():
    fx = parse_fixtures(SAMPLE)
    g = fx[0]
    assert isinstance(g, FixtureMatch)
    assert g.stage == "GROUP_STAGE" and g.group == "GROUP_A"
    assert g.home == "Mexico" and g.away == "South Africa"
    assert g.home_goals == 2 and g.away_goals == 0
    assert g.status == "FINISHED" and g.winner == "HOME_TEAM"


def test_parse_fixtures_keeps_unresolved_knockout():
    fx = parse_fixtures(SAMPLE)
    ko = fx[1]
    assert ko.stage == "LAST_32"
    assert ko.home is None and ko.away is None
    assert ko.home_goals is None and ko.status == "TIMED"


# ---------------------------------------------------------------------------
# Helpers para testes de simulate_tournament
# ---------------------------------------------------------------------------

def _group_fixtures(all_finished=False, results=None):
    """Gera os 72 jogos de grupo (todos os pares dentro de cada grupo)."""
    teams = {g: [f"{g}{i}" for i in range(1, 5)] for g in GROUPS}
    fx = []
    for g, ts in teams.items():
        for i in range(4):
            for j in range(i + 1, 4):
                h, a = ts[i], ts[j]
                gh = ga = None
                status = "TIMED"
                if all_finished:
                    gh, ga = (results or {}).get((h, a), (1, 0))
                    status = "FINISHED"
                fx.append(_fx("GROUP_STAGE", f"GROUP_{g}", h, a, gh, ga, status))
    return fx, teams


def _fx(stage, group, home, away, gh, ga, status, utc="2026-06-15T00:00:00Z"):
    winner = None
    if status == "FINISHED" and gh is not None:
        winner = "HOME_TEAM" if gh > ga else "AWAY_TEAM" if ga > gh else "DRAW"
    return FixtureMatch(stage, group, home, away, gh, ga, status, winner, utc)


def _ko_placeholders():
    fx = []
    for no in range(73, 105):
        fx.append(_fx(STAGE_OF[no], None, None, None, None, None, "TIMED",
                      utc=f"2026-06-28T{no % 24:02d}:00:00Z"))
    return fx


def _ratings_by_group(teams):
    # 1º de cada grupo mais forte; força decrescente por índice
    r = {}
    for g, ts in teams.items():
        for k, t in enumerate(ts):
            r[t] = TeamRatings(attack=1.6 - 0.2 * k, defense=0.7 + 0.2 * k)
    return r


# ---------------------------------------------------------------------------
# Testes de simulate_tournament
# ---------------------------------------------------------------------------

def test_simulate_fills_full_bracket_to_final():
    gfx, teams = _group_fixtures()
    fixtures = gfx + _ko_placeholders()
    res = simulate_tournament(fixtures, _ratings_by_group(teams), mu=1.3)
    assert len(res.groups) == 12
    assert {k.match_no for k in res.knockout} == set(range(73, 105))
    final = next(k for k in res.knockout if k.match_no == 104)
    assert final.winner and final.winner != final.loser
    assert all(not k.real for k in res.knockout)     # nada disputado ainda


def test_real_group_result_overrides_prediction():
    # força o 4º colocado teórico a vencer todos -> vira 1º real
    teams = {g: [f"{g}{i}" for i in range(1, 5)] for g in GROUPS}
    results = {}
    for g, ts in teams.items():
        for i in range(4):
            for j in range(i + 1, 4):
                # time de maior índice vence sempre
                results[(ts[i], ts[j])] = (0, 3)
    gfx, teams = _group_fixtures(all_finished=True, results=results)
    res = simulate_tournament(gfx + _ko_placeholders(), _ratings_by_group(teams), mu=1.3)
    a = next(gr for gr in res.groups if gr.group == "A")
    assert a.table[0].team == "A4"     # resultado real prevalece sobre a força


def test_real_knockout_result_is_marked_and_propagated():
    gfx, teams = _group_fixtures()
    ko = []
    for no in range(73, 105):
        if no == 73:
            ko.append(_fx("LAST_32", None, "X", "Y", 1, 0, "FINISHED",
                          utc="2026-06-28T00:00:00Z"))
        else:
            ko.append(_fx(STAGE_OF[no], None, None, None, None, None, "TIMED",
                          utc=f"2026-06-29T{no % 24:02d}:00:00Z"))
    res = simulate_tournament(gfx + ko, _ratings_by_group(teams), mu=1.3)
    m73 = next(k for k in res.knockout if k.match_no == 73)
    assert m73.real is True
    assert m73.winner == "X"
    m90 = next(k for k in res.knockout if k.match_no == 90)
    assert m90.home == "X"      # vencedor real do jogo 73 propaga para o jogo 90


# ---------------------------------------------------------------------------
# Testes para finished_results
# ---------------------------------------------------------------------------

def test_finished_results_returns_only_finished_matches():
    fixtures = [
        FixtureMatch(
            stage="GROUP_STAGE", group="GROUP_A",
            home="Brazil", away="Mexico",
            home_goals=2, away_goals=1,
            status="FINISHED", winner="HOME_TEAM",
            utc_date="2026-06-15T20:00:00Z",
        ),
        FixtureMatch(
            stage="LAST_32", group=None,
            home=None, away=None,
            home_goals=None, away_goals=None,
            status="TIMED", winner=None,
            utc_date="2026-06-28T19:00:00Z",
        ),
    ]
    result = finished_results(fixtures)
    assert len(result) == 1
    assert result[0] == ("2026-06-15", "Brazil", "Mexico", 2, 1)


# ---------------------------------------------------------------------------
# Teste para _knockout_rows (função pura de app.py)
# ---------------------------------------------------------------------------

def test_knockout_rows_groups_by_stage_label():
    gfx, teams = _group_fixtures()
    res = simulate_tournament(gfx + _ko_placeholders(), _ratings_by_group(teams), mu=1.3)
    rows = knockout_rows(res)
    assert "Final" in rows
    assert len(rows["16 avos de final"]) == 16
    linha = rows["Final"][0]
    assert {"Jogo", "Placar", "Origem"} <= set(linha)
