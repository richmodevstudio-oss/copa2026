"""Coleta de dados das partidas recentes (PRD Seção 4.1).

Define uma abstração ``MatchDataSource`` com duas implementações:

- ``FootballDataSource``: consome a API pública football-data.org (requer
  variável de ambiente ``FOOTBALL_DATA_API_KEY``).
- ``SyntheticDataSource``: gera dados plausíveis e determinísticos, permitindo
  rodar a aplicação totalmente offline (demonstração e testes).
"""

from __future__ import annotations

import os
import random
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Iterable, Protocol, runtime_checkable

import requests

from .models import Match
from .teams import TEAM_NAME_ALIASES, WORLD_CUP_2026_TEAMS

FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
WORLD_CUP_COMPETITION_CODE = "WC"

# A análise é específica da Copa de 2026; como o repositório pode permanecer
# publicado indefinidamente, a coleta de dados nunca passa da data da final
# (evita puxar amistosos pós-Copa quando o app/análise rodar no futuro).
WORLD_CUP_END = date(2026, 7, 19)


def collection_date_to(today: date | None = None) -> date:
    """Data-limite da coleta: nunca posterior à final da Copa (``WORLD_CUP_END``)."""
    return min(today or date.today(), WORLD_CUP_END)


def get_json_with_retries(
    session,
    url: str,
    *,
    headers: dict,
    params: dict | None = None,
    max_retries: int = 3,
    retry_backoff: float = 2.0,
) -> dict:
    """GET JSON com novas tentativas em falhas transitórias (rede / HTTP 429)."""
    import time

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, headers=headers, params=params, timeout=30)
            if getattr(resp, "status_code", 200) == 429:  # rate limit
                last_exc = RuntimeError("HTTP 429: limite de requisições")
            else:
                resp.raise_for_status()
                return resp.json()
        except requests.exceptions.RequestException as exc:
            last_exc = exc
        if attempt < max_retries:
            time.sleep(retry_backoff * attempt)
    raise last_exc or RuntimeError("Falha ao consultar a API.")


def normalize_name(name: str) -> str:
    """Normaliza um nome de seleção para comparação robusta.

    Minúsculas, sem acentos, sem pontuação e com espaços colapsados.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-z0-9]+", " ", no_accents.lower())
    return cleaned.strip()


# Índice global: nome normalizado (canônico ou apelido) -> nome canônico.
_CANONICAL_LOOKUP: dict[str, str] = {}
for _canonical in WORLD_CUP_2026_TEAMS:
    _CANONICAL_LOOKUP[normalize_name(_canonical)] = _canonical
    for _alias in TEAM_NAME_ALIASES.get(_canonical, []):
        _CANONICAL_LOOKUP[normalize_name(_alias)] = _canonical


def canonical_name(name: str) -> str:
    """Nome canônico de uma seleção, ou o próprio nome se não for da Copa."""
    return _CANONICAL_LOOKUP.get(normalize_name(name), name)


def resolve_team_ids(api_teams: list[dict]) -> dict[str, int]:
    """Mapeia ``{nome canônico -> team id}`` a partir da lista de times da API.

    Casa cada uma das 48 seleções pelo nome canônico ou por um apelido conhecido
    (``TEAM_NAME_ALIASES``). Times fora da Copa são ignorados.
    """
    mapping: dict[str, int] = {}
    for team in api_teams:
        canonical = _CANONICAL_LOOKUP.get(normalize_name(team["name"]))
        if canonical is not None:
            mapping[canonical] = int(team["id"])
    return mapping


@runtime_checkable
class MatchDataSource(Protocol):
    """Fonte de partidas recentes de uma seleção."""

    def recent_matches(self, team: str, days: int = 90) -> list[Match]: ...


def parse_football_data_matches(payload: dict) -> list[Match]:
    """Converte a resposta da football-data.org em ``Match`` finalizados."""
    matches: list[Match] = []
    for item in payload.get("matches", []):
        if item.get("status") != "FINISHED":
            continue
        full_time = item["score"]["fullTime"]
        if full_time["home"] is None or full_time["away"] is None:
            continue
        played_on = datetime.fromisoformat(
            item["utcDate"].replace("Z", "+00:00")
        ).date()
        matches.append(
            Match(
                home=canonical_name(item["homeTeam"]["name"]),
                away=canonical_name(item["awayTeam"]["name"]),
                home_goals=int(full_time["home"]),
                away_goals=int(full_time["away"]),
                played_on=played_on,
            )
        )
    return matches


class FootballDataSource:
    """Adapter para a API pública football-data.org (dados reais).

    Os ``team ids`` são resolvidos **dinamicamente** a partir do endpoint de
    times da competição (``/competitions/{code}/teams``), casando os nomes pela
    tabela de apelidos — evitando cravar IDs à mão. É possível passar
    ``team_ids`` manualmente para sobrescrever ou complementar a resolução.

    Requer uma chave de API em ``FOOTBALL_DATA_API_KEY`` ou via ``api_key``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        competition: str = WORLD_CUP_COMPETITION_CODE,
        team_ids: dict[str, int] | None = None,
        session: requests.Session | None = None,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
    ):
        self.api_key = api_key or os.environ.get("FOOTBALL_DATA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Defina FOOTBALL_DATA_API_KEY ou passe api_key explicitamente."
            )
        self.competition = competition
        self._session = session or requests.Session()
        self._team_ids: dict[str, int] = dict(team_ids or {})
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def _get(self, path: str, params: dict | None = None) -> dict:
        return get_json_with_retries(
            self._session,
            f"{FOOTBALL_DATA_BASE_URL}{path}",
            headers={"X-Auth-Token": self.api_key},
            params=params,
            max_retries=self.max_retries,
            retry_backoff=self.retry_backoff,
        )

    @property
    def team_ids(self) -> dict[str, int]:
        """IDs resolvidos (resolve sob demanda na primeira chamada)."""
        if not self._team_ids:
            payload = self._get(f"/competitions/{self.competition}/teams")
            self._team_ids = resolve_team_ids(payload.get("teams", []))
        return self._team_ids

    def team_id(self, team: str) -> int:
        try:
            return self.team_ids[team]
        except KeyError:
            raise KeyError(
                f"Sem team id para '{team}' na competição '{self.competition}'. "
                f"Passe team_ids={{'{team}': <id>}} manualmente."
            ) from None

    def recent_matches(self, team: str, days: int = 90) -> list[Match]:
        date_to = collection_date_to()
        date_from = date_to - timedelta(days=days)
        payload = self._get(
            f"/teams/{self.team_id(team)}/matches",
            params={
                "status": "FINISHED",
                "dateFrom": date_from.isoformat(),
                "dateTo": date_to.isoformat(),
            },
        )
        return parse_football_data_matches(payload)

    def competition_matches(self) -> dict:
        """Todos os jogos da competição (calendário + resultados + chaveamento)."""
        return self._get(f"/competitions/{self.competition}/matches")


class SyntheticDataSource:
    """Gera partidas determinísticas para uso offline.

    A cada seleção é atribuída uma "qualidade" estável; os gols de cada partida
    são amostrados de Poisson em função das qualidades relativas, produzindo um
    histórico internamente coerente.
    """

    def __init__(self, seed: int = 2026, n_matches: int = 12):
        self.seed = seed
        self.n_matches = n_matches

    def _quality(self, team: str) -> float:
        rng = random.Random(f"{self.seed}:quality:{team}")
        return rng.uniform(0.7, 1.6)

    def recent_matches(self, team: str, days: int = 90) -> list[Match]:
        rng = random.Random(f"{self.seed}:matches:{team}")
        q_team = self._quality(team)
        opponents = [t for t in WORLD_CUP_2026_TEAMS if t != team]
        today = date.today()

        matches: list[Match] = []
        for _ in range(self.n_matches):
            opp = rng.choice(opponents)
            q_opp = self._quality(opp)
            lam_team = max(0.2, 1.4 * q_team / q_opp)
            lam_opp = max(0.2, 1.4 * q_opp / q_team)
            g_team = _poisson(rng, lam_team)
            g_opp = _poisson(rng, lam_opp)
            played_on = today - timedelta(days=rng.randint(1, days))
            if rng.random() < 0.5:  # time joga em casa
                matches.append(Match(team, opp, g_team, g_opp, played_on))
            else:
                matches.append(Match(opp, team, g_opp, g_team, played_on))
        return matches


class HardcodedDataSource:
    """Histórico pré-Copa embutido (jogos pesquisados, sem dependência de rede).

    Por padrão usa a base gerada em ``pre_wc_data.PRE_WC_MATCHES``.
    """

    def __init__(
        self,
        matches: Iterable[tuple[str, str, str, int, int]] | None = None,
        *,
        last: int = 12,
    ):
        if matches is None:
            from .pre_wc_data import PRE_WC_MATCHES

            matches = PRE_WC_MATCHES
        self._matches = [
            Match(home, away, gh, ga, date.fromisoformat(d))
            for d, home, away, gh, ga in matches
        ]
        self.last = last

    def recent_matches(self, team: str, days: int = 90) -> list[Match]:
        jogos = [m for m in self._matches if team in (m.home, m.away)]
        jogos.sort(key=lambda m: m.played_on or date.min, reverse=True)
        return jogos[: self.last]


class CombinedDataSource:
    """Concatena várias fontes, removendo partidas duplicadas.

    Usada para combinar o histórico pré-Copa (hardcoded) com os jogos da própria
    Copa (football-data.org), preservando a ordem das fontes.
    """

    def __init__(self, *sources: MatchDataSource):
        self.sources = sources

    def recent_matches(self, team: str, days: int = 90) -> list[Match]:
        seen: set[Match] = set()
        out: list[Match] = []
        for source in self.sources:
            for match in source.recent_matches(team, days):
                if match not in seen:
                    seen.add(match)
                    out.append(match)
        return out


def _poisson(rng: random.Random, lam: float) -> int:
    """Amostra Poisson via algoritmo de Knuth, usando um RNG determinístico."""
    import math

    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= limit:
            return k - 1
