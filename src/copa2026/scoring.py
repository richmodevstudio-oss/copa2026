"""Função de pontuação do bolão (PRD Seção 3).

Pontuação base de 3 pontos por acertar o resultado (vitória do mandante,
vitória do visitante ou empate). Sobre a base, aplica-se *no máximo um* bônus
adicional — vale apenas o de maior valor entre os critérios acertados.
"""

from __future__ import annotations

Placar = tuple[int, int]


def _resultado(p: Placar) -> int:
    """-1 vitória do visitante, 0 empate, +1 vitória do mandante."""
    return (p[0] > p[1]) - (p[0] < p[1])


def _gols_vencedor_perdedor(p: Placar) -> tuple[int, int] | None:
    """(gols do vencedor, gols do perdedor) ou None em caso de empate."""
    if p[0] == p[1]:
        return None
    return (max(p), min(p))


def score(palpite: Placar, real: Placar) -> int:
    """Pontos obtidos pelo ``palpite`` dado o resultado ``real``."""
    if _resultado(palpite) != _resultado(real):
        return 0

    bonus = 0

    # +5 placar exato
    if palpite == real:
        bonus = max(bonus, 5)

    # +3 gols do vencedor
    gp = _gols_vencedor_perdedor(palpite)
    gr = _gols_vencedor_perdedor(real)
    if gp is not None and gr is not None and gp[0] == gr[0]:
        bonus = max(bonus, 3)

    # +2 diferença de gols
    if (palpite[0] - palpite[1]) == (real[0] - real[1]):
        bonus = max(bonus, 2)

    # +1 gols do perdedor
    if gp is not None and gr is not None and gp[1] == gr[1]:
        bonus = max(bonus, 1)

    # +1 goleada em ambos (diferença > 3 gols)
    if abs(palpite[0] - palpite[1]) > 3 and abs(real[0] - real[1]) > 3:
        bonus = max(bonus, 1)

    return 3 + bonus
