from copa2026.standings import TeamRecord, compute_group_table, rank_third_places


def test_table_orders_by_points_then_goal_diff():
    teams = ["A", "B", "C", "D"]
    matches = [
        ("A", "B", 2, 0), ("C", "D", 1, 1),
        ("A", "C", 1, 0), ("B", "D", 0, 0),
        ("A", "D", 3, 0), ("B", "C", 1, 1),
    ]
    table = compute_group_table(teams, matches)
    assert [r.team for r in table][0] == "A"      # 9 pts
    assert table[0].points == 9
    assert table[0].goal_diff == 6


def test_head_to_head_breaks_tie_on_equal_points_and_gd():
    # X e Y empatam em pontos, saldo e gols pró; X venceu o confronto direto.
    teams = ["X", "Y", "Z", "W"]
    matches = [
        ("X", "Y", 1, 0),   # confronto direto: X vence
        ("X", "Z", 0, 2), ("X", "W", 2, 0),
        ("Y", "Z", 0, 2), ("Y", "W", 2, 0),
        ("Z", "W", 0, 0),
    ]
    table = compute_group_table(teams, matches)
    names = [r.team for r in table]
    assert names.index("X") < names.index("Y")    # X à frente pelo confronto direto


def test_rank_third_places_takes_best_eight():
    thirds = [
        (chr(ord("A") + i), TeamRecord(f"T{i}", played=3, won=w, draw=0, lost=3 - w,
                                       goals_for=gf, goals_against=0))
        for i, (w, gf) in enumerate(
            [(2, 5), (2, 4), (1, 3), (1, 2), (1, 1), (1, 0), (0, 2), (0, 1),
             (0, 0), (2, 6), (1, 4), (0, 3)]
        )
    ]
    best = rank_third_places(thirds)
    assert len(best) == 8
    groups = {g for g, _ in best}
    assert "J" in groups          # 2V, 6 gols -> entra
    assert "I" not in groups      # 0V, 0 gols -> fica de fora
