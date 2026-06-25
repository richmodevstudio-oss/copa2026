# Artigo + Análise (backtest + probabilidade de título) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um artigo LaTeX (pasta `artigo/`) que documenta a metodologia e apresenta um backtest walk-forward (grau de confiança = taxa de acerto) e a probabilidade de cada seleção ser campeã (DP sobre o chaveamento), com um script Python regenerável que produz as tabelas/figuras.

**Architecture:** Dois módulos puros novos (`backtest.py`, `championship.py`) e um de formatação LaTeX (`relatorio.py`), todos testáveis sem rede. Um script (`scripts/gerar_analise.py`) faz 1 chamada à API, calcula tudo e escreve os artefatos `.tex`/figura que o artigo inclui via `\input`. A força (ratings) usa só dados reais; o "mock" da fase de grupos serve apenas para fixar os confrontos do R32.

**Tech Stack:** Python 3 (numpy, scipy, requests, matplotlib), pytest (TDD, `pythonpath=src`), LaTeX (MiKTeX: `pdflatex`/`latexmk`).

## Global Constraints

- Pacote em `src/copa2026/`; `pythonpath = src` no `pytest.ini`; rodar testes com `python -m pytest` na raiz.
- Strings de UI/artigo e docstrings em **português**; nomes canônicos das seleções em inglês.
- TDD; testes **sem rede** (dados sintéticos/injetados).
- Ratings calculados **só com dados reais** (pré-Copa + jogos reais da Copa); jogos previstos/mock **nunca** entram na força.
- `matplotlib` já é dependência (`requirements.txt`); **não** adicionar dependências novas.
- Artefatos gerados (`artigo/gerado/*.tex`, figura) são **commitados**.

---

## Contexto do código existente (não re-investigar)

- `src/copa2026/models.py`: `Match(home, away, home_goals, away_goals, played_on: date|None)` (frozen); `TeamRatings(attack, defense)` (frozen).
- `src/copa2026/strength.py`: `league_mu(matches) -> float`; `compute_ratings(matches, wc_teams, *, external_attack=0.5, external_defense=1.5, reg=0.0, max_iter=500, tol=1e-9) -> dict[str, TeamRatings]`.
- `src/copa2026/prediction.py`: `expected_goals(home: TeamRatings, away: TeamRatings, mu) -> (float,float)` (λ_casa=μ·O_casa·D_fora; sem fator de mando); `score_matrix(lambda_home, lambda_away, max_goals=8) -> np.ndarray` (`P[x,y]`, x=gols casa na linha).
- `src/copa2026/teams.py`: `WORLD_CUP_2026_TEAMS_SET` (frozenset); `display_pt(nome) -> str` (rótulo PT).
- `src/copa2026/pre_wc_data.py`: `PRE_WC_MATCHES: list[tuple[str,str,str,int,int]]` = `(data_iso, mandante, visitante, gols_casa, gols_fora)`, ex.: `('2026-06-10','Argentina','Iceland',3,0)`.
- `src/copa2026/bracket_data.py`: `MATCHES: dict[int, (slotA, slotB)]` (jogos 73–104; slots `("W"/"R"/"3", grupo)`, `("WM"/"LM", n)`); `STAGE_OF: dict[int,str]` (LAST_32/LAST_16/QUARTER_FINALS/SEMI_FINALS/THIRD_PLACE/FINAL).
- `src/copa2026/tournament.py`: `FixtureMatch(stage, group, home, away, home_goals, away_goals, status, winner, utc_date, duration=None)`; `fetch_wc_fixtures(source) -> list[FixtureMatch]`; `finished_results(fixtures) -> list[tuple]`; `simulate_tournament(fixtures, ratings, mu) -> TournamentResult` com `.knockout: list[KnockoutResult]` onde `KnockoutResult` tem `match_no, stage, home, away, ...`. Os jogos 73–88 carregam os confrontos do R32 já determinados.
- `src/copa2026/data_source.py`: `FootballDataSource(api_key=...)`, `HardcodedDataSource(matches=None, *, last=12)`, `CombinedDataSource(*sources)`, `competition_matches()`.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/copa2026/backtest.py` | `outcome_probabilities`, `ratings_asof`, `walk_forward_backtest` + dataclasses |
| `src/copa2026/championship.py` | `prob_vitoria`, `probabilidades_titulo` (DP) |
| `src/copa2026/relatorio.py` | formatadores LaTeX puros (`macros_tex`, `tabela_backtest_tex`, `tabela_titulo_tex`) |
| `scripts/gerar_analise.py` | orquestra (1 chamada à API) e escreve os artefatos |
| `artigo/previsor-copa-2026.tex` | artigo principal |
| `artigo/gerado/{dados,backtest,titulo}.tex` | gerados, incluídos via `\input` |
| `artigo/figuras/titulo.pdf` | figura gerada (matplotlib) |
| `artigo/.gitignore` | ignora `*.aux/*.log/*.out/*.fls/*.fdb_latexmk` e o PDF de build |
| `tests/test_backtest.py`, `tests/test_championship.py`, `tests/test_relatorio.py` | testes |
| `prd.md`, `README.md` | nota apontando para o artigo |

---

## Task 1: `backtest.py` — `outcome_probabilities` + `ratings_asof`

**Files:**
- Create: `src/copa2026/backtest.py`
- Test: `tests/test_backtest.py`

**Interfaces:**
- Produces:
  - `outcome_probabilities(matrix: np.ndarray) -> tuple[float, float, float]` → `(p_casa, p_empate, p_fora)`.
  - `ratings_asof(corte: date, partidas: list[Match], *, janela: int = 90, reg: float = 2.0) -> tuple[dict[str, TeamRatings], float]`.

- [ ] **Step 1: Testes**

```python
# tests/test_backtest.py
from datetime import date

import numpy as np

from copa2026.backtest import outcome_probabilities, ratings_asof
from copa2026.models import Match


def test_outcome_probabilities_buckets_and_sum():
    # P[x,y], x=gols casa (linha). Massa: (2,0)=casa, (1,1)=empate, (0,2)=fora.
    m = np.zeros((3, 3))
    m[2, 0] = 0.5   # casa vence
    m[1, 1] = 0.3   # empate
    m[0, 2] = 0.2   # fora vence
    p_casa, p_empate, p_fora = outcome_probabilities(m)
    assert abs(p_casa - 0.5) < 1e-9
    assert abs(p_empate - 0.3) < 1e-9
    assert abs(p_fora - 0.2) < 1e-9
    assert abs((p_casa + p_empate + p_fora) - 1.0) < 1e-9


def _amistosos(n, d):
    # n jogos no mesmo dia d entre seleções da Copa, com placares variados.
    jogos = []
    times = ["Brazil", "France", "Spain", "England"]
    for i in range(n):
        h, a = times[i % 4], times[(i + 1) % 4]
        jogos.append(Match(h, a, (i % 3) + 1, i % 2, d))
    return jogos


def test_ratings_asof_ignores_future_matches():
    corte = date(2026, 6, 1)
    passado = _amistosos(8, date(2026, 5, 1))
    futuro = [Match("Brazil", "Spain", 5, 0, date(2026, 6, 2))]  # após o corte
    r1, mu1 = ratings_asof(corte, passado)
    r2, mu2 = ratings_asof(corte, passado + futuro)
    assert mu1 == mu2
    assert r1 == r2


def test_ratings_asof_empty_window_raises():
    corte = date(2026, 6, 1)
    antigo = _amistosos(4, date(2026, 1, 1))  # fora da janela de 90 dias
    try:
        ratings_asof(corte, antigo)
        assert False, "esperava ValueError"
    except ValueError:
        pass
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_backtest.py -v`
Expected: FAIL (`ModuleNotFoundError: copa2026.backtest`).

- [ ] **Step 3: Implementar (parte 1) `backtest.py`**

```python
"""Verificação regressiva (backtest walk-forward) do previsor.

Para cada jogo já disputado, prevê o resultado (Vitória casa / Empate / Vitória
fora) usando apenas dados anteriores ao jogo e compara com o real. O grau de
confiança empírico é a taxa de acerto. Probabilidades de resultado vêm da matriz
de placares de Poisson (PRD §4.3); aqui não importa o placar exato.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from .models import Match
from .strength import compute_ratings, league_mu
from .teams import WORLD_CUP_2026_TEAMS_SET


def outcome_probabilities(matrix: np.ndarray) -> tuple[float, float, float]:
    """(p_casa, p_empate, p_fora) somando a matriz de placares por região.

    ``P[x, y]`` com ``x`` = gols da casa (linha): casa vence abaixo da diagonal,
    empate na diagonal, fora vence acima.
    """
    p_empate = float(np.trace(matrix))
    p_casa = float(np.tril(matrix, -1).sum())
    p_fora = float(np.triu(matrix, 1).sum())
    return p_casa, p_empate, p_fora


def ratings_asof(
    corte: date,
    partidas: list[Match],
    *,
    janela: int = 90,
    reg: float = 2.0,
) -> tuple[dict, float]:
    """Força (ataque/defesa) e mu calculados com a janela ``[corte-janela, corte)``.

    Função pura: depende só de ``corte`` e ``partidas`` (sem ``date.today()``),
    o que torna o backtest walk-forward isento de viés de futuro.
    """
    inicio = corte - timedelta(days=janela)
    janela_partidas = [
        m for m in partidas
        if m.played_on is not None and inicio <= m.played_on < corte
    ]
    if not janela_partidas:
        raise ValueError(f"janela vazia até {corte.isoformat()}")
    mu = league_mu(janela_partidas)
    ratings = compute_ratings(janela_partidas, WORLD_CUP_2026_TEAMS_SET, reg=reg)
    return ratings, mu
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_backtest.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add src/copa2026/backtest.py tests/test_backtest.py
git commit -m "feat: outcome_probabilities e ratings_asof (base do backtest)"
```

---

## Task 2: `backtest.py` — `walk_forward_backtest`

**Files:**
- Modify: `src/copa2026/backtest.py`
- Test: `tests/test_backtest.py` (adicionar)

**Interfaces:**
- Consumes: `outcome_probabilities`, `ratings_asof` (Task 1); `FixtureMatch` (`tournament.py`); `expected_goals`, `score_matrix` (`prediction.py`); `Match`, `TeamRatings` (`models.py`).
- Produces:
  - `GameBacktest` (frozen dataclass): `played_on: date, home: str, away: str, p_home: float, p_draw: float, p_away: float, previsto: str, real: str, acertou: bool`. (`previsto`/`real` ∈ {"CASA","EMPATE","FORA"}).
  - `BacktestResult` (frozen dataclass): `jogos: list[GameBacktest], acertos: int, total: int, confianca: float`.
  - `walk_forward_backtest(jogos_copa: list[FixtureMatch], partidas_base: list[Match], *, janela: int = 90, reg: float = 2.0) -> BacktestResult`.

- [ ] **Step 1: Testes**

```python
# adicionar em tests/test_backtest.py
from copa2026.backtest import walk_forward_backtest, GameBacktest
from copa2026.tournament import FixtureMatch


def _fx(home, away, gh, ga, dia):
    return FixtureMatch("GROUP_STAGE", "GROUP_A", home, away, gh, ga,
                        "FINISHED", None, f"2026-{dia}T18:00:00Z")


def _base_forte_fraca():
    # Brazil claramente mais forte que Bolivia no histórico pré-Copa.
    from copa2026.models import Match
    from datetime import date
    jogos = []
    for k in range(6):
        jogos.append(Match("Brazil", "Bolivia", 3, 0, date(2026, 5, 10 + k)))
        jogos.append(Match("France", "Bolivia", 2, 0, date(2026, 5, 10 + k)))
        jogos.append(Match("Brazil", "France", 1, 1, date(2026, 5, 10 + k)))
    return jogos


def test_walk_forward_hitrate_and_fields():
    base = _base_forte_fraca()
    jogos = [_fx("Brazil", "Bolivia", 2, 0, "06-12"),   # casa vence (previsível)
             _fx("Bolivia", "Brazil", 0, 3, "06-15")]   # fora vence
    res = walk_forward_backtest(jogos, base)
    assert res.total == 2
    assert res.confianca == res.acertos / res.total
    assert res.jogos[0].previsto == "CASA" and res.jogos[0].real == "CASA"
    assert res.jogos[0].acertou is True
    # soma das probabilidades ~ 1
    g = res.jogos[0]
    assert abs((g.p_home + g.p_draw + g.p_away) - 1.0) < 1e-9


def test_walk_forward_has_no_lookahead():
    base = _base_forte_fraca()
    g1 = _fx("Brazil", "Bolivia", 2, 0, "06-12")
    g2 = _fx("Bolivia", "France", 0, 1, "06-14")
    g3 = _fx("Brazil", "France", 2, 1, "06-18")
    # a previsão de g1/g2 não pode depender de jogos posteriores
    sem_g3 = walk_forward_backtest([g1, g2], base).jogos
    com_g3 = walk_forward_backtest([g1, g2, g3], base).jogos
    assert sem_g3 == com_g3[:2]


def test_walk_forward_skips_games_without_base():
    base = _base_forte_fraca()
    # jogo muito depois -> janela ainda tem base; jogo de seleções sem história
    # ainda é previsto (rating neutro), então total conta os FINISHED com janela.
    jogos = [_fx("Brazil", "Bolivia", 1, 0, "06-12")]
    res = walk_forward_backtest(jogos, base)
    assert res.total == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_backtest.py -v`
Expected: FAIL (`ImportError: cannot import name 'walk_forward_backtest'`).

- [ ] **Step 3: Implementar — acrescentar a `backtest.py`**

No topo de `backtest.py`, acrescentar imports:

```python
from dataclasses import dataclass

from .models import Match, TeamRatings
from .prediction import expected_goals, score_matrix
from .tournament import FixtureMatch
```

Ao final de `backtest.py`:

```python
_LABELS = ("CASA", "EMPATE", "FORA")
_NEUTRO = TeamRatings(1.0, 1.0)


@dataclass(frozen=True)
class GameBacktest:
    played_on: date
    home: str
    away: str
    p_home: float
    p_draw: float
    p_away: float
    previsto: str
    real: str
    acertou: bool


@dataclass(frozen=True)
class BacktestResult:
    jogos: list
    acertos: int
    total: int
    confianca: float


def _resultado(gh: int, ga: int) -> str:
    if gh > ga:
        return "CASA"
    if gh < ga:
        return "FORA"
    return "EMPATE"


def walk_forward_backtest(
    jogos_copa: list[FixtureMatch],
    partidas_base: list[Match],
    *,
    janela: int = 90,
    reg: float = 2.0,
) -> BacktestResult:
    """Backtest sem lookahead: prevê cada jogo real com dados anteriores a ele."""
    reais = sorted(
        (f for f in jogos_copa
         if f.status == "FINISHED" and f.home and f.away
         and f.home_goals is not None and f.away_goals is not None),
        key=lambda f: f.utc_date,
    )
    copa_matches = [
        Match(f.home, f.away, f.home_goals, f.away_goals,
              date.fromisoformat(f.utc_date[:10]))
        for f in reais
    ]

    jogos: list[GameBacktest] = []
    for i, f in enumerate(reais):
        d = date.fromisoformat(f.utc_date[:10])
        base = partidas_base + [m for m in copa_matches if m.played_on < d]
        try:
            ratings, mu = ratings_asof(d, base, janela=janela, reg=reg)
        except ValueError:
            continue
        hr = ratings.get(f.home, _NEUTRO)
        ar = ratings.get(f.away, _NEUTRO)
        lambda_home, lambda_away = expected_goals(hr, ar, mu)
        matrix = score_matrix(lambda_home, lambda_away)
        p_home, p_draw, p_away = outcome_probabilities(matrix)
        previsto = _LABELS[int(np.argmax((p_home, p_draw, p_away)))]
        real = _resultado(f.home_goals, f.away_goals)
        jogos.append(GameBacktest(d, f.home, f.away, p_home, p_draw, p_away,
                                  previsto, real, previsto == real))

    acertos = sum(1 for j in jogos if j.acertou)
    total = len(jogos)
    confianca = acertos / total if total else 0.0
    return BacktestResult(jogos, acertos, total, confianca)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_backtest.py -v`
Expected: PASS (6 testes).

- [ ] **Step 5: Commit**

```bash
git add src/copa2026/backtest.py tests/test_backtest.py
git commit -m "feat: walk_forward_backtest (verificacao sem lookahead)"
```

---

## Task 3: `championship.py` — `prob_vitoria` + `probabilidades_titulo` (DP)

**Files:**
- Create: `src/copa2026/championship.py`
- Test: `tests/test_championship.py`

**Interfaces:**
- Consumes: `outcome_probabilities` (`backtest.py`); `expected_goals`, `score_matrix` (`prediction.py`); `MATCHES`, `STAGE_OF` (`bracket_data.py`); `TeamRatings` (`models.py`).
- Produces:
  - `prob_vitoria(a: str, b: str, ratings, mu, *, max_goals: int = 8) -> float` — P(a avança) = P(a vence) + ½·P(empate).
  - `probabilidades_titulo(confrontos_r32: dict[int, tuple[str, str]], ratings, mu, *, matches=MATCHES, final: int = 104, stage_of=STAGE_OF, max_goals: int = 8) -> dict[str, dict[str, float]]` — por time, `{rótulo_da_rodada: prob, ..., "CAMPEAO": prob}`.

- [ ] **Step 1: Testes**

```python
# tests/test_championship.py
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_championship.py -v`
Expected: FAIL (`ModuleNotFoundError: copa2026.championship`).

- [ ] **Step 3: Implementar `championship.py`**

```python
"""Probabilidade de cada seleção ser campeã, por programação dinâmica sobre o
chaveamento (PRD §9 + §4.3).

Para cada jogo do mata-mata, a probabilidade de um time vencer é somada sobre a
distribuição de possíveis adversários (cada um ponderado pela sua probabilidade
de chegar àquele jogo). Empate no tempo normal é decidido nos pênaltis como
moeda justa (½ para cada lado).
"""

from __future__ import annotations

from .backtest import outcome_probabilities
from .bracket_data import MATCHES, STAGE_OF
from .models import TeamRatings
from .prediction import expected_goals, score_matrix

_NEUTRO = TeamRatings(1.0, 1.0)

_ROTULO = {
    "LAST_32": "R32",
    "LAST_16": "R16",
    "QUARTER_FINALS": "QF",
    "SEMI_FINALS": "SF",
    "FINAL": "Final",
}


def prob_vitoria(a: str, b: str, ratings: dict, mu: float, *, max_goals: int = 8) -> float:
    """P(``a`` avança contra ``b``) = P(a vence) + ½·P(empate)."""
    ra = ratings.get(a, _NEUTRO)
    rb = ratings.get(b, _NEUTRO)
    lambda_a, lambda_b = expected_goals(ra, rb, mu)
    matrix = score_matrix(lambda_a, lambda_b, max_goals)
    p_a, p_empate, _ = outcome_probabilities(matrix)
    return p_a + 0.5 * p_empate


def probabilidades_titulo(
    confrontos_r32: dict[int, tuple[str, str]],
    ratings: dict,
    mu: float,
    *,
    matches: dict = MATCHES,
    final: int = 104,
    stage_of: dict = STAGE_OF,
    max_goals: int = 8,
) -> dict[str, dict[str, float]]:
    """Probabilidade de cada time vencer cada rodada e ser campeão.

    ``confrontos_r32`` mapeia os jogos-folha (R32) aos dois times determinados.
    Os demais jogos referenciam vencedores via slots ``("WM", n)``.
    """
    win_dist: dict[int, dict[str, float]] = {}

    for no in sorted(m for m in matches if m != 103 and m <= final):
        if no in confrontos_r32:
            ta, tb = confrontos_r32[no]
            home_side = {ta: 1.0}
            away_side = {tb: 1.0}
        else:
            (_, na), (_, nb) = matches[no]
            home_side = win_dist[na]
            away_side = win_dist[nb]

        dist: dict[str, float] = {}
        for t, pr in home_side.items():
            s = sum(po * prob_vitoria(t, o, ratings, mu, max_goals=max_goals)
                    for o, po in away_side.items())
            dist[t] = pr * s
        for t, pr in away_side.items():
            s = sum(po * prob_vitoria(t, o, ratings, mu, max_goals=max_goals)
                    for o, po in home_side.items())
            dist[t] = pr * s
        win_dist[no] = dist

    por_time: dict[str, dict[str, float]] = {}
    for no, dist in win_dist.items():
        if no == final:
            continue
        rotulo = _ROTULO.get(stage_of.get(no), str(no))
        for t, p in dist.items():
            por_time.setdefault(t, {})[rotulo] = p
    for t, p in win_dist[final].items():
        por_time.setdefault(t, {})["CAMPEAO"] = p
    return por_time
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_championship.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add src/copa2026/championship.py tests/test_championship.py
git commit -m "feat: probabilidades_titulo (DP sobre o chaveamento)"
```

---

## Task 4: `relatorio.py` — formatadores LaTeX puros

**Files:**
- Create: `src/copa2026/relatorio.py`
- Test: `tests/test_relatorio.py`

**Interfaces:**
- Consumes: `BacktestResult`, `GameBacktest` (`backtest.py`); `display_pt` (`teams.py`).
- Produces (todas puras, devolvem `str`):
  - `pct(x: float) -> str` — `"12,3\%"` (vírgula decimal, 1 casa).
  - `macros_tex(resultado: BacktestResult, favorito: str, data_iso: str) -> str` — define `\grauConfianca`, `\nJogosBacktest`, `\nAcertos`, `\favoritoTitulo`, `\dataAnalise`.
  - `tabela_backtest_tex(resultado: BacktestResult) -> str` — `longtable` booktabs jogo a jogo.
  - `tabela_titulo_tex(por_time: dict[str, dict[str, float]]) -> str` — `longtable` por seleção, ordenada por `CAMPEAO` desc., colunas R32/R16/QF/SF/Campeão.

- [ ] **Step 1: Testes**

```python
# tests/test_relatorio.py
from copa2026.backtest import BacktestResult, GameBacktest
from copa2026.relatorio import (
    macros_tex, pct, tabela_backtest_tex, tabela_titulo_tex,
)
from datetime import date


def _result():
    g = GameBacktest(date(2026, 6, 12), "Brazil", "Bolivia",
                     0.7, 0.2, 0.1, "CASA", "CASA", True)
    return BacktestResult([g], acertos=1, total=1, confianca=1.0)


def test_pct_virgula_decimal():
    assert pct(0.123) == "12,3\\%"
    assert pct(1.0) == "100,0\\%"


def test_macros_define_grau_confianca():
    tex = macros_tex(_result(), favorito="Brazil", data_iso="2026-06-25")
    assert "\\newcommand{\\grauConfianca}{100,0\\%}" in tex
    assert "\\newcommand{\\nJogosBacktest}{1}" in tex
    assert "Brasil" in tex            # display_pt do favorito


def test_tabela_backtest_inclui_jogo_e_acerto():
    tex = tabela_backtest_tex(_result())
    assert "longtable" in tex
    assert "Brasil" in tex and "Bol" in tex  # display_pt dos times
    assert "\\checkmark" in tex              # acerto marcado


def test_tabela_titulo_ordena_por_campeao():
    por_time = {
        "Brazil": {"R32": 0.9, "R16": 0.7, "QF": 0.5, "SF": 0.35, "CAMPEAO": 0.25},
        "Bolivia": {"R32": 0.2, "R16": 0.05, "QF": 0.01, "SF": 0.003, "CAMPEAO": 0.001},
    }
    tex = tabela_titulo_tex(por_time)
    assert tex.index("Brasil") < tex.index("Bol")   # campeão mais provável antes
    assert "longtable" in tex
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_relatorio.py -v`
Expected: FAIL (`ModuleNotFoundError: copa2026.relatorio`).

- [ ] **Step 3: Implementar `relatorio.py`**

```python
"""Formatação dos resultados da análise em LaTeX (tabelas e macros).

Funções puras: recebem dados já calculados e devolvem trechos ``.tex`` que o
artigo inclui via ``\\input``. Não acessam rede nem o sistema de arquivos.
"""

from __future__ import annotations

from .backtest import BacktestResult
from .teams import display_pt

_RESULTADO_PT = {"CASA": "Casa", "EMPATE": "Empate", "FORA": "Fora"}


def pct(x: float) -> str:
    """Percentual com vírgula decimal e uma casa, ex.: ``12,3\\%``."""
    return f"{100 * x:.1f}".replace(".", ",") + r"\%"


def macros_tex(resultado: BacktestResult, favorito: str, data_iso: str) -> str:
    linhas = [
        r"% gerado por scripts/gerar_analise.py — não editar à mão",
        r"\newcommand{\grauConfianca}{" + pct(resultado.confianca) + "}",
        r"\newcommand{\nJogosBacktest}{" + str(resultado.total) + "}",
        r"\newcommand{\nAcertos}{" + str(resultado.acertos) + "}",
        r"\newcommand{\favoritoTitulo}{" + display_pt(favorito) + "}",
        r"\newcommand{\dataAnalise}{" + data_iso + "}",
    ]
    return "\n".join(linhas) + "\n"


def tabela_backtest_tex(resultado: BacktestResult) -> str:
    cab = [
        r"% gerado por scripts/gerar_analise.py — não editar à mão",
        r"\begin{longtable}{llcccll c}",
        r"\toprule",
        r"Data & Jogo & P(C) & P(E) & P(F) & Prev. & Real & OK \\",
        r"\midrule",
        r"\endhead",
    ]
    corpo = []
    for g in resultado.jogos:
        ok = r"\checkmark" if g.acertou else r"$\times$"
        jogo = f"{display_pt(g.home)} $\\times$ {display_pt(g.away)}"
        corpo.append(
            f"{g.played_on.isoformat()} & {jogo} & {pct(g.p_home)} & "
            f"{pct(g.p_draw)} & {pct(g.p_away)} & {_RESULTADO_PT[g.previsto]} & "
            f"{_RESULTADO_PT[g.real]} & {ok} \\\\"
        )
    rod = [r"\bottomrule", r"\end{longtable}"]
    return "\n".join(cab + corpo + rod) + "\n"


def tabela_titulo_tex(por_time: dict[str, dict[str, float]]) -> str:
    ordenado = sorted(
        por_time.items(), key=lambda kv: kv[1].get("CAMPEAO", 0.0), reverse=True
    )
    cab = [
        r"% gerado por scripts/gerar_analise.py — não editar à mão",
        r"\begin{longtable}{lccccc}",
        r"\toprule",
        r"Sele\c{c}\~ao & R32 & R16 & QF & SF & Campe\~ao \\",
        r"\midrule",
        r"\endhead",
    ]
    corpo = []
    for time, p in ordenado:
        corpo.append(
            f"{display_pt(time)} & {pct(p.get('R32', 0))} & {pct(p.get('R16', 0))} "
            f"& {pct(p.get('QF', 0))} & {pct(p.get('SF', 0))} "
            f"& {pct(p.get('CAMPEAO', 0))} \\\\"
        )
    rod = [r"\bottomrule", r"\end{longtable}"]
    return "\n".join(cab + corpo + rod) + "\n"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_relatorio.py -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Commit**

```bash
git add src/copa2026/relatorio.py tests/test_relatorio.py
git commit -m "feat: relatorio.py (formatadores LaTeX das analises)"
```

---

## Task 5: `scripts/gerar_analise.py` — orquestração e geração dos artefatos

**Files:**
- Create: `scripts/gerar_analise.py`
- Create (gerados ao rodar): `artigo/gerado/dados.tex`, `artigo/gerado/backtest.tex`, `artigo/gerado/titulo.tex`, `artigo/figuras/titulo.pdf`

**Interfaces:**
- Consumes: `fetch_wc_fixtures`, `simulate_tournament` (`tournament.py`); `walk_forward_backtest` (`backtest.py`); `probabilidades_titulo` (`championship.py`); `ratings_asof` (`backtest.py`); `macros_tex`, `tabela_backtest_tex`, `tabela_titulo_tex` (`relatorio.py`); `FootballDataSource` (`data_source.py`); `PRE_WC_MATCHES` (`pre_wc_data.py`); `display_pt` (`teams.py`).

Notas:
- Carrega `.env` (mesma rotina de `app.py`: ler `FOOTBALL_DATA_API_KEY`).
- `partidas_base` = `[Match(h, a, gh, ga, date.fromisoformat(d)) for d,h,a,gh,ga in PRE_WC_MATCHES]`.
- Jogos reais da Copa = `Match(...)` a partir dos `FixtureMatch` FINISHED (data = `utc_date[:10]`).
- `ratings, mu = ratings_asof(date.today(), partidas_base + copa_reais)` — snapshot atual (mesma janela de 90 dias).
- `confrontos_r32 = {k.match_no: (k.home, k.away) for k in simulate_tournament(fixtures, ratings, mu).knockout if 73 <= k.match_no <= 88}`.
- Favorito = time de maior `CAMPEAO`.
- Figura: barras horizontais das 12 maiores probabilidades de título (matplotlib, `savefig` em PDF).

- [ ] **Step 1: Implementar `scripts/gerar_analise.py`**

```python
"""Gera os artefatos LaTeX da análise (backtest + probabilidade de título).

Faz UMA chamada à API (todos os jogos da Copa), calcula o backtest walk-forward
e a probabilidade de título por DP, e escreve as tabelas/figura que o artigo
inclui. Reexecutar atualiza os números conforme novos resultados.

Rodar:  python scripts/gerar_analise.py
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from copa2026.backtest import ratings_asof, walk_forward_backtest  # noqa: E402
from copa2026.championship import probabilidades_titulo  # noqa: E402
from copa2026.data_source import FootballDataSource  # noqa: E402
from copa2026.models import Match  # noqa: E402
from copa2026.pre_wc_data import PRE_WC_MATCHES  # noqa: E402
from copa2026.relatorio import (  # noqa: E402
    macros_tex, tabela_backtest_tex, tabela_titulo_tex,
)
from copa2026.teams import display_pt  # noqa: E402
from copa2026.tournament import fetch_wc_fixtures, simulate_tournament  # noqa: E402

GERADO = RAIZ / "artigo" / "gerado"
FIGURAS = RAIZ / "artigo" / "figuras"


def _carrega_chave() -> str:
    env = RAIZ / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if linha.startswith("FOOTBALL_DATA_API_KEY"):
                return linha.split("=", 1)[1].strip().strip('"').strip("'")
    chave = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    if not chave:
        raise SystemExit("Defina FOOTBALL_DATA_API_KEY no .env para gerar a análise.")
    return chave


def _figura_titulo(por_time: dict, caminho: Path) -> None:
    top = sorted(por_time.items(), key=lambda kv: kv[1].get("CAMPEAO", 0),
                 reverse=True)[:12]
    nomes = [display_pt(t) for t, _ in top][::-1]
    valores = [p.get("CAMPEAO", 0) * 100 for _, p in top][::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(nomes, valores, color="#1f77b4")
    ax.set_xlabel("Probabilidade de título (%)")
    ax.set_title("Probabilidade de ser campeão — 12 maiores")
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)


def main() -> None:
    chave = _carrega_chave()
    fixtures = fetch_wc_fixtures(FootballDataSource(api_key=chave))

    base = [Match(h, a, gh, ga, date.fromisoformat(d))
            for d, h, a, gh, ga in PRE_WC_MATCHES]
    copa_reais = [
        Match(f.home, f.away, f.home_goals, f.away_goals,
              date.fromisoformat(f.utc_date[:10]))
        for f in fixtures
        if f.status == "FINISHED" and f.home and f.away
        and f.home_goals is not None and f.away_goals is not None
    ]

    ratings, mu = ratings_asof(date.today(), base + copa_reais)

    backtest = walk_forward_backtest(fixtures, base)

    res = simulate_tournament(fixtures, ratings, mu)
    confrontos_r32 = {
        k.match_no: (k.home, k.away)
        for k in res.knockout if 73 <= k.match_no <= 88
    }
    por_time = probabilidades_titulo(confrontos_r32, ratings, mu)
    favorito = max(por_time, key=lambda t: por_time[t].get("CAMPEAO", 0))

    GERADO.mkdir(parents=True, exist_ok=True)
    FIGURAS.mkdir(parents=True, exist_ok=True)
    (GERADO / "dados.tex").write_text(
        macros_tex(backtest, favorito, date.today().isoformat()), encoding="utf-8")
    (GERADO / "backtest.tex").write_text(
        tabela_backtest_tex(backtest), encoding="utf-8")
    (GERADO / "titulo.tex").write_text(
        tabela_titulo_tex(por_time), encoding="utf-8")
    _figura_titulo(por_time, FIGURAS / "titulo.pdf")

    print(f"Backtest: {backtest.acertos}/{backtest.total} "
          f"(confiança {backtest.confianca:.1%})")
    print(f"Favorito ao título: {display_pt(favorito)} "
          f"({por_time[favorito]['CAMPEAO']:.1%})")
    print(f"Artefatos escritos em {GERADO} e {FIGURAS}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar o script (gera os artefatos; única etapa com rede)**

Run: `python scripts/gerar_analise.py`
Expected: imprime o backtest (ex.: `Backtest: NN/MM (confiança XX.X%)`), o favorito, e cria `artigo/gerado/{dados,backtest,titulo}.tex` + `artigo/figuras/titulo.pdf`.

- [ ] **Step 3: Conferir os artefatos gerados**

Run: `python -c "import pathlib; [print(p, pathlib.Path('artigo').joinpath(p).exists()) for p in ['gerado/dados.tex','gerado/backtest.tex','gerado/titulo.tex','figuras/titulo.pdf']]"`
Expected: os quatro caminhos existem (`True`).

Run: `grep -c '\\\\' artigo/gerado/titulo.tex`
Expected: número > 0 (linhas da tabela presentes).

- [ ] **Step 4: Commit (script + artefatos gerados)**

```bash
git add scripts/gerar_analise.py artigo/gerado/dados.tex artigo/gerado/backtest.tex artigo/gerado/titulo.tex artigo/figuras/titulo.pdf
git commit -m "feat: gerar_analise.py + artefatos da analise gerados"
```

---

## Task 6: Artigo LaTeX — `artigo/previsor-copa-2026.tex` + build

**Files:**
- Create: `artigo/previsor-copa-2026.tex`
- Create: `artigo/.gitignore`

**Interfaces:**
- Consumes (via `\input`): `artigo/gerado/dados.tex` (macros), `artigo/gerado/backtest.tex`, `artigo/gerado/titulo.tex`, `artigo/figuras/titulo.pdf` (gerados na Task 5).

- [ ] **Step 1: Escrever `artigo/.gitignore`**

```gitignore
*.aux
*.log
*.out
*.toc
*.fls
*.fdb_latexmk
*.synctex.gz
previsor-copa-2026.pdf
```

- [ ] **Step 2: Escrever `artigo/previsor-copa-2026.tex`**

```latex
\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazil]{babel}
\usepackage{amsmath, amssymb}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{graphicx}
\usepackage{geometry}
\geometry{margin=2.5cm}

\input{gerado/dados}

\title{Previsor de Resultados da Copa do Mundo de 2026:\\
Metodologia, Verifica\c{c}\~ao Emp\'irica e Probabilidade de T\'itulo}
\author{richmo.media}
\date{\dataAnalise}

\begin{document}
\maketitle

\begin{abstract}
Este artigo descreve o m\'etodo usado para prever resultados da Copa de 2026 a
partir da forma recente das sele\c{c}\~oes, verifica-o empiricamente por uma
an\'alise regressiva (\emph{backtest}) sobre os jogos j\'a disputados e projeta
a probabilidade de cada sele\c{c}\~ao ser campe\~a por encadeamento das
probabilidades de vit\'oria no mata-mata.
\end{abstract}

\section{Introdu\c{c}\~ao}
O objetivo do previsor \'e gerar, para um bol\~ao, o palpite que maximiza os
pontos esperados. A metodologia combina a forma recente (janela de 90 dias),
um modelo de for\c{c}a ofensiva/defensiva e a distribui\c{c}\~ao de Poisson para
os gols.

\section{Metodologia}
\subsection{Coleta e janela de 90 dias}
Para cada partida a prever, consideram-se apenas os jogos das 48 sele\c{c}\~oes
nos \'ultimos 90 dias, capturando a forma recente.

\subsection{For\c{c}a ofensiva e defensiva (modelo circular)}
Cada sele\c{c}\~ao $i$ tem for\c{c}a de ataque $O_i$ e fragilidade defensiva
$D_i$. Sendo $\mu$ a m\'edia de gols por time por jogo, os gols esperados de $i$
contra $j$ s\~ao $\mu\,O_i\,D_j$. Como ataque depende da defesa do advers\'ario
e vice-versa, resolve-se o sistema por ponto fixo:
\begin{align}
O_i &\leftarrow \frac{\sum_{m} g^{\text{pro}}_{i,m}}
                     {\sum_{m} \mu\,D_{\text{adv}(i,m)}}, &
D_i &\leftarrow \frac{\sum_{m} g^{\text{contra}}_{i,m}}
                     {\sum_{m} \mu\,O_{\text{adv}(i,m)}},
\end{align}
iterando at\'e a converg\^encia. Uma regulariza\c{c}\~ao (encolhimento para
$O=D=1$) estabiliza estimativas de amostras pequenas.

\subsection{Gols esperados}
Com a for\c{c}a estimada, os gols esperados de mandante e visitante s\~ao
\begin{equation}
\lambda_{\text{casa}} = \mu\,O_{\text{casa}}\,D_{\text{fora}}, \qquad
\lambda_{\text{fora}} = \mu\,O_{\text{fora}}\,D_{\text{casa}},
\end{equation}
e a probabilidade de cada placar $(x,y)$ segue dois processos de Poisson
independentes: $P(x,y) = \mathrm{Pois}(x;\lambda_{\text{casa}})\,
\mathrm{Pois}(y;\lambda_{\text{fora}})$.

\subsection{Palpite \'otimo (resumo)}
O palpite recomendado \'e o placar que maximiza o valor esperado da fun\c{c}\~ao
de pontua\c{c}\~ao do bol\~ao sobre toda a matriz de placares. Esse passo
importa apenas para o placar exato (aposta/bol\~ao) e n\~ao para as an\'alises
de \emph{resultado} (vit\'oria/empate/derrota) deste artigo.

\section{Verifica\c{c}\~ao emp\'irica (\emph{backtest} walk-forward)}
Voltamos ao primeiro jogo da Copa e avan\c{c}amos jogo a jogo. Para cada partida
j\'a disputada, a for\c{c}a \'e recalculada usando \textbf{apenas} os dados
anteriores \`aquele jogo (sem vi\'es de futuro) e prev\^e-se o resultado de maior
probabilidade entre vit\'oria da casa, empate e vit\'oria de fora — somando as
regi\~oes da matriz de placares. Comparando com o resultado real, obtemos um
\textbf{grau de confian\c{c}a emp\'irico} (taxa de acerto) de
\textbf{\grauConfianca} em \nJogosBacktest{} jogos (\nAcertos{} acertos).

{\footnotesize\input{gerado/backtest}}

\section{Probabilidade de t\'itulo}
Como a fase de grupos ainda n\~ao terminou, os jogos faltantes s\~ao preenchidos
com o resultado previsto pelo m\'etodo, fixando os 32 confrontos das oitavas.
A partir da\'i, encadeamos as probabilidades: a chance de um time vencer um jogo
soma sobre os poss\'iveis advers\'arios, cada um ponderado pela sua probabilidade
de chegar \`aquele jogo (empate decidido nos p\^enaltis como moeda justa).
O produto ao longo das rodadas d\'a a probabilidade de t\'itulo. O favorito
segundo o m\'etodo \'e \textbf{\favoritoTitulo}. Estas proje\c{c}\~oes devem ser
lidas \`a luz do grau de confian\c{c}a emp\'irico (\grauConfianca).

\begin{figure}[h]
\centering
\includegraphics[width=0.8\textwidth]{figuras/titulo.pdf}
\caption{Probabilidade de t\'itulo das 12 sele\c{c}\~oes mais prov\'aveis.}
\end{figure}

{\footnotesize\input{gerado/titulo}}

\section{Reprodutibilidade}
Todas as tabelas e a figura s\~ao geradas por
\texttt{scripts/gerar\_analise.py}, que consome os resultados reais da API e
reexecuta os c\'alculos. Conforme novos jogos ocorrem (fim da fase de grupos,
mata-mata), basta reexecutar o script para atualizar o artigo.

\end{document}
```

- [ ] **Step 3: Compilar o PDF**

Run: `cd artigo && latexmk -pdf -interaction=nonstopmode previsor-copa-2026.tex; cd ..`
Expected: gera `artigo/previsor-copa-2026.pdf` sem erros fatais (avisos de \emph{overfull box} são aceitáveis).

- [ ] **Step 4: Verificar que o PDF foi criado**

Run: `python -c "import pathlib; print('PDF OK' if pathlib.Path('artigo/previsor-copa-2026.pdf').exists() else 'FALTOU PDF')"`
Expected: `PDF OK`.

- [ ] **Step 5: Commit (sem o PDF de build nem auxiliares — ignorados pelo .gitignore)**

```bash
git add artigo/previsor-copa-2026.tex artigo/.gitignore
git commit -m "feat: artigo LaTeX (metodologia + backtest + prob. de titulo)"
```

---

## Task 7: Documentação e verificação final

**Files:**
- Modify: `README.md`, `prd.md`

- [ ] **Step 1: Nota no `README.md`**

Acrescentar, após a introdução, uma linha apontando o artigo e como gerá-lo:

```markdown
## Artigo

Um artigo em LaTeX com a metodologia, a verificação empírica (backtest) e a
probabilidade de título está em [`artigo/`](artigo/). Regenerar os números:
`python scripts/gerar_analise.py` e recompilar com
`latexmk -pdf artigo/previsor-copa-2026.tex`.
```

- [ ] **Step 2: Nota no `prd.md`**

Acrescentar uma subseção curta em §8 (Trabalhos Futuros) ou nova seção citando o artigo (`artigo/previsor-copa-2026.tex`), o backtest walk-forward (`backtest.py`), a probabilidade de título por DP (`championship.py`) e o script regenerável (`scripts/gerar_analise.py`).

- [ ] **Step 3: Verificação final — suíte + build**

Run: `python -m pytest -q`
Expected: PASS (suíte inteira verde, incluindo os novos testes).

Run: `python -c "import ast; ast.parse(open('scripts/gerar_analise.py', encoding='utf-8').read()); print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add README.md prd.md
git commit -m "docs: aponta o artigo e a analise (backtest + prob. de titulo)"
```

---

## Self-review (verificação do plano contra o spec)

- **Cobertura do spec:** `outcome_probabilities`/`ratings_asof` (T1) ✓; `walk_forward_backtest` sem lookahead (T2) ✓; `prob_vitoria`/`probabilidades_titulo` DP (T3) ✓; separação de dados — ratings só com reais, mock só p/ R32 (T5: `ratings_asof` recebe `base+copa_reais`; `confrontos_r32` via `simulate_tournament`) ✓; formatadores LaTeX (T4) ✓; script regenerável de 1 chamada (T5) ✓; artigo com as seções de metodologia/verificação/título/reprodutibilidade (T6) ✓; taxa de acerto como grau de confiança (T2/T4/T6) ✓; figura matplotlib (T5) ✓; docs (T7) ✓; sem mudança no app/Streamlit ✓.
- **Sem placeholders:** todo passo de código tem o código completo; testes têm asserções reais; comandos têm saída esperada.
- **Consistência de tipos:** `BacktestResult`/`GameBacktest` (T2) usados em T4/T5; `ratings_asof`/`walk_forward_backtest` (T1/T2) em T5; `probabilidades_titulo` retorna `dict[time -> {rótulo: prob, "CAMPEAO": prob}]` (T3) consumido por `tabela_titulo_tex` (T4) e pelo script (T5) via chave `"CAMPEAO"`; `confrontos_r32` keys 73–88 (T5) batem com a detecção de folha em `probabilidades_titulo` (T3); `prob_vitoria` (T3) reusa `outcome_probabilities` (T1).
- **Decisão de projeto registrada:** a extração dos confrontos do R32 vive no script (T5), não em `championship.py`, mantendo o módulo puro/unitário; `championship.probabilidades_titulo` é parametrizável (`matches`/`final`/`stage_of`) para testes com chaveamentos pequenos.
