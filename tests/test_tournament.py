from copa2026.tournament import FixtureMatch, parse_fixtures


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
