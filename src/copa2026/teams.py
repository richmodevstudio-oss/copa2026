"""As 48 seleções classificadas para a Copa do Mundo de 2026.

O nome **canônico** é em inglês, para casar com a nomenclatura da
football-data.org. ``TEAM_DISPLAY_PT`` traz o rótulo em português usado na
interface. ``TEAM_NAME_ALIASES`` lista variantes de nome usadas por provedores
de dados (ex.: "Korea Republic" para "South Korea"), usadas na resolução de IDs.

Qualquer adversário do histórico que não esteja nesta lista recebe "força
mínima" no cálculo de ratings (ver ``strength.py``).
"""

from __future__ import annotations

# (nome canônico em inglês, rótulo em português, confederação)
_TEAMS: list[tuple[str, str, str]] = [
    ("Canada", "Canadá", "Anfitrião"),
    ("United States", "Estados Unidos", "Anfitrião"),
    ("Mexico", "México", "Anfitrião"),
    ("Curaçao", "Curaçao", "CONCACAF"),
    ("Haiti", "Haiti", "CONCACAF"),
    ("Panama", "Panamá", "CONCACAF"),
    ("Japan", "Japão", "AFC"),
    ("Iran", "Irã", "AFC"),
    ("Uzbekistan", "Uzbequistão", "AFC"),
    ("South Korea", "Coreia do Sul", "AFC"),
    ("Jordan", "Jordânia", "AFC"),
    ("Australia", "Austrália", "AFC"),
    ("Qatar", "Catar", "AFC"),
    ("Saudi Arabia", "Arábia Saudita", "AFC"),
    ("New Zealand", "Nova Zelândia", "OFC"),
    ("Argentina", "Argentina", "CONMEBOL"),
    ("Brazil", "Brasil", "CONMEBOL"),
    ("Ecuador", "Equador", "CONMEBOL"),
    ("Uruguay", "Uruguai", "CONMEBOL"),
    ("Colombia", "Colômbia", "CONMEBOL"),
    ("Paraguay", "Paraguai", "CONMEBOL"),
    ("Morocco", "Marrocos", "CAF"),
    ("Tunisia", "Tunísia", "CAF"),
    ("Egypt", "Egito", "CAF"),
    ("Algeria", "Argélia", "CAF"),
    ("Ghana", "Gana", "CAF"),
    ("Cape Verde", "Cabo Verde", "CAF"),
    ("South Africa", "África do Sul", "CAF"),
    ("Ivory Coast", "Costa do Marfim", "CAF"),
    ("Senegal", "Senegal", "CAF"),
    ("England", "Inglaterra", "UEFA"),
    ("France", "França", "UEFA"),
    ("Croatia", "Croácia", "UEFA"),
    ("Portugal", "Portugal", "UEFA"),
    ("Norway", "Noruega", "UEFA"),
    ("Netherlands", "Holanda", "UEFA"),
    ("Germany", "Alemanha", "UEFA"),
    ("Switzerland", "Suíça", "UEFA"),
    ("Austria", "Áustria", "UEFA"),
    ("Belgium", "Bélgica", "UEFA"),
    ("Spain", "Espanha", "UEFA"),
    ("Scotland", "Escócia", "UEFA"),
    ("Turkey", "Turquia", "UEFA"),
    ("Czech Republic", "República Tcheca", "UEFA"),
    ("Sweden", "Suécia", "UEFA"),
    ("Bosnia and Herzegovina", "Bósnia e Herzegovina", "UEFA"),
    ("DR Congo", "RD Congo", "Repescagem"),
    ("Iraq", "Iraque", "Repescagem"),
]

WORLD_CUP_2026_TEAMS: list[str] = [canonical for canonical, _, _ in _TEAMS]
WORLD_CUP_2026_TEAMS_SET = frozenset(WORLD_CUP_2026_TEAMS)

TEAM_DISPLAY_PT: dict[str, str] = {canonical: pt for canonical, pt, _ in _TEAMS}
TEAM_CONFEDERATION: dict[str, str] = {canonical: conf for canonical, _, conf in _TEAMS}

# Variantes de nome usadas por provedores de dados (football-data.org e afins).
# A chave é o nome canônico; os valores são nomes alternativos a aceitar.
TEAM_NAME_ALIASES: dict[str, list[str]] = {
    "United States": ["USA", "United States of America"],
    "South Korea": ["Korea Republic", "Republic of Korea"],
    "Iran": ["IR Iran", "Iran Islamic Republic"],
    "Czech Republic": ["Czechia"],
    "Ivory Coast": ["Côte d'Ivoire", "Cote d'Ivoire"],
    "DR Congo": ["Congo DR", "Democratic Republic of the Congo", "Congo Democratic Republic"],
    "Turkey": ["Türkiye", "Turkiye"],
    "Bosnia and Herzegovina": ["Bosnia-Herzegovina", "Bosnia & Herzegovina"],
    "Cape Verde": ["Cabo Verde", "Cape Verde Islands"],
    "Curaçao": ["Curacao"],
}

assert len(WORLD_CUP_2026_TEAMS) == 48, "A Copa 2026 tem 48 seleções"


def display_pt(team: str) -> str:
    """Rótulo em português de uma seleção (ou o próprio nome se desconhecido)."""
    return TEAM_DISPLAY_PT.get(team, team)
