"""Cálculo de força das seleções por ponto-fixo iterativo (PRD Seção 4.2).

A força de cada time é decomposta em ``attack`` (O) e ``defense`` (D). Os
ratings são estimados resolvendo, por iteração, o sistema em que os gols
previstos (``mu * O_i * D_opp``) igualam os gols efetivamente marcados. Times
fora da Copa entram com força mínima fixa, quebrando a circularidade.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable

from .models import Match, TeamRatings


def league_mu(matches: Iterable[Match]) -> float:
    """Média de gols marcados por time por partida no histórico agregado."""
    matches = list(matches)
    if not matches:
        raise ValueError("histórico vazio: impossível calcular mu")
    total = sum(m.home_goals + m.away_goals for m in matches)
    return total / (2 * len(matches))


def compute_ratings(
    matches: Iterable[Match],
    wc_teams: Collection[str],
    *,
    external_attack: float = 0.5,
    external_defense: float = 1.5,
    reg: float = 0.0,
    max_iter: int = 500,
    tol: float = 1e-9,
) -> dict[str, TeamRatings]:
    """Estima ``TeamRatings`` para cada seleção da Copa que aparece no histórico.

    Args:
        matches: partidas do histórico (90 dias).
        wc_teams: conjunto das 48 seleções da Copa.
        external_attack: poder ofensivo fixo de adversários fora da Copa.
        external_defense: fragilidade defensiva fixa de adversários fora da Copa.
        reg: regularização (encolhimento). Equivale a ``reg`` partidas virtuais
            contra um adversário médio (O=D=1), puxando ratings de amostras
            pequenas para 1 e ancorando a escala. ``0`` desativa.
        max_iter: teto de iterações de ponto-fixo.
        tol: variação máxima entre iterações para declarar convergência.
    """
    matches = list(matches)
    wc_teams = set(wc_teams)
    mu = league_mu(matches)

    # Times da Copa que de fato jogaram.
    teams = sorted(
        {m.home for m in matches if m.home in wc_teams}
        | {m.away for m in matches if m.away in wc_teams}
    )

    attack = {t: 1.0 for t in teams}
    defense = {t: 1.0 for t in teams}

    def opp_attack(name: str) -> float:
        return attack.get(name, external_attack)

    def opp_defense(name: str) -> float:
        return defense.get(name, external_defense)

    # Gols marcados/sofridos são constantes; pré-computa uma vez.
    goals_for = {t: 0.0 for t in teams}
    goals_against = {t: 0.0 for t in teams}
    for m in matches:
        if m.home in goals_for:
            goals_for[m.home] += m.home_goals
            goals_against[m.home] += m.away_goals
        if m.away in goals_for:
            goals_for[m.away] += m.away_goals
            goals_against[m.away] += m.home_goals

    for _ in range(max_iter):
        # 1) Atualiza os ataques usando as defesas correntes.
        denom_attack = {t: 0.0 for t in teams}  # sum mu * D_opp
        for m in matches:
            if m.home in attack:
                denom_attack[m.home] += mu * opp_defense(m.away)
            if m.away in attack:
                denom_attack[m.away] += mu * opp_defense(m.home)
        # Regularização: 'reg' partidas virtuais contra adversário médio
        # (O=D=1), com mu gols marcados/sofridos, encolhendo ratings para 1.
        reg_goals = reg * mu
        reg_denom = reg * mu
        new_attack = {
            t: (goals_for[t] + reg_goals) / (denom_attack[t] + reg_denom)
            if (denom_attack[t] + reg_denom) > 0
            else attack[t]
            for t in teams
        }

        # 2) Atualiza as defesas usando os ataques recém-calculados.
        attack = new_attack
        denom_defense = {t: 0.0 for t in teams}  # sum mu * O_opp
        for m in matches:
            if m.home in defense:
                denom_defense[m.home] += mu * opp_attack(m.away)
            if m.away in defense:
                denom_defense[m.away] += mu * opp_attack(m.home)
        new_defense = {
            t: (goals_against[t] + reg_goals) / (denom_defense[t] + reg_denom)
            if (denom_defense[t] + reg_denom) > 0
            else defense[t]
            for t in teams
        }

        delta = max(abs(new_defense[t] - defense[t]) for t in teams)
        defense = new_defense
        if delta < tol:
            break

    return {t: TeamRatings(attack=attack[t], defense=defense[t]) for t in teams}
