"""Mapa fixo do chaveamento da Copa 2026 (a API não fornece chaveamento).

Confrontos do R32 em notação de posição de grupo e a árvore até a final,
derivados das regras/Anexo da FIFA. Validados em testes (`test_bracket_data`).
"""

from __future__ import annotations

GROUPS = list("ABCDEFGHIJKL")
WINNERS_FACING_THIRD = ["A", "B", "D", "E", "G", "I", "K", "L"]

# Slot: ("W", grupo) vencedor; ("R", grupo) vice; ("3", grupo) terceiro alocado
# ao confronto do 1º desse grupo; ("WM", n) vencedor do jogo n; ("LM", n) perdedor.
MATCHES: dict[int, tuple[tuple, tuple]] = {
    73: (("R", "A"), ("R", "B")),
    74: (("W", "E"), ("3", "E")),
    75: (("W", "F"), ("R", "C")),
    76: (("W", "C"), ("R", "F")),
    77: (("W", "I"), ("3", "I")),
    78: (("R", "E"), ("R", "I")),
    79: (("W", "A"), ("3", "A")),
    80: (("W", "L"), ("3", "L")),
    81: (("W", "D"), ("3", "D")),
    82: (("W", "G"), ("3", "G")),
    83: (("R", "K"), ("R", "L")),
    84: (("W", "H"), ("R", "J")),
    85: (("W", "B"), ("3", "B")),
    86: (("W", "K"), ("3", "K")),
    87: (("W", "J"), ("R", "H")),
    88: (("R", "D"), ("R", "G")),
    89: (("WM", 74), ("WM", 77)),
    90: (("WM", 73), ("WM", 75)),
    91: (("WM", 83), ("WM", 84)),
    92: (("WM", 81), ("WM", 82)),
    93: (("WM", 76), ("WM", 78)),
    94: (("WM", 79), ("WM", 80)),
    95: (("WM", 86), ("WM", 88)),
    96: (("WM", 85), ("WM", 87)),
    97: (("WM", 89), ("WM", 90)),
    98: (("WM", 93), ("WM", 94)),
    99: (("WM", 91), ("WM", 92)),
    100: (("WM", 95), ("WM", 96)),
    101: (("WM", 97), ("WM", 98)),
    102: (("WM", 99), ("WM", 100)),
    103: (("LM", 101), ("LM", 102)),  # disputa de 3º lugar
    104: (("WM", 101), ("WM", 102)),  # final
}

STAGE_OF: dict[int, str] = {
    **{n: "LAST_32" for n in range(73, 89)},
    **{n: "LAST_16" for n in range(89, 97)},
    **{n: "QUARTER_FINALS" for n in range(97, 101)},
    101: "SEMI_FINALS",
    102: "SEMI_FINALS",
    103: "THIRD_PLACE",
    104: "FINAL",
}

STAGE_LABEL_PT: dict[str, str] = {
    "GROUP_STAGE": "Fase de grupos",
    "LAST_32": "16 avos de final",
    "LAST_16": "Oitavas de final",
    "QUARTER_FINALS": "Quartas de final",
    "SEMI_FINALS": "Semifinais",
    "THIRD_PLACE": "Disputa de 3º lugar",
    "FINAL": "Final",
}
