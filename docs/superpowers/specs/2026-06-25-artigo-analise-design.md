# Design — Artigo LaTeX + módulo de análise (backtest + probabilidade de título)

Data: 2026-06-25
Status: aprovado para planejamento

## 1. Objetivo

Produzir um artigo em LaTeX (pasta separada `artigo/`) que documenta a
metodologia do previsor e apresenta duas análises novas, calculadas por um
módulo Python regenerável:

1. **Verificação do modelo (backtest walk-forward):** voltando ao primeiro
   jogo da Copa e avançando jogo a jogo, prever o resultado (Vitória casa /
   Empate / Vitória fora) usando **apenas dados anteriores** ao jogo e comparar
   com o real, estabelecendo um **grau de confiança empírico = taxa de acerto**.
2. **Probabilidade de título:** encadeamento (programação dinâmica) das
   probabilidades de vitória de cada seleção, do R32 até a final, chegando à
   probabilidade de cada time ser campeão — apresentada com o grau de confiança
   como ressalva.

## 2. Decisões de produto (definidas com o usuário)

- **Backtest:** *walk-forward* sem lookahead (ratings recalculados por jogo com
  a janela de 90 dias que termina antes do jogo).
- **Probabilidade de título:** DP rigorosa sobre o chaveamento, somando sobre a
  distribuição de adversários (soma 100% entre os 32 times).
- **Grau de confiança:** taxa de acerto (fração de jogos cujo resultado de maior
  probabilidade V/E/D se confirmou).
- **Saída:** somente o artigo; um script regenerável produz tabelas/figuras que
  o `.tex` inclui via `\input`. Sem mudanças no app Streamlit.

## 3. Separação de dados (princípio central)

- **Ratings (força):** calculados **apenas com dados reais** — histórico
  pré-Copa embutido (`pre_wc_data.PRE_WC_MATCHES`, datado) + jogos **reais** da
  Copa já disputados (da API). Jogos previstos/"mockados" **nunca** entram no
  cálculo da força (evita circularidade).
- **Mock:** serve só para **completar a fase de grupos** — jogos de grupo ainda
  não disputados recebem o placar previsto — e assim **fixar os 32 confrontos do
  R32**. Reaproveita a classificação FIFA já existente
  (`tournament.simulate_tournament`).
- **Backtest:** usa apenas jogos **reais** disputados. (Hoje a fase de grupos
  está em andamento e o mata-mata não começou, então o backtest cobre os jogos
  de grupo já realizados.)

## 4. Arquitetura de código

Módulos novos em `src/copa2026/` (puros, testáveis, sem rede):

### 4.1. `backtest.py`

- `outcome_probabilities(matrix) -> tuple[float, float, float]`
  Soma a matriz de placares de Poisson nos três resultados:
  `p_casa = Σ_{x>y} P[x,y]`, `p_empate = Σ_{x=y}`, `p_fora = Σ_{x<y}`.
  (Reusa `prediction.score_matrix`.)

- `ratings_asof(corte: date, partidas: list[Match], *, janela: int = 90,
  reg: float = 2.0) -> tuple[dict[str, TeamRatings], float]`
  Função **pura**: filtra `partidas` para `corte - janela <= played_on < corte`,
  e calcula `compute_ratings(janela_partidas, WC_SET, reg)` + `league_mu`.
  **Não usa `date.today()`** — é o que torna o walk-forward correto. Lança
  `ValueError` se a janela ficar vazia (tratado pelo chamador: jogo sem base).

- `GameBacktest` (dataclass): `played_on, home, away, p_home, p_draw, p_away,
  previsto: str ("CASA"/"EMPATE"/"FORA"), real: str, acertou: bool`.
- `BacktestResult` (dataclass): `jogos: list[GameBacktest]`,
  `acertos: int`, `total: int`, `confianca: float` (= acertos/total).

- `walk_forward_backtest(jogos_copa: list[FixtureMatch],
  partidas_base: list[Match], *, janela=90, reg=2.0) -> BacktestResult`
  Ordena os jogos **reais** (`status == "FINISHED"`) por data; para cada um:
  monta a base = `partidas_base` (pré-Copa) + jogos reais da Copa com
  `played_on < data_do_jogo`; chama `ratings_asof`; calcula
  `expected_goals → score_matrix → outcome_probabilities`; o previsto é o
  `argmax(p_casa, p_empate, p_fora)`; compara com o real. Jogos sem base
  suficiente (janela vazia) são pulados e não contam no denominador.

### 4.2. `championship.py`

- `prob_vitoria(a: str, b: str, ratings, mu, *, max_goals=8) -> float`
  P(a avança contra b) = `Σ_{x>y} P[x,y] + 0.5 · Σ_{x=y} P[x,y]`
  (empate decidido nos pênaltis como moeda justa). Times sem rating → neutro
  `TeamRatings(1,1)`.

- `probabilidades_titulo(confrontos_r32: dict[int, tuple[str, str]],
  ratings, mu, *, max_goals=8) -> dict[str, dict[str, float]]`
  DP sobre `bracket_data.MATCHES`. `confrontos_r32` mapeia cada jogo 73–88 aos
  dois times determinados (vindos da classificação real+mock).
  - `win_dist: dict[int, dict[str, float]]` — `win_dist[m][T]` = P(T vence o
    jogo `m`) = P(T chega e vence).
  - Iterando `m` em ordem crescente (73→102, 104; o jogo 103/3º lugar é
    irrelevante para o título e fica de fora):
    - **R32 (73–88):** lados são os dois times de `confrontos_r32[m]`, cada um
      com prob. de chegada 1. `win_dist[m][T] = Σ_O Pbeat(T,O)` (lado oposto tem
      1 time).
    - **Demais:** lados vêm de `win_dist[n_casa]` e `win_dist[n_fora]` (os slots
      `("WM", n)` de `MATCHES[m]`). Para cada T no lado da casa:
      `win_dist[m][T] = win_dist[n_casa][T] · Σ_{O ∈ win_dist[n_fora]}
      win_dist[n_fora][O] · Pbeat(T,O)`; e simetricamente para o lado de fora.
  - Saída por time: `{ "R32": p, "R16": p, "QF": p, "SF": p, "FINAL": p,
    "CAMPEAO": p }`, onde cada valor é `win_dist[jogo_da_rodada_do_time][T]`
    (probabilidade cumulativa de vencer aquela rodada). `CAMPEAO = win_dist[104]`.
  - Invariante testável: `Σ_T CAMPEAO[T] ≈ 1`.

### 4.3. Extração dos confrontos do R32

Função auxiliar (em `championship.py` ou no script) que, dada a lista de
`FixtureMatch` e `(ratings, mu)`, chama `tournament.simulate_tournament` e lê os
campos `home`/`away` dos `KnockoutResult` dos jogos 73–88 → `confrontos_r32`.
(Reaproveita toda a classificação FIFA + mock de grupos já implementados; só
ignora a propagação determinística do vencedor, substituída pela DP.)

## 5. Script regenerável — `scripts/gerar_analise.py`

1. Carrega `.env`, instancia `FootballDataSource`, faz **1 chamada**
   (`competition_matches` → `fetch_wc_fixtures`).
2. Monta `partidas_base` a partir de `PRE_WC_MATCHES`; monta a lista de jogos
   reais da Copa (FINISHED, datados) a partir dos fixtures.
3. `ratings, mu = ratings_asof(hoje, base + jogos_reais_copa)`.
4. Backtest: `walk_forward_backtest(fixtures, partidas_base)`.
5. Mock + R32: `simulate_tournament(fixtures, ratings, mu)` → `confrontos_r32`.
6. Título: `probabilidades_titulo(confrontos_r32, ratings, mu)`.
7. **Gera artefatos** em `artigo/gerado/` (commitados):
   - `dados.tex` — macros: `\grauConfianca`, `\nJogosBacktest`, `\nAcertos`,
     `\dataAnalise`, `\favoritoTitulo`.
   - `backtest.tex` — tabela `booktabs` jogo-a-jogo (data, mandante, visitante,
     p V/E/D, previsto, real, ✔/�’).
   - `titulo.tex` — tabela por seleção (R32→Final + Campeão %), ordenada por
     prob. de título.
   - `artigo/figuras/titulo.pdf` (opcional) — barras das ~12 maiores via
     matplotlib.

Reexecutar o script atualiza os arquivos gerados conforme novos resultados
(fim da fase de grupos, jogos do mata-mata).

## 6. Artigo LaTeX — `artigo/`

- `artigo/previsor-copa-2026.tex` (principal), classe `article`, português,
  pacotes `amsmath`, `booktabs`, `graphicx`, `siunitx`. Inclui os gerados via
  `\input{gerado/...}`.
- Compila com `latexmk -pdf artigo/previsor-copa-2026.tex` (MiKTeX disponível
  localmente). Build verificado na implementação (gera o PDF sem erros).
- Estrutura:
  1. **Introdução** — objetivo (maximizar pontos esperados do bolão).
  2. **Metodologia** — espelha o `prd.md`:
     - Coleta e janela de 90 dias (§4.1).
     - Força ataque (O) / defesa (D) por ponto-fixo circular (§4.2), com as
       equações de iteração e regularização.
     - Gols esperados: Poisson, `λ_casa = μ·O_casa·D_fora` (§4.3).
     - Palpite ótimo — **resumido**: maximiza o valor esperado da função de
       pontuação do bolão (§3, §4.4); importa só para apostas/placar exato e
       não para as análises de resultado deste artigo.
  3. **Verificação (backtest walk-forward)** — método sem lookahead, tabela
     `backtest.tex`, grau de confiança empírico (`\grauConfianca`).
  4. **Projeção do campeão** — mock dos jogos faltantes, encadeamento DP, tabela
     `titulo.tex` (prob. por rodada + campeão), figura opcional, com o grau de
     confiança como ressalva sobre a incerteza.
  5. **Reprodutibilidade** — o `scripts/gerar_analise.py` e como regenerar.

## 7. Testes (TDD, sem rede)

`tests/`:

- `test_backtest.py`:
  - `outcome_probabilities`: soma ≈ 1; buckets corretos para uma matriz
    assimétrica conhecida.
  - `ratings_asof`: respeita o corte (um jogo após o corte não altera os
    ratings); janela vazia → `ValueError`.
  - `walk_forward_backtest`: em dados sintéticos, (a) não há lookahead — a
    previsão do jogo *i* independe de jogos posteriores; (b) a taxa de acerto
    bate com a contagem manual.
- `test_championship.py`:
  - `prob_vitoria`: `prob_vitoria(A,B) + prob_vitoria(B,A) ≈ 1`.
  - `probabilidades_titulo`: chaveamento-brinquedo de 2 times (1 jogo) e de
    4 times (R "semis"+final reduzido a 2 jogos por lado) com probabilidades
    calculáveis à mão; `Σ_T CAMPEAO[T] ≈ 1`; monotonia (prob. de rodada
    posterior ≤ anterior).

Para testar a DP de forma isolada, `probabilidades_titulo` recebe o mapa de
jogos e a raiz como parâmetros opcionais —
`probabilidades_titulo(confrontos_r32, ratings, mu, *, matches=MATCHES,
final=104)` — de modo que os testes injetam um `matches` reduzido (ex.: 1 ou 3
jogos) com sua própria raiz, sem depender do chaveamento completo de 73–104.

## 8. Fora de escopo (YAGNI)

- Exibir as análises no app Streamlit (decidido: só o artigo).
- Disputa de 3º lugar na DP (não afeta a probabilidade de título).
- Calibração/Brier como grau de confiança (escolhido: taxa de acerto).
- Simulação Monte Carlo (a DP é exata para o chaveamento dado).

## 9. Mapa de arquivos

| Arquivo | Ação |
|---|---|
| `src/copa2026/backtest.py` | novo — `outcome_probabilities`, `ratings_asof`, `walk_forward_backtest` |
| `src/copa2026/championship.py` | novo — `prob_vitoria`, `probabilidades_titulo`, extração R32 |
| `scripts/gerar_analise.py` | novo — orquestra e gera os artefatos LaTeX |
| `artigo/previsor-copa-2026.tex` | novo — artigo principal |
| `artigo/gerado/{dados,backtest,titulo}.tex` | novos (gerados) — incluídos via `\input` |
| `artigo/figuras/titulo.pdf` | novo (gerado, opcional) |
| `artigo/.gitignore` | ignora artefatos auxiliares do LaTeX (`*.aux`, `*.log`, `*.pdf` do build) — mantém os `gerado/*.tex` |
| `tests/test_backtest.py`, `tests/test_championship.py` | novos testes |
| `prd.md` / `README.md` | nota apontando para o artigo |
| `requirements.txt` | sem mudança (matplotlib já é dependência) |
