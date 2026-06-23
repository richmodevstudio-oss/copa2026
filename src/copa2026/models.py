"""Estruturas de dados centrais do domínio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Match:
    """Uma partida do histórico.

    Os gols são sempre do ponto de vista de ``home`` e ``away``.
    """

    home: str
    away: str
    home_goals: int
    away_goals: int
    played_on: Optional[date] = None


@dataclass(frozen=True)
class TeamRatings:
    """Força de uma seleção, decomposta em dois ratings.

    - ``attack`` (O):  poder ofensivo (>1 marca mais que a média).
    - ``defense`` (D): fragilidade defensiva (>1 sofre mais que a média).
    """

    attack: float
    defense: float
