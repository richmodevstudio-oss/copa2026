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
    assert [r.team for r in table] == ["A", "C", "B", "D"]


def test_head_to_head_breaks_tie_on_equal_points_and_gd():
    # X e Y empatam em pontos (6), saldo (+1) e gols pró (3);
    # X vence o confronto direto (2x1) e deve ficar à frente.
    teams = ["X", "Y", "Z", "W"]
    matches = [
        ("X", "Y", 2, 1),   # confronto direto: X vence
        ("X", "Z", 1, 0), ("X", "W", 0, 1),
        ("Y", "Z", 1, 0), ("Y", "W", 1, 0),
        ("Z", "W", 1, 1),
    ]
    table = compute_group_table(teams, matches)
    # confirma o empate real nos três critérios gerais antes do desempate
    assert table[0].points == table[1].points == 6
    assert table[0].goal_diff == table[1].goal_diff == 1
    assert table[0].goals_for == table[1].goals_for == 3
    assert {table[0].team, table[1].team} == {"X", "Y"}
    assert table[0].team == "X"   # confronto direto coloca X à frente


def test_name_breaks_full_tie_including_head_to_head():
    # P e Q empatam em tudo, inclusive no confronto direto (1x1);
    # desempate determinístico por nome -> "P" antes de "Q".
    teams = ["Q", "P", "R", "S"]
    matches = [
        ("P", "Q", 1, 1),
        ("P", "R", 2, 0), ("P", "S", 2, 0),
        ("Q", "R", 2, 0), ("Q", "S", 2, 0),
        ("R", "S", 0, 0),
    ]
    table = compute_group_table(teams, matches)
    assert table[0].points == table[1].points == 7
    assert {table[0].team, table[1].team} == {"P", "Q"}
    assert table[0].team == "P"   # nome desempata


def test_rank_third_places_ties_broken_by_group_letter():
    # Dois terceiros idênticos (4 pts, +1, 3 GP); grupo "A" vem antes de "B".
    a = TeamRecord("Ta", played=3, won=1, draw=1, lost=1, goals_for=3, goals_against=2)
    b = TeamRecord("Tb", played=3, won=1, draw=1, lost=1, goals_for=3, goals_against=2)
    weak = [
        (chr(ord("C") + i),
         TeamRecord(f"W{i}", played=3, won=0, draw=0, lost=3, goals_for=0, goals_against=i + 1))
        for i in range(6)
    ]
    best = rank_third_places([("B", b), ("A", a), *weak])
    assert len(best) == 8
    assert best[0][0] == "A" and best[1][0] == "B"   # empate -> letra do grupo decide


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
