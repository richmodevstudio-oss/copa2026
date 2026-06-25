from copa2026.championship import prob_vitoria, probabilidades_titulo
from copa2026.models import TeamRatings


def _ratings():
    return {
        "A": TeamRatings(1.6, 0.7),   # forte
        "B": TeamRatings(0.8, 1.4),   # fraco
        "C": TeamRatings(1.2, 1.0),
        "D": TeamRatings(1.0, 1.1),
    }


def test_prob_vitoria_complementar():
    r = _ratings()
    p = prob_vitoria("A", "B", r, mu=1.3)
    q = prob_vitoria("B", "A", r, mu=1.3)
    assert abs((p + q) - 1.0) < 1e-9
    assert p > q          # A é mais forte


def test_dp_dois_times_um_jogo():
    r = _ratings()
    # chaveamento-brinquedo: 1 jogo (final = jogo 1), A x B
    matches = {1: (("W", "X"), ("W", "Y"))}  # slots ignorados em folha
    confrontos = {1: ("A", "B")}
    por_time = probabilidades_titulo(confrontos, r, mu=1.3,
                                     matches=matches, final=1)
    pa = prob_vitoria("A", "B", r, mu=1.3)
    assert abs(por_time["A"]["CAMPEAO"] - pa) < 1e-9
    assert abs(por_time["B"]["CAMPEAO"] - (1 - pa)) < 1e-9
    assert abs(sum(t["CAMPEAO"] for t in por_time.values()) - 1.0) < 1e-9


def test_dp_quatro_times_soma_um():
    r = _ratings()
    # 2 semifinais (jogos 1 e 2) -> final (jogo 3)
    matches = {
        1: (("W", "X"), ("W", "Y")),
        2: (("W", "X"), ("W", "Y")),
        3: (("WM", 1), ("WM", 2)),
    }
    confrontos = {1: ("A", "B"), 2: ("C", "D")}
    por_time = probabilidades_titulo(confrontos, r, mu=1.3,
                                     matches=matches, final=3)
    assert set(por_time) == {"A", "B", "C", "D"}
    assert abs(sum(t["CAMPEAO"] for t in por_time.values()) - 1.0) < 1e-9
    # A (forte) campeão mais provável que B (fraco)
    assert por_time["A"]["CAMPEAO"] > por_time["B"]["CAMPEAO"]
    # probabilidade de campeão <= probabilidade de vencer a 1ª rodada
    assert por_time["A"]["CAMPEAO"] <= por_time["A"]["1"] + 1e-12
