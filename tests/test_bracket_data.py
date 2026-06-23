from copa2026.bracket_data import MATCHES, STAGE_OF, WINNERS_FACING_THIRD
from copa2026.third_place_data import BEST_THIRD_ALLOCATION


def test_matches_cover_73_to_104():
    assert set(MATCHES) == set(range(73, 105))
    assert set(STAGE_OF) == set(range(73, 105))


def test_every_match_reference_is_defined():
    for no, (a, b) in MATCHES.items():
        for slot in (a, b):
            tag, val = slot
            assert tag in {"W", "R", "3", "WM", "LM"}
            if tag in {"WM", "LM"}:
                assert val in MATCHES and val < no   # dependência já resolvida na ordem


def test_r32_thirds_only_for_designated_winner_groups():
    third_slots = [
        a[1] if a[0] == "3" else b[1]
        for a, b in (MATCHES[n] for n in range(73, 89))
        if a[0] == "3" or b[0] == "3"
    ]
    assert sorted(third_slots) == sorted(WINNERS_FACING_THIRD)


def test_allocation_has_495_consistent_rows():
    assert len(BEST_THIRD_ALLOCATION) == 495
    for key, mapping in BEST_THIRD_ALLOCATION.items():
        assert len(key) == 8
        assert set(mapping) == set(WINNERS_FACING_THIRD)
        assert set(mapping.values()) == set(key)     # terceiros vêm dos grupos da chave


def test_known_allocation_row():
    # combinação E,F,G,H,I,J,K,L (terceiros de A,B,C,D não avançam)
    row = BEST_THIRD_ALLOCATION["EFGHIJKL"]
    assert row["A"] == "E" and row["E"] == "F" and row["L"] == "K"
