# Aba "Tabela da Copa" — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar uma aba Streamlit que reproduz a tabela da Copa 2026 (grupos + mata-mata), misturando resultados reais (API, conferidos a cada atualização) com resultados previstos até a final, sob a premissa de que o previsor sempre acerta o vencedor.

**Architecture:** A força das 48 seleções é calculada **uma vez** a partir do histórico combinado (pré-Copa embutido + jogos da Copa via API); cada jogo futuro é previsto sem rede repetida. A fase de grupos usa resultados reais quando disponíveis e calcula a classificação pelas regras FIFA; o mata-mata é montado por um mapa de chaveamento fixo embutido (a API não fornece chaveamento) e propagado por λ até a final.

**Tech Stack:** Python 3, numpy, scipy, requests, Streamlit, pytest (TDD, `pythonpath=src`).

## Global Constraints

- Pacote em `src/copa2026/` (importável; `pythonpath = src` no `pytest.ini`).
- Strings da UI e docs em **português**; nomes canônicos das seleções em inglês (casam com a API).
- TDD: teste antes da implementação; testes **sem rede** (dados injetados/sintéticos).
- Toda etapa referencia a seção do `prd.md` quando aplicável.
- Nomes canônicos das 48 seleções em `WORLD_CUP_2026_TEAMS` / `WORLD_CUP_2026_TEAMS_SET` (`teams.py`).
- Mapeamento de nomes da API: `canonical_name()` (`data_source.py`) — Curaçao, "Cape Verde Islands", "Congo DR", "Bosnia-Herzegovina", "Czechia", "Iraq" etc. precisam de apelidos.

---

## Contexto técnico já apurado (não re-investigar)

- API `GET https://api.football-data.org/v4/competitions/WC/matches` (header `X-Auth-Token`) devolve 104 jogos com `stage` ∈ {GROUP_STAGE, LAST_32, LAST_16, QUARTER_FINALS, SEMI_FINALS, THIRD_PLACE, FINAL}, `group` ∈ {GROUP_A…GROUP_L}, `status` (FINISHED/TIMED), `score.fullTime.{home,away}`, `score.winner`, `score.duration`, `utcDate`, `homeTeam.name`, `awayTeam.name`. **Jogos de mata-mata vêm com times nulos e sem metadata de chaveamento.**
- Grupos (validados na API): A: México, África do Sul, Coreia do Sul, Czechia; B: Canadá, Bósnia, Catar, Suíça; C: Brasil, Haiti, Marrocos, Escócia; D: Austrália, Paraguai, Turquia, EUA; E: Curaçao, Equador, Alemanha, Costa do Marfim; F: Japão, Holanda, Suécia, Tunísia; G: Bélgica, Egito, Irã, Nova Zelândia; H: Cabo Verde, Arábia Saudita, Espanha, Uruguai; I: França, Iraque, Noruega, Senegal; J: Argélia, Argentina, Áustria, Jordânia; K: Colômbia, Congo DR, Portugal, Uzbequistão; L: Croácia, Inglaterra, Gana, Panamá.
- **Chaveamento R32 (match → confronto, notação de posição de grupo)** — derivado da Wikipédia/regulamento FIFA:

| Jogo | Mandante | Visitante |
|---|---|---|
| 73 | 2º A | 2º B |
| 74 | 1º E | 3º (alloc) |
| 75 | 1º F | 2º C |
| 76 | 1º C | 2º F |
| 77 | 1º I | 3º (alloc) |
| 78 | 2º E | 2º I |
| 79 | 1º A | 3º (alloc) |
| 80 | 1º L | 3º (alloc) |
| 81 | 1º D | 3º (alloc) |
| 82 | 1º G | 3º (alloc) |
| 83 | 2º K | 2º L |
| 84 | 1º H | 2º J |
| 85 | 1º B | 3º (alloc) |
| 86 | 1º K | 3º (alloc) |
| 87 | 1º J | 2º H |
| 88 | 2º D | 2º G |

- **Árvore (match → vencedores que se enfrentam):** 89=(W74,W77) 90=(W73,W75) 91=(W83,W84) 92=(W81,W82) 93=(W76,W78) 94=(W79,W80) 95=(W86,W88) 96=(W85,W87); 97=(W89,W90) 98=(W93,W94) 99=(W91,W92) 100=(W95,W96); 101=(W97,W98) 102=(W99,W100); 103=(L101,L102) (3º lugar); 104=(W101,W102) (final).
- **Grupos cujo 1º enfrenta um 3º:** A, B, D, E, G, I, K, L (ordem das colunas da tabela oficial dos terceiros).
- **Tabela oficial dos 8 melhores terceiros:** template Wikipédia `Template:2026 FIFA World Cup third-place table` (raw wikitext), 495 linhas. Cada linha: 8 grupos avançam (tokens `'''X'''`) e 8 atribuições (`3X`) na ordem das colunas (1A,1B,1D,1E,1G,1I,1K,1L).

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/copa2026/ratings.py` | força global das 48 seleções (1×) + `predict_scoreline` + vencedor de mata-mata |
| `src/copa2026/standings.py` | classificação de grupo (regras FIFA) + ranking dos terceiros |
| `src/copa2026/bracket_data.py` | mapa de chaveamento fixo (escrito à mão, pequeno) |
| `src/copa2026/third_place_data.py` | **gerado** — `BEST_THIRD_ALLOCATION` (495 entradas) |
| `scripts/generate_third_place_data.py` | gera `third_place_data.py` da Wikipédia |
| `src/copa2026/tournament.py` | `FixtureMatch`, parser, `fetch_wc_fixtures`, `simulate_tournament` |
| `src/copa2026/data_source.py` | método `competition_matches()` em `FootballDataSource` |
| `app.py` | abas + render da aba "Tabela da Copa" |
| `tests/test_ratings.py`, `test_standings.py`, `test_bracket_data.py`, `test_tournament.py` | testes |
| `prd.md` | nova seção da feature |
| `docs/tabela_copa2026/` | **removido** (PDF não renderizável, redundante) |

---

## Task 1: Força global e previsão de placar (`ratings.py`)

**Files:**
- Create: `src/copa2026/ratings.py`
- Test: `tests/test_ratings.py`

**Interfaces:**
- Consumes: `compute_ratings`, `league_mu` (`strength.py`); `expected_goals`, `score_matrix` (`prediction.py`); `best_guess` (`optimizer.py`); `TeamRatings` (`models.py`); `WORLD_CUP_2026_TEAMS`, `WORLD_CUP_2026_TEAMS_SET` (`teams.py`); `MatchDataSource` (`data_source.py`).
- Produces:
  - `compute_global_ratings(source, *, teams=WORLD_CUP_2026_TEAMS, days=90, reg=2.0) -> tuple[dict[str, TeamRatings], float]` (ratings, mu).
  - `ScorePrediction` dataclass: `home, away, palpite: tuple[int,int], lambda_home, lambda_away, home_ratings, away_ratings`.
  - `predict_scoreline(home, away, ratings, mu, *, max_goals=8) -> ScorePrediction`.
  - `knockout_winner(pred: ScorePrediction) -> tuple[str, bool]` → (time que avança, foi_nos_penaltis).

- [ ] **Step 1: Teste de `predict_scoreline` e `knockout_winner`**

```python
# tests/test_ratings.py
from copa2026.models import TeamRatings
from copa2026.ratings import predict_scoreline, knockout_winner


def _ratings():
    return {"Brazil": TeamRatings(1.6, 0.7), "Chile": TeamRatings(0.8, 1.4)}


def test_predict_scoreline_favors_stronger_team():
    pred = predict_scoreline("Brazil", "Chile", _ratings(), mu=1.3)
    assert pred.lambda_home > pred.lambda_away
    assert pred.palpite[0] >= pred.palpite[1]


def test_knockout_winner_from_decisive_palpite():
    pred = predict_scoreline("Brazil", "Chile", _ratings(), mu=1.3)
    winner, penalties = knockout_winner(pred)
    assert winner == "Brazil"
    assert penalties is False


def test_knockout_winner_draw_resolved_by_lambda_with_penalties():
    # times de força idêntica -> palpite empatado; desempata por lambda/qualidade
    r = {"A": TeamRatings(1.2, 0.9), "B": TeamRatings(1.2, 0.9)}
    pred = predict_scoreline("A", "B", r, mu=1.0)
    assert pred.palpite[0] == pred.palpite[1]      # empate no palpite
    winner, penalties = knockout_winner(pred)
    assert penalties is True
    assert winner in ("A", "B")


def test_unknown_team_uses_neutral_rating():
    pred = predict_scoreline("Brazil", "Narnia", _ratings(), mu=1.3)
    assert pred.away_ratings == TeamRatings(1.0, 1.0)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_ratings.py -v`
Expected: FAIL (`ModuleNotFoundError: copa2026.ratings`).

- [ ] **Step 3: Implementar `ratings.py`**

```python
"""Força global das 48 seleções e previsão de placar para simulações em lote.

Diferente de ``pipeline.predict_match`` (que recalcula a força por par de times),
aqui a força é calculada **uma única vez** sobre o histórico de todas as
seleções, permitindo prever as ~100 partidas do torneio sem repetir rede ou
otimização. PRD Seções 4.2–4.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain

from .data_source import MatchDataSource
from .models import TeamRatings
from .optimizer import best_guess
from .prediction import expected_goals, score_matrix
from .strength import compute_ratings, league_mu
from .teams import WORLD_CUP_2026_TEAMS, WORLD_CUP_2026_TEAMS_SET

_NEUTRO = TeamRatings(1.0, 1.0)


def compute_global_ratings(
    source: MatchDataSource,
    *,
    teams=WORLD_CUP_2026_TEAMS,
    days: int = 90,
    reg: float = 2.0,
) -> tuple[dict[str, TeamRatings], float]:
    """Coleta o histórico de todas as seleções e calcula força + mu uma vez."""
    history = list(
        dict.fromkeys(
            chain.from_iterable(source.recent_matches(t, days) for t in teams)
        )
    )
    if not history:
        raise ValueError("Sem histórico de partidas para calcular a força.")
    mu = league_mu(history)
    ratings = compute_ratings(history, WORLD_CUP_2026_TEAMS_SET, reg=reg)
    return ratings, mu


@dataclass(frozen=True)
class ScorePrediction:
    home: str
    away: str
    palpite: tuple[int, int]
    lambda_home: float
    lambda_away: float
    home_ratings: TeamRatings
    away_ratings: TeamRatings


def predict_scoreline(
    home: str,
    away: str,
    ratings: dict[str, TeamRatings],
    mu: float,
    *,
    max_goals: int = 8,
) -> ScorePrediction:
    """Palpite ótimo (max pontos esperados) a partir de ratings já calculados."""
    hr = ratings.get(home, _NEUTRO)
    ar = ratings.get(away, _NEUTRO)
    lambda_home, lambda_away = expected_goals(hr, ar, mu)
    matrix = score_matrix(lambda_home, lambda_away, max_goals)
    palpite, _ = best_guess(matrix)
    return ScorePrediction(home, away, palpite, lambda_home, lambda_away, hr, ar)


def _quality(r: TeamRatings) -> float:
    """Qualidade escalar p/ desempatar quem avança (ataque sobre fragilidade)."""
    return r.attack / r.defense if r.defense else r.attack


def knockout_winner(pred: ScorePrediction) -> tuple[str, bool]:
    """Time que avança e se a decisão foi nos pênaltis (palpite empatado).

    Palpite com vencedor -> avança quem marcou mais (sem pênaltis). Palpite
    empatado -> avança o de maior lambda; se lambda empatar, o de maior
    qualidade; rótulo 'pênaltis'.
    """
    gh, ga = pred.palpite
    if gh != ga:
        return (pred.home if gh > ga else pred.away), False
    if pred.lambda_home != pred.lambda_away:
        return (pred.home if pred.lambda_home > pred.lambda_away else pred.away), True
    if _quality(pred.home_ratings) >= _quality(pred.away_ratings):
        return pred.home, True
    return pred.away, True
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_ratings.py -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Teste de `compute_global_ratings` com fonte sintética**

```python
# adicionar em tests/test_ratings.py
from copa2026.data_source import SyntheticDataSource
from copa2026.ratings import compute_global_ratings


def test_compute_global_ratings_covers_played_teams():
    ratings, mu = compute_global_ratings(SyntheticDataSource(seed=1), days=120)
    assert mu > 0
    assert len(ratings) > 30           # maioria das seleções tem histórico
    assert all(r.attack > 0 and r.defense > 0 for r in ratings.values())
```

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests/test_ratings.py -v`
Expected: PASS (5 testes).

- [ ] **Step 7: Commit**

```bash
git add src/copa2026/ratings.py tests/test_ratings.py
git commit -m "feat: força global e predict_scoreline para simulação em lote"
```

---

## Task 2: Classificação de grupo e ranking de terceiros (`standings.py`)

**Files:**
- Create: `src/copa2026/standings.py`
- Test: `tests/test_standings.py`

**Interfaces:**
- Produces:
  - `TeamRecord` dataclass: `team, played, won, draw, lost, goals_for, goals_against`; props `points` (3V+E), `goal_diff`.
  - `compute_group_table(teams: list[str], matches: list[tuple[str,str,int,int]]) -> list[TeamRecord]` (ordenada 1º→4º; `matches` = `(home, away, home_goals, away_goals)`).
  - `rank_third_places(thirds: list[tuple[str, TeamRecord]]) -> list[tuple[str, TeamRecord]]` (recebe `(grupo, 3º colocado)`; devolve os 8 melhores, ordenados).

Critérios FIFA (PRD: novo apêndice): (1) pontos; (2) saldo geral; (3) gols pró geral; entre empatados: (4) pontos no confronto direto; (5) saldo no confronto direto; (6) gols pró no confronto direto; (7) desempate determinístico de cauda por nome (substitui fair-play/sorteio, sem dados de cartões).

- [ ] **Step 1: Testes de classificação**

```python
# tests/test_standings.py
from copa2026.standings import TeamRecord, compute_group_table, rank_third_places


def test_table_orders_by_points_then_goal_diff():
    teams = ["A", "B", "C", "D"]
    matches = [
        ("A", "B", 2, 0), ("C", "D", 1, 1),
        ("A", "C", 1, 0), ("B", "D", 0, 0),
        ("A", "D", 3, 0), ("B", "C", 1, 1),
    ]
    table = compute_group_table(teams, matches)
    assert [r.team for r in table][0] == "A"      # 9 pts
    assert table[0].points == 9
    assert table[0].goal_diff == 6


def test_head_to_head_breaks_tie_on_equal_points_and_gd():
    # X e Y empatam em pontos, saldo e gols pró; X venceu o confronto direto.
    teams = ["X", "Y", "Z", "W"]
    matches = [
        ("X", "Y", 1, 0),   # confronto direto: X vence
        ("X", "Z", 0, 2), ("X", "W", 2, 0),
        ("Y", "Z", 0, 2), ("Y", "W", 2, 0),
        ("Z", "W", 0, 0),
    ]
    table = compute_group_table(teams, matches)
    names = [r.team for r in table]
    assert names.index("X") < names.index("Y")    # X à frente pelo confronto direto


def test_rank_third_places_takes_best_eight():
    thirds = [
        (chr(ord("A") + i), TeamRecord(f"T{i}", played=3, won=w, draw=0, lost=3 - w,
                                       goals_for=gf, goals_against=0))
        for i, (w, gf) in enumerate(
            [(2, 5), (2, 4), (1, 3), (1, 2), (1, 1), (1, 0), (0, 2), (0, 1),
             (0, 0), (2, 6), (1, 4), (0, 3)]
        )
    ]
    best = rank_third_places(thirds)
    assert len(best) == 8
    groups = {g for g, _ in best}
    assert "J" in groups          # 2V, 6 gols -> entra
    assert "I" not in groups      # 0V, 0 gols -> fica de fora
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_standings.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementar `standings.py`**

```python
"""Classificação de grupo pelos critérios oficiais FIFA (PRD Apêndice).

Ordem dos critérios: pontos -> saldo geral -> gols pró geral; entre times
empatados nesses três: pontos, saldo e gols pró **apenas nos confrontos
diretos**; persistindo o empate, desempate determinístico por nome (stand-in
para fair-play/sorteio, indisponíveis sem dados de cartões).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TeamRecord:
    team: str
    played: int = 0
    won: int = 0
    draw: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return 3 * self.won + self.draw

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


def _tally(teams, matches) -> dict[str, TeamRecord]:
    rec = {t: TeamRecord(t) for t in teams}
    for home, away, gh, ga in matches:
        if home not in rec or away not in rec:
            continue
        rh, ra = rec[home], rec[away]
        rh.played += 1
        ra.played += 1
        rh.goals_for += gh
        rh.goals_against += ga
        ra.goals_for += ga
        ra.goals_against += gh
        if gh > ga:
            rh.won += 1
            ra.lost += 1
        elif gh < ga:
            ra.won += 1
            rh.lost += 1
        else:
            rh.draw += 1
            ra.draw += 1
    return rec


def compute_group_table(teams, matches) -> list[TeamRecord]:
    rec = _tally(teams, matches)

    def overall(t):
        r = rec[t]
        return (r.points, r.goal_diff, r.goals_for)

    order = sorted(teams, key=lambda t: (*[-v for v in overall(t)], t))

    final: list[str] = []
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and overall(order[j + 1]) == overall(order[i]):
            j += 1
        tied = order[i : j + 1]
        if len(tied) > 1:
            tied = _resolve_tied(tied, matches)
        final.extend(tied)
        i = j + 1
    return [rec[t] for t in final]


def _resolve_tied(tied, matches) -> list[str]:
    tset = set(tied)
    sub = [m for m in matches if m[0] in tset and m[1] in tset]
    subrec = _tally(tied, sub)

    def h2h(t):
        r = subrec[t]
        return (r.points, r.goal_diff, r.goals_for)

    return sorted(tied, key=lambda t: (*[-v for v in h2h(t)], t))


def rank_third_places(thirds) -> list[tuple[str, TeamRecord]]:
    """Os 8 melhores terceiros, por pontos -> saldo -> gols pró -> grupo."""
    return sorted(
        thirds,
        key=lambda gr: (-gr[1].points, -gr[1].goal_diff, -gr[1].goals_for, gr[0]),
    )[:8]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_standings.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add src/copa2026/standings.py tests/test_standings.py
git commit -m "feat: classificacao de grupo FIFA e ranking de terceiros"
```

---

## Task 3: Mapa de chaveamento e tabela dos terceiros (`bracket_data.py` + gerador)

**Files:**
- Create: `src/copa2026/bracket_data.py` (escrito à mão)
- Create: `scripts/generate_third_place_data.py`
- Create: `src/copa2026/third_place_data.py` (gerado pelo script)
- Test: `tests/test_bracket_data.py`

**Interfaces:**
- Produces em `bracket_data.py`:
  - `GROUPS = list("ABCDEFGHIJKL")`.
  - `Slot = tuple[str, object]` com tags: `("W", "A")` vencedor do grupo A; `("R", "A")` vice; `("3", "A")` terceiro alocado ao confronto do 1º do grupo A; `("WM", 74)` vencedor do jogo 74; `("LM", 101)` perdedor do jogo 101.
  - `MATCHES: dict[int, tuple[Slot, Slot]]` (jogos 73–104).
  - `STAGE_OF: dict[int, str]` (LAST_32/LAST_16/QUARTER_FINALS/SEMI_FINALS/THIRD_PLACE/FINAL).
  - `WINNERS_FACING_THIRD = ["A", "B", "D", "E", "G", "I", "K", "L"]`.
- Produces em `third_place_data.py`: `BEST_THIRD_ALLOCATION: dict[str, dict[str, str]]` — chave = 8 letras de grupo ordenadas (ex.: `"EFGHIJKL"`), valor = `{grupo_do_1º: grupo_do_3º}` para os 8 confrontos.

- [ ] **Step 1: Escrever `bracket_data.py` (dados fixos, sem rede)**

```python
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
```

- [ ] **Step 2: Escrever o gerador `scripts/generate_third_place_data.py`**

```python
"""Gera src/copa2026/third_place_data.py a partir da tabela oficial da Wikipédia.

A tabela dos 8 melhores terceiros (495 combinações) está no template
`Template:2026 FIFA World Cup third-place table`. Cada linha lista, em negrito,
os 8 grupos cujos terceiros avançam e, em 8 colunas (1A,1B,1D,1E,1G,1I,1K,1L),
qual terceiro (3X) enfrenta cada um desses primeiros colocados.

Rodar:  python scripts/generate_third_place_data.py
"""

from __future__ import annotations

import re
from pathlib import Path

import requests

WINNERS = ["A", "B", "D", "E", "G", "I", "K", "L"]
URL = (
    "https://en.wikipedia.org/w/index.php"
    "?title=Template:2026_FIFA_World_Cup_third-place_table&action=raw"
)
OUT = Path(__file__).resolve().parents[1] / "src" / "copa2026" / "third_place_data.py"


def parse(wikitext: str) -> dict[str, dict[str, str]]:
    blocks = re.split(r'!\s*scope="row"', wikitext)[1:]
    alloc: dict[str, dict[str, str]] = {}
    for block in blocks:
        groups = re.findall(r"'''([A-L])'''", block)
        thirds = re.findall(r"\b3([A-L])\b", block)
        if len(groups) != 8 or len(thirds) != 8:
            continue
        key = "".join(sorted(groups))
        if set(thirds) != set(groups):
            raise ValueError(f"linha inconsistente: {key} -> {thirds}")
        alloc[key] = dict(zip(WINNERS, thirds))
    if len(alloc) != 495:
        raise ValueError(f"esperado 495 combinações, obtido {len(alloc)}")
    return alloc


def main() -> None:
    text = requests.get(URL, timeout=30, headers={"User-Agent": "copa2026/1.0"}).text
    alloc = parse(text)
    lines = [
        '"""Tabela oficial dos 8 melhores terceiros (PRD §4.4).',
        "",
        "GERADO por scripts/generate_third_place_data.py — não editar à mão.",
        "Chave: 8 letras de grupo ordenadas. Valor: {grupo do 1º: grupo do 3º}.",
        '"""',
        "",
        "BEST_THIRD_ALLOCATION: dict[str, dict[str, str]] = {",
    ]
    for key in sorted(alloc):
        lines.append(f"    {key!r}: {alloc[key]!r},")
    lines.append("}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(alloc)} combinações escritas em {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Rodar o gerador (única etapa com rede)**

Run: `python scripts/generate_third_place_data.py`
Expected: imprime `495 combinações escritas em .../third_place_data.py` e cria o arquivo.

- [ ] **Step 4: Teste de estrutura do chaveamento e da tabela**

```python
# tests/test_bracket_data.py
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
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_bracket_data.py -v`
Expected: PASS (5 testes).

- [ ] **Step 6: Commit**

```bash
git add src/copa2026/bracket_data.py src/copa2026/third_place_data.py \
        scripts/generate_third_place_data.py tests/test_bracket_data.py
git commit -m "feat: mapa de chaveamento + tabela oficial dos 8 melhores terceiros"
```

---

## Task 4: Fixtures da competição (`FixtureMatch`, parser, fetch) em `tournament.py` + `data_source.py`

**Files:**
- Create: `src/copa2026/tournament.py` (parte 1: modelo + parser + fetch)
- Modify: `src/copa2026/data_source.py` (novo método `competition_matches`)
- Test: `tests/test_tournament.py` (parte 1)

**Interfaces:**
- Produces em `tournament.py`:
  - `FixtureMatch` dataclass: `stage: str, group: str | None, home: str | None, away: str | None, home_goals: int | None, away_goals: int | None, status: str, winner: str | None, utc_date: str`.
  - `parse_fixtures(payload: dict) -> list[FixtureMatch]` (converte resposta da API; aplica `canonical_name` aos nomes não nulos).
  - `fetch_wc_fixtures(source: FootballDataSource) -> list[FixtureMatch]`.
- Produces em `data_source.py`:
  - `FootballDataSource.competition_matches() -> dict` → `self._get(f"/competitions/{self.competition}/matches")`.

- [ ] **Step 1: Teste do parser com payload de exemplo**

```python
# tests/test_tournament.py
from copa2026.tournament import FixtureMatch, parse_fixtures


SAMPLE = {
    "matches": [
        {
            "stage": "GROUP_STAGE", "group": "GROUP_A", "status": "FINISHED",
            "utcDate": "2026-06-11T20:00:00Z",
            "homeTeam": {"name": "Mexico"}, "awayTeam": {"name": "South Africa"},
            "score": {"winner": "HOME_TEAM", "duration": "REGULAR",
                      "fullTime": {"home": 2, "away": 0}},
        },
        {
            "stage": "LAST_32", "group": None, "status": "TIMED",
            "utcDate": "2026-06-28T19:00:00Z",
            "homeTeam": {"name": None}, "awayTeam": {"name": None},
            "score": {"winner": None, "duration": "REGULAR",
                      "fullTime": {"home": None, "away": None}},
        },
    ]
}


def test_parse_fixtures_group_match():
    fx = parse_fixtures(SAMPLE)
    g = fx[0]
    assert isinstance(g, FixtureMatch)
    assert g.stage == "GROUP_STAGE" and g.group == "GROUP_A"
    assert g.home == "Mexico" and g.away == "South Africa"
    assert g.home_goals == 2 and g.away_goals == 0
    assert g.status == "FINISHED" and g.winner == "HOME_TEAM"


def test_parse_fixtures_keeps_unresolved_knockout():
    fx = parse_fixtures(SAMPLE)
    ko = fx[1]
    assert ko.stage == "LAST_32"
    assert ko.home is None and ko.away is None
    assert ko.home_goals is None and ko.status == "TIMED"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_tournament.py -v`
Expected: FAIL (`ModuleNotFoundError: copa2026.tournament`).

- [ ] **Step 3: Implementar parser/fetch em `tournament.py` e método na fonte**

Em `src/copa2026/tournament.py`:

```python
"""Orquestração da tabela da Copa: real (API) + previsto até a final.

A força é calculada uma vez (``ratings``); cada jogo da fase de grupos usa o
placar real se disputado, senão o previsto; o mata-mata é montado pelo mapa
fixo (``bracket_data``) e propagado por lambda até a final (PRD §4).
"""

from __future__ import annotations

from dataclasses import dataclass

from .data_source import FootballDataSource, canonical_name


@dataclass(frozen=True)
class FixtureMatch:
    stage: str
    group: str | None
    home: str | None
    away: str | None
    home_goals: int | None
    away_goals: int | None
    status: str
    winner: str | None
    utc_date: str


def _name(team: dict) -> str | None:
    raw = team.get("name")
    return canonical_name(raw) if raw else None


def parse_fixtures(payload: dict) -> list[FixtureMatch]:
    out: list[FixtureMatch] = []
    for m in payload.get("matches", []):
        full = m["score"]["fullTime"]
        out.append(
            FixtureMatch(
                stage=m["stage"],
                group=m.get("group"),
                home=_name(m["homeTeam"]),
                away=_name(m["awayTeam"]),
                home_goals=full["home"],
                away_goals=full["away"],
                status=m["status"],
                winner=m["score"].get("winner"),
                utc_date=m["utcDate"],
            )
        )
    return out


def fetch_wc_fixtures(source: FootballDataSource) -> list[FixtureMatch]:
    return parse_fixtures(source.competition_matches())
```

Em `src/copa2026/data_source.py`, dentro de `class FootballDataSource`, após `recent_matches`:

```python
    def competition_matches(self) -> dict:
        """Todos os jogos da competição (calendário + resultados + chaveamento)."""
        return self._get(f"/competitions/{self.competition}/matches")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_tournament.py -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/copa2026/tournament.py src/copa2026/data_source.py tests/test_tournament.py
git commit -m "feat: FixtureMatch + parser + competition_matches da API"
```

---

## Task 5: Simulação do torneio (`simulate_tournament`)

**Files:**
- Modify: `src/copa2026/tournament.py` (adicionar simulação)
- Test: `tests/test_tournament.py` (adicionar)

**Interfaces:**
- Consumes: `ScorePrediction`, `predict_scoreline`, `knockout_winner` (`ratings.py`); `TeamRecord`, `compute_group_table`, `rank_third_places` (`standings.py`); `MATCHES`, `STAGE_OF`, `GROUPS` (`bracket_data.py`); `BEST_THIRD_ALLOCATION` (`third_place_data.py`).
- Produces:
  - `GroupResult` dataclass: `group: str, table: list[TeamRecord]`.
  - `KnockoutResult` dataclass: `match_no: int, stage: str, home: str, away: str, home_goals: int, away_goals: int, winner: str, loser: str, real: bool, penalties: bool`.
  - `TournamentResult` dataclass: `groups: list[GroupResult], knockout: list[KnockoutResult], third_key: str`.
  - `simulate_tournament(fixtures: list[FixtureMatch], ratings, mu, *, max_goals=8) -> TournamentResult`.

Notas de algoritmo:
- Membros de cada grupo derivam dos jogos `GROUP_STAGE` (campos `home`/`away`).
- Jogo de grupo: real se `status == "FINISHED"` (usa `home_goals`/`away_goals`), senão previsto via `predict_scoreline`.
- Os 8 melhores terceiros → chave ordenada → `BEST_THIRD_ALLOCATION[key]`.
- Iterar match 73→104 em ordem crescente garante que `("WM", n)`/`("LM", n)` já estejam resolvidos.
- Resultado real de mata-mata: casar por **ordem cronológica dentro da fase** (limitação documentada — a API não liga jogo a slot).

- [ ] **Step 1: Testes da simulação (grupos previstos, propagação, pênaltis, real sobrepõe)**

```python
# adicionar em tests/test_tournament.py
from copa2026.bracket_data import GROUPS
from copa2026.models import TeamRatings
from copa2026.tournament import simulate_tournament


def _group_fixtures(all_finished=False, results=None):
    """Gera os 72 jogos de grupo (todos os pares dentro de cada grupo)."""
    teams = {g: [f"{g}{i}" for i in range(1, 5)] for g in GROUPS}
    fx = []
    for g, ts in teams.items():
        for i in range(4):
            for j in range(i + 1, 4):
                h, a = ts[i], ts[j]
                gh = ga = None
                status = "TIMED"
                if all_finished:
                    gh, ga = (results or {}).get((h, a), (1, 0))
                    status = "FINISHED"
                fx.append(_fx("GROUP_STAGE", g, h, a, gh, ga, status))
    return fx, teams


def _fx(stage, group, home, away, gh, ga, status, utc="2026-06-15T00:00:00Z"):
    from copa2026.tournament import FixtureMatch
    winner = None
    if status == "FINISHED" and gh is not None:
        winner = "HOME_TEAM" if gh > ga else "AWAY_TEAM" if ga > gh else "DRAW"
    return FixtureMatch(stage, group, home, away, gh, ga, status, winner, utc)


def _ko_placeholders():
    fx = []
    for no in range(73, 105):
        from copa2026.bracket_data import STAGE_OF
        fx.append(_fx(STAGE_OF[no], None, None, None, None, None, "TIMED",
                      utc=f"2026-06-28T{no % 24:02d}:00:00Z"))
    return fx


def _ratings_by_group(teams):
    # 1º de cada grupo mais forte; força decrescente por índice
    r = {}
    for g, ts in teams.items():
        for k, t in enumerate(ts):
            r[t] = TeamRatings(attack=1.6 - 0.2 * k, defense=0.7 + 0.2 * k)
    return r


def test_simulate_fills_full_bracket_to_final():
    gfx, teams = _group_fixtures()
    fixtures = gfx + _ko_placeholders()
    res = simulate_tournament(fixtures, _ratings_by_group(teams), mu=1.3)
    assert len(res.groups) == 12
    assert {k.match_no for k in res.knockout} == set(range(73, 105))
    final = next(k for k in res.knockout if k.match_no == 104)
    assert final.winner and final.winner != final.loser
    assert all(not k.real for k in res.knockout)     # nada disputado ainda


def test_real_group_result_overrides_prediction():
    # força o 4º colocado teórico a vencer todos -> vira 1º real
    teams = {g: [f"{g}{i}" for i in range(1, 5)] for g in GROUPS}
    results = {}
    for g, ts in teams.items():
        for i in range(4):
            for j in range(i + 1, 4):
                # time de maior índice vence sempre
                results[(ts[i], ts[j])] = (0, 3)
    gfx, teams = _group_fixtures(all_finished=True, results=results)
    res = simulate_tournament(gfx + _ko_placeholders(), _ratings_by_group(teams), mu=1.3)
    a = next(gr for gr in res.groups if gr.group == "A")
    assert a.table[0].team == "A4"     # resultado real prevalece sobre a força


def test_real_knockout_result_is_marked_and_propagated():
    gfx, teams = _group_fixtures()
    ko = []
    from copa2026.bracket_data import STAGE_OF
    for no in range(73, 105):
        if no == 73:
            ko.append(_fx("LAST_32", None, "X", "Y", 1, 0, "FINISHED",
                          utc="2026-06-28T00:00:00Z"))
        else:
            ko.append(_fx(STAGE_OF[no], None, None, None, None, None, "TIMED",
                          utc=f"2026-06-29T{no % 24:02d}:00:00Z"))
    res = simulate_tournament(gfx + ko, _ratings_by_group(teams), mu=1.3)
    m73 = next(k for k in res.knockout if k.match_no == 73)
    assert m73.real is True
    assert m73.winner == "X"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_tournament.py -v`
Expected: FAIL (`AttributeError`/`ImportError`: `simulate_tournament` ausente).

- [ ] **Step 3: Implementar a simulação em `tournament.py`**

Adicionar imports no topo de `tournament.py`:

```python
from .bracket_data import GROUPS, MATCHES, STAGE_OF
from .ratings import predict_scoreline, knockout_winner
from .standings import TeamRecord, compute_group_table, rank_third_places
from .third_place_data import BEST_THIRD_ALLOCATION
```

Adicionar ao final de `tournament.py`:

```python
@dataclass(frozen=True)
class GroupResult:
    group: str
    table: list[TeamRecord]


@dataclass(frozen=True)
class KnockoutResult:
    match_no: int
    stage: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    winner: str
    loser: str
    real: bool
    penalties: bool


@dataclass(frozen=True)
class TournamentResult:
    groups: list[GroupResult]
    knockout: list[KnockoutResult]
    third_key: str


def _group_members(fixtures) -> dict[str, list[str]]:
    members: dict[str, list[str]] = {g: [] for g in GROUPS}
    for f in fixtures:
        if f.stage != "GROUP_STAGE":
            continue
        letter = f.group.removeprefix("GROUP_")
        for team in (f.home, f.away):
            if team and team not in members[letter]:
                members[letter].append(team)
    return members


def _group_scorelines(fixtures, ratings, mu, max_goals):
    """(grupo -> lista de (home, away, gh, ga)) com real ou previsto."""
    by_group: dict[str, list[tuple[str, str, int, int]]] = {g: [] for g in GROUPS}
    for f in fixtures:
        if f.stage != "GROUP_STAGE":
            continue
        letter = f.group.removeprefix("GROUP_")
        if f.status == "FINISHED" and f.home_goals is not None:
            gh, ga = f.home_goals, f.away_goals
        else:
            gh, ga = predict_scoreline(f.home, f.away, ratings, mu,
                                       max_goals=max_goals).palpite
        by_group[letter].append((f.home, f.away, gh, ga))
    return by_group


def _api_knockout_by_match(fixtures) -> dict[int, "FixtureMatch"]:
    """Casa jogos de mata-mata da API aos números de jogo por ordem cronológica
    dentro de cada fase (a API não liga jogo a slot — limitação documentada)."""
    mapping: dict[int, FixtureMatch] = {}
    for stage in {STAGE_OF[n] for n in MATCHES}:
        numbers = sorted(n for n in MATCHES if STAGE_OF[n] == stage)
        api = sorted(
            (f for f in fixtures if f.stage == stage),
            key=lambda f: f.utc_date,
        )
        for no, fx in zip(numbers, api):
            mapping[no] = fx
    return mapping


def simulate_tournament(fixtures, ratings, mu, *, max_goals: int = 8) -> TournamentResult:
    members = _group_members(fixtures)
    scorelines = _group_scorelines(fixtures, ratings, mu, max_goals)

    tables = {g: compute_group_table(members[g], scorelines[g]) for g in GROUPS}
    groups = [GroupResult(g, tables[g]) for g in GROUPS]

    winner_of = {g: tables[g][0].team for g in GROUPS}
    runner_of = {g: tables[g][1].team for g in GROUPS}
    third_rec = {g: tables[g][2] for g in GROUPS}

    best_thirds = rank_third_places([(g, third_rec[g]) for g in GROUPS])
    third_key = "".join(sorted(g for g, _ in best_thirds))
    alloc = BEST_THIRD_ALLOCATION[third_key]   # {grupo do 1º: grupo do 3º}

    api_ko = _api_knockout_by_match(fixtures)
    results: dict[int, KnockoutResult] = {}

    def resolve(slot) -> str:
        tag, val = slot
        if tag == "W":
            return winner_of[val]
        if tag == "R":
            return runner_of[val]
        if tag == "3":
            return tables[alloc[val]][2].team
        if tag == "WM":
            return results[val].winner
        if tag == "LM":
            return results[val].loser

    for no in sorted(MATCHES):
        slot_a, slot_b = MATCHES[no]
        home, away = resolve(slot_a), resolve(slot_b)
        fx = api_ko.get(no)
        if fx and fx.status == "FINISHED" and fx.home_goals is not None and fx.home:
            home, away = fx.home, fx.away
            gh, ga = fx.home_goals, fx.away_goals
            winner = home if fx.winner == "HOME_TEAM" else away
            penalties = fx.winner not in ("HOME_TEAM", "AWAY_TEAM") and gh == ga
            real = True
        else:
            pred = predict_scoreline(home, away, ratings, mu, max_goals=max_goals)
            gh, ga = pred.palpite
            winner, penalties = knockout_winner(pred)
            real = False
        loser = away if winner == home else home
        results[no] = KnockoutResult(no, STAGE_OF[no], home, away, gh, ga,
                                     winner, loser, real, penalties)

    knockout = [results[no] for no in sorted(results)]
    return TournamentResult(groups, knockout, third_key)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_tournament.py -v`
Expected: PASS (5 testes).

- [ ] **Step 5: Rodar a suíte completa**

Run: `python -m pytest -q`
Expected: PASS (toda a suíte verde).

- [ ] **Step 6: Commit**

```bash
git add src/copa2026/tournament.py tests/test_tournament.py
git commit -m "feat: simulate_tournament (grupos FIFA + chaveamento ate a final)"
```

---

## Task 6: Aba "Tabela da Copa" no Streamlit (`app.py`)

**Files:**
- Modify: `app.py`
- Test: `tests/test_tournament.py` (helper de render puro, sem Streamlit)

**Interfaces:**
- Consumes: `compute_global_ratings` (`ratings.py`), `fetch_wc_fixtures`, `simulate_tournament`, `TournamentResult` (`tournament.py`), `display_pt` (`teams.py`), `STAGE_LABEL_PT`, `STAGE_OF` (`bracket_data.py`).
- Produces em `app.py`: função pura `_knockout_rows(result) -> dict[str, list[dict]]` (fase → linhas para exibição), testável sem Streamlit; e a renderização da aba.

- [ ] **Step 1: Teste da função pura de linhas do mata-mata**

```python
# adicionar em tests/test_tournament.py
def test_knockout_rows_groups_by_stage_label():
    import app
    gfx, teams = _group_fixtures()
    res = simulate_tournament(gfx + _ko_placeholders(), _ratings_by_group(teams), mu=1.3)
    rows = app._knockout_rows(res)
    assert "Final" in rows
    assert len(rows["16 avos de final"]) == 16
    linha = rows["Final"][0]
    assert {"Jogo", "Placar", "Origem"} <= set(linha)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_tournament.py::test_knockout_rows_groups_by_stage_label -v`
Expected: FAIL (`AttributeError: module 'app' has no attribute '_knockout_rows'`).

- [ ] **Step 3: Implementar `_knockout_rows` e a aba em `app.py`**

Adicionar imports (junto aos demais, após `_load_env_file`):

```python
from copa2026.bracket_data import STAGE_LABEL_PT, STAGE_OF  # noqa: E402
from copa2026.ratings import compute_global_ratings  # noqa: E402
from copa2026.tournament import (  # noqa: E402
    TournamentResult,
    fetch_wc_fixtures,
    simulate_tournament,
)
from copa2026.data_source import FootballDataSource  # noqa: E402
```

Adicionar a função pura (nível de módulo):

```python
_STAGE_ORDER = ["LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS",
                "THIRD_PLACE", "FINAL"]


def _knockout_rows(result: TournamentResult) -> dict[str, list[dict]]:
    """Linhas de exibição do mata-mata, agrupadas por rótulo de fase (em ordem)."""
    rows: dict[str, list[dict]] = {STAGE_LABEL_PT[s]: [] for s in _STAGE_ORDER}
    for k in result.knockout:
        origem = "✅ Real" if k.real else "🔮 Previsto"
        placar = f"{k.home_goals} x {k.away_goals}"
        if k.penalties:
            placar += " (pên.)"
        rows[STAGE_LABEL_PT[k.stage]].append(
            {
                "Jogo": f"{display_pt(k.home)} x {display_pt(k.away)}",
                "Placar": placar,
                "Avança": display_pt(k.winner),
                "Origem": origem,
            }
        )
    return rows
```

Adicionar a busca cacheada e a renderização da aba. Envolver o corpo atual (linhas 92–177 do `app.py` original — título, seletor e resultado da previsão ponto-a-ponto) dentro de `with aba_previsor:`; criar `with aba_tabela:`. Estrutura:

```python
@st.cache_data(ttl=600, show_spinner="Buscando jogos e simulando o torneio...")
def _run_tournament(fd_api_key: str) -> TournamentResult:
    source = FootballDataSource(api_key=fd_api_key)
    fixtures = fetch_wc_fixtures(source)
    combined = CombinedDataSource(HardcodedDataSource(), source)
    ratings, mu = compute_global_ratings(combined)
    return simulate_tournament(fixtures, ratings, mu)


def _render_tabela(fd_api_key: str) -> None:
    st.subheader("🏆 Tabela da Copa — real + previsto")
    if not fd_api_key:
        st.info(
            "Defina FOOTBALL_DATA_API_KEY no .env para montar a tabela com os "
            "jogos e resultados reais da Copa."
        )
        return
    if st.button("🔄 Atualizar resultados"):
        _run_tournament.clear()
    try:
        result = _run_tournament(fd_api_key)
    except Exception as exc:  # rede/API
        st.error(f"Falha ao montar a tabela: {exc}")
        return

    st.markdown("### Fase de grupos")
    cols = st.columns(3)
    for idx, gr in enumerate(result.groups):
        with cols[idx % 3]:
            st.caption(f"Grupo {gr.group}")
            df = pd.DataFrame(
                [
                    {
                        "Seleção": display_pt(r.team), "P": r.points,
                        "J": r.played, "SG": r.goal_diff, "GP": r.goals_for,
                    }
                    for r in gr.table
                ]
            )
            st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("### Mata-mata")
    st.caption("✅ Real = já disputado · 🔮 Previsto = palpite do modelo")
    for label, linhas in _knockout_rows(result).items():
        if not linhas:
            continue
        st.markdown(f"**{label}**")
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
```

Logo após o `st.caption(...)` do título principal (linha ~96), criar as abas e indentar o conteúdo existente:

```python
aba_previsor, aba_tabela = st.tabs(["🎯 Previsor de placar", "🏆 Tabela da Copa"])

with aba_previsor:
    # ... (todo o conteúdo atual: seletor de times, métricas, heatmap, histórico) ...

with aba_tabela:
    _render_tabela(fd_api_key)
```

(O `st.divider()`/legenda final do rodapé permanecem fora das abas.)

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_tournament.py::test_knockout_rows_groups_by_stage_label -v`
Expected: PASS.

- [ ] **Step 5: Verificar que o app importa sem erro de sintaxe**

Run: `python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('ok')"`
Expected: imprime `ok`.

- [ ] **Step 6: Rodar a suíte completa**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app.py tests/test_tournament.py
git commit -m "feat: aba Tabela da Copa no Streamlit (grupos + mata-mata)"
```

---

## Task 7: Documentação, limpeza e verificação final

**Files:**
- Modify: `prd.md` (nova seção)
- Modify: `CLAUDE.md` (citar a aba e os novos módulos)
- Delete: `docs/tabela_copa2026/` (PDF não renderizável e redundante com a API)

- [ ] **Step 1: Remover o PDF**

```bash
git rm -r --ignore-unmatch docs/tabela_copa2026
rm -rf docs/tabela_copa2026
```

(O PDF estava em `docs/` ainda não versionado; `rm -rf` garante a remoção do diretório.)

- [ ] **Step 2: Adicionar seção ao `prd.md`**

Acrescentar ao final (antes do Apêndice A, ou como nova seção numerada) um bloco descrevendo a feature: objetivo da aba, fonte (API `competitions/WC/matches`), regra de mistura real/previsto, classificação FIFA (critérios 1–6 + desempate determinístico de cauda), tabela oficial dos 8 melhores terceiros, propagação por λ e resolução de empate no mata-mata por λ/qualidade com rótulo "(pênaltis)". Referenciar `ratings.py`, `standings.py`, `bracket_data.py`, `third_place_data.py`, `tournament.py`.

- [ ] **Step 3: Atualizar `CLAUDE.md`**

Na seção "Arquitetura", acrescentar as linhas dos novos módulos:

```
- `ratings.py` — força global (1×) + `predict_scoreline` (PRD §4.2–4.4).
- `standings.py` — classificação de grupo (regras FIFA).
- `bracket_data.py` — mapa fixo do chaveamento (escrito à mão).
- `third_place_data.py` — tabela dos 8 melhores terceiros (**gerada**).
- `tournament.py` — simulação da tabela (real + previsto).
```

E em "Dados", citar: regenerar a tabela dos terceiros com `python scripts/generate_third_place_data.py`.

- [ ] **Step 4: Verificação final — suíte completa + lint de import**

Run: `python -m pytest -q`
Expected: PASS (toda a suíte).

Run: `python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add prd.md CLAUDE.md docs/tabela_copa2026
git commit -m "docs: descreve a aba Tabela da Copa e remove PDF redundante"
```

---

## Self-review (verificação do plano contra o spec)

- **Cobertura do spec:** aba nova (T6) ✓; fonte API + mistura real/previsto (T4/T5) ✓; chaveamento embutido + tabela dos terceiros (T3) ✓; classificação FIFA (T2) ✓; força global/performance (T1) ✓; atualização por refresh + cache + botão (T6) ✓; "sempre acerta o vencedor"/empate por λ com pênaltis (T1/T5) ✓; remoção do PDF (T7) ✓; testes sem rede (T1–T6) ✓.
- **Desvio consciente do spec:** o `fixtures_data.py` de fallback offline foi removido do escopo (YAGNI — a produção tem a chave; sem chave a aba exibe aviso). Testes usam fixtures sintéticos, não o fallback.
- **Consistência de tipos:** `predict_scoreline`/`ScorePrediction`/`knockout_winner` (T1) usados em T5; `TeamRecord`/`compute_group_table`/`rank_third_places` (T2) usados em T5; `MATCHES`/`STAGE_OF`/`GROUPS`/`WINNERS_FACING_THIRD` (T3) e `BEST_THIRD_ALLOCATION` (T3) usados em T5; `FixtureMatch`/`fetch_wc_fixtures`/`simulate_tournament`/`TournamentResult` (T4/T5) usados em T6. Nomes conferidos entre tarefas.
- **Limitação documentada:** resultado real de mata-mata casado por ordem cronológica dentro da fase (a API não liga jogo a slot); com zero jogos de KO disputados hoje (28/jun em diante), o caminho real de KO é exercitado por teste sintético.
