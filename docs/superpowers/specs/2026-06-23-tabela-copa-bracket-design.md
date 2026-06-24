# Design — Aba "Tabela da Copa" (chaveamento real + previsto)

Data: 2026-06-23
Status: aprovado para planejamento

## 1. Objetivo

Adicionar uma aba à interface Streamlit que reproduz a tabela da Copa 2026
(fase de grupos + mata-mata) misturando **resultados reais** (jogos já
disputados, conferidos na API a cada atualização) com **resultados previstos**
para os jogos futuros, preenchendo todo o chaveamento até a final sob a premissa
de que **o previsor sempre acerta o vencedor**.

## 2. Decisões de produto (definidas com o usuário)

- **Layout:** tabelas simples por fase. Fase de grupos = 12 tabelas de
  classificação (uma por grupo). Mata-mata = uma lista de confrontos por fase
  (R32 → R16 → Quartas → Semis → 3º lugar → Final).
- **Classificação dos grupos:** regras oficiais FIFA — critérios de desempate
  completos e a tabela oficial de alocação dos 8 melhores terceiros nos slots
  do R32.
- **Mata-mata:** mostra o placar do palpite ótimo (consistente com o resto do
  app). Quem avança é o time de maior λ (gols esperados); empate no palpite
  resolve-se por λ; se λ também empatar, por (ataque − fragilidade defensiva),
  exibindo o rótulo "(pênaltis)".

## 3. Fonte de dados (investigada)

A API football-data.org (chave já em `.env`, usada pela produção) serve a
competição `WC` completa via `/competitions/WC/matches`:

- 104 jogos, `stage` ∈ {GROUP_STAGE, LAST_32, LAST_16, QUARTER_FINALS,
  SEMI_FINALS, THIRD_PLACE, FINAL}, `group` ∈ {GROUP_A … GROUP_L}.
- Cada jogo traz `status` (FINISHED/TIMED), `score.fullTime`, `utcDate`, times.

**Limitação crucial:** os jogos de mata-mata vêm com `homeTeam`/`awayTeam`
nulos e **sem nenhuma metadata de chaveamento** — a API não diz "vencedor do
grupo A", nem qual jogo alimenta qual. Portanto o **mapa de chaveamento**
(quem enfrenta quem no R32 e a árvore até a final) e a **tabela dos 8 melhores
terceiros** são fixos/publicados e ficam **embutidos** no código (padrão já
usado em `pre_wc_data.py`).

O **PDF** em `docs/tabela_copa2026/` não é renderizável (streams de imagem
corrompidos) e é redundante com a API → **removido antes do commit**.

## 4. Arquitetura

Novos módulos em `src/copa2026/` (mantendo o estilo do pacote):

### 4.1. `bracket_data.py` (referência embutida, gerada)

Dados fixos publicados pela FIFA:

- `R32_SLOTS`: os 16 confrontos do R32 definidos por posição de grupo
  (ex.: `("1A", "3C/D/F/G")`), na ordem oficial dos slots.
- `BRACKET_TREE`: como cada vencedor de R32 alimenta R16 → Quartas → Semis →
  Final → 3º lugar (índices de slot).
- `BEST_THIRD_ALLOCATION`: tabela oficial que mapeia o **conjunto** dos 8 grupos
  cujos terceiros se classificam → a qual slot do R32 cada terceiro vai
  (495 combinações = C(12,8)). Gerada por `scripts/generate_bracket_data.py`
  a partir da fonte pública (Wikipédia/FIFA).

### 4.2. `standings.py` (classificação FIFA)

- `GroupStanding`: pos, time, J, V, E, D, GP, GC, SG, Pts.
- `compute_group_table(group, matches) -> list[GroupStanding]`: ordena pelos
  critérios oficiais: (1) pontos; (2) saldo de gols geral; (3) gols pró geral;
  (4) entre os empatados: pontos no confronto direto, saldo no confronto
  direto, gols pró no confronto direto; (5) *fair play* / sorteio →
  desempate determinístico de cauda (ordem estável documentada, já que não há
  dados de cartões confiáveis). Cada critério referencia a regra FIFA.
- `rank_third_places(group_tables) -> list[GroupStanding]`: ordena os 12
  terceiros pelos mesmos critérios e devolve os 8 melhores.

### 4.3. Força global — pequeno refactor de previsão

Hoje `predict_match` busca histórico e recalcula a força a cada par de times
(2 chamadas de API por jogo). Simular ~100 jogos assim é lento e redundante.

- Adicionar em `pipeline.py` (ou novo `ratings.py`):
  - `compute_global_ratings(source, teams) -> (ratings: dict, mu: float)` —
    coleta `recent_matches` de todas as 48 seleções uma vez, deduplica, roda
    `compute_ratings` + `league_mu` **uma vez**.
  - `predict_scoreline(home, away, ratings, mu, *, max_goals) -> ScorePrediction`
    com `palpite`, `lambda_home`, `lambda_away` — reaproveita
    `expected_goals` → `score_matrix` → `best_guess` **sem rede**.
- `predict_match` existente permanece intacto (caminho de partida única).

### 4.4. `tournament.py` (orquestração da tabela)

- `FixtureMatch`: dataclass normalizada (stage, group, home, away,
  home_goals, away_goals, status, utc_date) — parser da resposta da API.
- `fetch_wc_fixtures(source) -> list[FixtureMatch]`: lê
  `/competitions/WC/matches` (novo método em `FootballDataSource`). Há um
  *fallback* embutido com o calendário da fase de grupos
  (`fixtures_data.py`, gerado) para rodar offline/sem chave e nos testes.
- `simulate_tournament(fixtures, ratings, mu) -> TournamentResult`:
  1. Para cada jogo de grupo: usa o placar **real** se FINISHED, senão o
     **previsto** (`predict_scoreline`).
  2. Calcula as 12 tabelas (`standings.py`) → 1º/2º de cada grupo + 8 melhores
     terceiros.
  3. Monta o R32 via `bracket_data` (alocando terceiros pela tabela oficial).
  4. Para cada confronto de mata-mata: se a API tem resultado **real**
     FINISHED para aquele slot (casado por ordem cronológica dentro da fase),
     usa-o e propaga o vencedor real; senão prevê o placar e define o vencedor
     por λ. Propaga até a final.
  - Saída: tabelas de grupo + confrontos por fase, cada um marcado como
    `real` ou `previsto`.

## 5. Interface (`app.py`)

- Envolver a UI atual em `aba_previsor, aba_tabela = st.tabs([...])`; a previsão
  ponto-a-ponto existente fica na primeira aba, sem mudanças de lógica.
- Aba "Tabela da Copa":
  - Busca da competição em `@st.cache_data(ttl=600)` (evita martelar a API a
    cada rerun) + botão **🔄 Atualizar** que limpa o cache.
  - Mostra 12 tabelas de classificação (`st.dataframe`) e, abaixo, as listas de
    confrontos por fase, distinguindo visualmente **real** vs **previsto**
    (ex.: ✅ real / 🔮 previsto) e marcando "(pênaltis)" quando aplicável.
  - Sem chave de API: exibe aviso e usa o *fallback* embutido (tudo previsto).
- Strings em português (convenção do projeto).

## 6. Tratamento de erros / casos de borda

- Sem `FOOTBALL_DATA_API_KEY`: aba funciona com fixtures embutidos (tudo
  previsto); aviso de que não há resultados reais.
- Falha de rede/API: mensagem amigável; não derruba a aba do previsor.
- Empate no palpite do mata-mata: vencedor por λ → ataque/defesa → rótulo
  "(pênaltis)". Nunca deixa um confronto sem vencedor.
- Resultado real de mata-mata que contraria o avanço previsto: o real
  prevalece para aquele slot e o vencedor real propaga adiante (documentado).

## 7. Testes (TDD)

Suíte em `tests/`, sem rede (dados sintéticos/injetados):

- `test_standings.py`: ordenação por todos os critérios FIFA; confronto direto;
  seleção dos 8 melhores terceiros; alocação pela tabela oficial.
- `test_tournament.py`: real vs previsto na fase de grupos; montagem do R32;
  propagação do vencedor por λ; resolução de empate "(pênaltis)"; *fallback*
  offline; resultado real de KO sobrescreve previsto.
- `test_ratings.py`: `compute_global_ratings`/`predict_scoreline` coerentes com
  `predict_match` para um par isolado.
- Parser `FixtureMatch` a partir de payload de exemplo da API.

## 8. Fora de escopo (YAGNI)

- Desenho de árvore de chaveamento em HTML/CSS (optou-se por tabelas).
- *Fair play* real (dados de cartões) — desempate de cauda determinístico.
- Probabilidades de avanço / simulação Monte Carlo (a premissa é "sempre
  acerta o vencedor").

## 9. Mapa de arquivos

| Arquivo | Ação |
|---|---|
| `src/copa2026/bracket_data.py` | novo (gerado) — slots R32, árvore, tabela 3os |
| `src/copa2026/fixtures_data.py` | novo (gerado) — fallback do calendário de grupos |
| `src/copa2026/standings.py` | novo — classificação FIFA |
| `src/copa2026/tournament.py` | novo — orquestração real+previsto |
| `src/copa2026/pipeline.py` ou `ratings.py` | força global + `predict_scoreline` |
| `src/copa2026/data_source.py` | método para listar jogos da competição |
| `app.py` | abas + aba "Tabela da Copa" |
| `scripts/generate_bracket_data.py` | novo — gera dados embutidos |
| `tests/test_*.py` | novos testes |
| `docs/tabela_copa2026/` | **removido** (PDF inútil) |
| `prd.md` | nova seção descrevendo a feature |
