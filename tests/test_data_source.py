"""Testes da camada de dados (parsing de API e provedor sintético)."""

import pytest

from datetime import date

from copa2026.data_source import (
    CombinedDataSource,
    FootballDataSource,
    HardcodedDataSource,
    SyntheticDataSource,
    WORLD_CUP_END,
    canonical_name,
    collection_date_to,
    parse_football_data_matches,
)


def test_collection_date_to_caps_no_final():
    assert WORLD_CUP_END == date(2026, 7, 19)
    # antes da final: a própria data
    assert collection_date_to(date(2026, 6, 25)) == date(2026, 6, 25)
    # depois da final: limita à data da final (repo pode ficar publicado)
    assert collection_date_to(date(2027, 1, 10)) == WORLD_CUP_END


def test_recent_matches_limita_coleta_a_final(monkeypatch):
    import copa2026.data_source as ds

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2027, 3, 1)  # bem depois da Copa

    monkeypatch.setattr(ds, "date", _FakeDate)
    routes = {
        "/competitions/WC/teams": {"teams": [{"id": 764, "name": "Brazil"}]},
        "/teams/764/matches": {"matches": []},
    }
    session = _FakeSession(routes)
    src = FootballDataSource(api_key="fake", session=session)
    src.recent_matches("Brazil")
    call = next(p for url, p in session.calls if "/teams/764/matches" in url)
    assert call["dateTo"] == "2026-07-19"  # limitado à final, não 2027


def test_hardcoded_retorna_jogos_do_time_mais_recentes_primeiro():
    matches = [
        ("2026-03-01", "Brazil", "Chile", 2, 0),
        ("2026-06-01", "Brazil", "France", 1, 1),
        ("2026-05-01", "Spain", "Italy", 0, 0),  # sem o Brasil
    ]
    src = HardcodedDataSource(matches=matches)
    ms = src.recent_matches("Brazil")
    assert len(ms) == 2
    assert ms[0].played_on.isoformat() == "2026-06-01"  # mais recente primeiro
    assert all("Brazil" in (m.home, m.away) for m in ms)


def test_hardcoded_limita_por_last():
    matches = [(f"2026-0{i}-01", "Brazil", "X", i, 0) for i in range(1, 6)]
    src = HardcodedDataSource(matches=matches, last=3)
    assert len(src.recent_matches("Brazil")) == 3


def test_hardcoded_default_carrega_dados_reais():
    ms = HardcodedDataSource().recent_matches("Brazil")
    assert len(ms) >= 5  # base real embutida


def test_combined_concatena_e_remove_duplicatas():
    a = HardcodedDataSource(matches=[("2026-06-01", "Brazil", "France", 1, 1)])
    b = HardcodedDataSource(
        matches=[
            ("2026-06-01", "Brazil", "France", 1, 1),  # duplicata
            ("2026-05-01", "Brazil", "Chile", 2, 0),
        ]
    )
    ms = CombinedDataSource(a, b).recent_matches("Brazil")
    assert len(ms) == 2


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeSession:
    """Sessão HTTP falsa que devolve respostas roteadas por trecho da URL."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append((url, params))
        for fragment, payload in self.routes.items():
            if fragment in url:
                return _FakeResponse(payload)
        raise AssertionError(f"URL inesperada: {url}")


def test_football_data_source_resolve_ids_e_busca_partidas():
    routes = {
        "/competitions/WC/teams": {
            "teams": [
                {"id": 764, "name": "Brazil"},
                {"id": 1, "name": "Korea Republic"},  # apelido -> South Korea
            ]
        },
        "/teams/764/matches": {
            "matches": [
                {
                    "utcDate": "2026-03-01T20:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"name": "Brazil"},
                    "awayTeam": {"name": "Korea Republic"},
                    "score": {"fullTime": {"home": 3, "away": 0}},
                }
            ]
        },
    }
    session = _FakeSession(routes)
    src = FootballDataSource(api_key="fake", session=session)

    matches = src.recent_matches("Brazil")
    assert src.team_ids["South Korea"] == 1
    assert matches[0].home == "Brazil"
    assert matches[0].away == "South Korea"  # canonicalizado
    # buscou pelo id 764 do Brasil
    assert any("/teams/764/matches" in url for url, _ in session.calls)


def test_football_data_source_exige_api_key():
    with pytest.raises(ValueError):
        FootballDataSource(api_key="")


class _FlakySession:
    """Falha com ConnectionError nas primeiras N chamadas, depois responde."""

    def __init__(self, payload, fail_times):
        self.payload = payload
        self.fail_times = fail_times
        self.attempts = 0

    def get(self, url, headers=None, params=None, timeout=None):
        import requests as _rq

        self.attempts += 1
        if self.attempts <= self.fail_times:
            raise _rq.exceptions.ConnectionError("conexão resetada")
        return _FakeResponse(self.payload)


def test_get_repete_em_falha_transitoria():
    session = _FlakySession({"teams": [{"id": 764, "name": "Brazil"}]}, fail_times=2)
    src = FootballDataSource(
        api_key="fake", session=session, max_retries=3, retry_backoff=0
    )
    ids = src.team_ids  # dispara _get; deve sobreviver a 2 falhas
    assert ids["Brazil"] == 764
    assert session.attempts == 3


def test_get_desiste_apos_esgotar_tentativas():
    session = _FlakySession({"teams": []}, fail_times=99)
    src = FootballDataSource(
        api_key="fake", session=session, max_retries=2, retry_backoff=0
    )
    with pytest.raises(Exception):
        _ = src.team_ids


def test_canonicaliza_nomes_de_apelido():
    assert canonical_name("Korea Republic") == "South Korea"
    assert canonical_name("Czechia") == "Czech Republic"
    assert canonical_name("Brazil") == "Brazil"
    # nome desconhecido (adversário externo) permanece inalterado
    assert canonical_name("Some Club FC") == "Some Club FC"


def test_parse_canonicaliza_nomes_da_api():
    payload = {
        "matches": [
            {
                "utcDate": "2026-03-01T20:00:00Z",
                "status": "FINISHED",
                "homeTeam": {"name": "Korea Republic"},
                "awayTeam": {"name": "IR Iran"},
                "score": {"fullTime": {"home": 1, "away": 1}},
            }
        ]
    }
    m = parse_football_data_matches(payload)[0]
    assert m.home == "South Korea"
    assert m.away == "Iran"


def test_parse_ignora_jogos_nao_finalizados_e_mapeia_placar():
    payload = {
        "matches": [
            {
                "utcDate": "2026-03-01T20:00:00Z",
                "status": "FINISHED",
                "homeTeam": {"name": "Brazil"},
                "awayTeam": {"name": "Argentina"},
                "score": {"fullTime": {"home": 2, "away": 1}},
            },
            {
                "utcDate": "2026-03-10T20:00:00Z",
                "status": "SCHEDULED",
                "homeTeam": {"name": "Brazil"},
                "awayTeam": {"name": "Chile"},
                "score": {"fullTime": {"home": None, "away": None}},
            },
        ]
    }
    matches = parse_football_data_matches(payload)
    assert len(matches) == 1
    m = matches[0]
    assert (m.home, m.away, m.home_goals, m.away_goals) == ("Brazil", "Argentina", 2, 1)
    assert m.played_on.isoformat() == "2026-03-01"


def test_synthetic_e_deterministico():
    a = SyntheticDataSource(seed=2026).recent_matches("Brazil")
    b = SyntheticDataSource(seed=2026).recent_matches("Brazil")
    assert a == b


def test_synthetic_muda_com_a_seed():
    a = SyntheticDataSource(seed=1).recent_matches("Brazil")
    b = SyntheticDataSource(seed=2).recent_matches("Brazil")
    assert a != b


def test_synthetic_envolve_o_time_pedido():
    matches = SyntheticDataSource(seed=2026).recent_matches("Brazil")
    assert len(matches) > 0
    assert all("Brazil" in (m.home, m.away) for m in matches)
