"""Testes da resolução de team ids a partir de nomes da API."""

from copa2026.data_source import normalize_name, resolve_team_ids


def test_normalize_remove_acentos_caixa_e_pontuacao():
    assert normalize_name("Côte d'Ivoire") == "cote d ivoire"
    assert normalize_name("Türkiye") == "turkiye"
    assert normalize_name("  Bosnia-Herzegovina  ") == "bosnia herzegovina"


def test_resolve_casa_nome_canonico():
    api_teams = [
        {"id": 764, "name": "Brazil"},
        {"id": 762, "name": "Argentina"},
    ]
    ids = resolve_team_ids(api_teams)
    assert ids["Brazil"] == 764
    assert ids["Argentina"] == 762


def test_resolve_casa_por_apelido():
    api_teams = [
        {"id": 1, "name": "Korea Republic"},     # South Korea
        {"id": 2, "name": "Czechia"},            # Czech Republic
        {"id": 3, "name": "IR Iran"},            # Iran
        {"id": 4, "name": "Côte d'Ivoire"},      # Ivory Coast
        {"id": 5, "name": "Türkiye"},            # Turkey
    ]
    ids = resolve_team_ids(api_teams)
    assert ids["South Korea"] == 1
    assert ids["Czech Republic"] == 2
    assert ids["Iran"] == 3
    assert ids["Ivory Coast"] == 4
    assert ids["Turkey"] == 5


def test_resolve_ignora_times_fora_da_copa():
    api_teams = [
        {"id": 99, "name": "Italy"},   # não classificada
        {"id": 764, "name": "Brazil"},
    ]
    ids = resolve_team_ids(api_teams)
    assert "Italy" not in ids
    assert ids == {"Brazil": 764}
