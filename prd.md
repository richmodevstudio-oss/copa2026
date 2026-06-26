# PRD — Previsor de Resultados da Copa do Mundo 2026

| | |
|---|---|
| **Documento** | Product Requirements Document (PRD) |
| **Produto** | Gerador de palpites otimizados para jogos da Copa 2026 |
| **Versão** | 1.0 |
| **Data** | 2026-06-16 |
| **Status** | Proposta |

---

## 1. Visão Geral

### 1.1. Objetivo

Construir uma aplicação capaz de gerar **palpites de placar** para partidas da Copa do Mundo de 2026 que **maximizem a pontuação esperada** segundo o sistema de pontos do bolão (definido na Seção 3).

O sistema deve:

1. Receber dois times participantes da Copa (entre as 48 seleções).
2. Buscar automaticamente o histórico recente de partidas de ambos.
3. Estimar a "força" de cada seleção e o número esperado de gols na partida.
4. Calcular o placar que oferece o **maior valor esperado de pontos** e apresentá-lo ao usuário.

### 1.2. Motivação

Hoje o palpite é feito de forma **semi-intuitiva**: estima-se mentalmente a força das equipes e um placar plausível. Este documento **formaliza** esse raciocínio em um algoritmo reproduzível, transparente e otimizado, eliminando o viés humano e maximizando matematicamente a pontuação.

### 1.3. Escopo

**Dentro do escopo (v1.0):**
- Previsão para uma partida individual entre duas das 48 seleções da Copa 2026.
- Coleta automática de dados via API pública de futebol.
- Interface web para seleção dos times e visualização dos dados e do palpite.

**Fora do escopo (v1.0):**
- Simulação de chaveamento/mata-mata completo do torneio.
- Modelagem de eventos intra-jogo (cartões, lesões, escalações específicas).
- Treinamento de modelos de machine learning supervisionados (a abordagem é estatística/paramétrica).

---

## 2. Stack Técnica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Computação numérica | `numpy`, `scipy` |
| Manipulação de dados | `pandas` |
| Visualização | `matplotlib` |
| Interface | `streamlit` |
| Utilitários de sistema | `sys` |
| Coleta de dados | API pública de futebol (ex.: API-Football, football-data.org) |

> **Nota sobre `sklearn`:** listado nas premissas iniciais, mas a abordagem consolidada é paramétrica (modelo de Poisson com ajuste por ponto-fixo). O `sklearn` permanece como dependência **opcional**, útil caso futuramente se adote calibração por regressão.

---

## 3. Regras de Pontuação

Cada palpite recebe pontos após o jogo conforme as regras abaixo.

### 3.1. Pontuação base

- **+3 pontos** por acertar o resultado (vitória do time A, vitória do time B ou empate).

### 3.2. Pontuação de bônus

Sobre a pontuação base, aplica-se **no máximo um** bônus adicional — **vale apenas o de maior valor** entre os critérios acertados (os bônus **não acumulam** entre si):

| Prioridade | Critério acertado | Bônus |
|:---:|---|:---:|
| 1 | Placar exato | +5 |
| 2 | Número de gols do vencedor | +3 |
| 3 | Diferença de gols | +2 |
| 4 | Número de gols do perdedor | +1 |
| 4 | Goleada (diferença > 3 gols) | +1 |

### 3.3. Formalização da função de pontuação

Seja o palpite $(p_A, p_B)$ e o resultado real $(r_A, r_B)$. A pontuação é:

$$
\text{Pontos} = \text{base}(p, r) + \text{bonus}(p, r)
$$

onde:

- $\text{base}(p, r) = 3$ se $\text{sinal}(p_A - p_B) = \text{sinal}(r_A - r_B)$, senão $0$.
- $\text{bonus}(p, r) = 0$ caso a base seja $0$; caso contrário, é o **máximo** entre os bônus dos critérios atendidos:

$$
\text{bonus}(p, r) = \max
\begin{cases}
5 & \text{se } (p_A, p_B) = (r_A, r_B) \\
3 & \text{se gols do vencedor coincidem} \\
2 & \text{se } (p_A - p_B) = (r_A - r_B) \\
1 & \text{se gols do perdedor coincidem} \\
1 & \text{se ambos têm goleada } (|p_A - p_B| > 3 \text{ e } |r_A - r_B| > 3) \\
0 & \text{caso contrário}
\end{cases}
$$

> **Premissa:** o bônus só é considerado quando a pontuação base foi obtida (i.e., o resultado foi acertado). Esta interpretação deve ser validada com o regulamento do bolão antes da implementação.

---

## 4. Algoritmo

O algoritmo é composto por quatro etapas sequenciais: **coleta de dados**, **cálculo de força**, **estimativa de gols** e **otimização do palpite**.

### 4.1. Etapa 1 — Coleta de dados

Para a partida entre os times $A$ e $B$, reúne-se o **histórico recente** de cada
um (jogos imediatamente anteriores à Copa, mais os jogos da própria Copa já
disputados):

1. **Histórico pré-Copa (embutido):** os jogos recentes das 48 seleções
   (amistosos e eliminatórias de 2026) ficam pré-coletados em
   `pre_wc_data.py`. Decisão tomada porque nenhuma API gratuita serve a forma
   recente das seleções — football-data.org (free) só dá jogos da própria Copa e
   API-Football (free) só libera temporadas 2022–2024.
2. **Jogos da Copa (em tempo real):** obtidos da API pública football-data.org
   conforme a competição avança, combinados ao histórico pré-Copa sem duplicatas.
3. Para cada partida, extrair: mandante, visitante, gols marcados e sofridos.
4. Construir o conjunto de adversários históricos. Adversários que **não
   pertencem** às 48 seleções da Copa recebem **força mínima** (ver Seção 4.2.4).

> A camada de dados é abstrata (`MatchDataSource`): além das fontes reais acima,
> há uma fonte **sintética** determinística para demonstração/offline.

### 4.2. Etapa 2 — Cálculo da força (modelo iterativo)

A "força" de um time é decomposta em dois ratings, resolvendo a **circularidade** (a força de um time depende da força de seus adversários, que por sua vez dependem da de outros times):

- **Poder ofensivo** $O_i$: tendência do time $i$ a marcar gols.
- **Fragilidade defensiva** $D_i$: tendência do time $i$ a sofrer gols.

O par $(O_i, D_i)$ é estimado por **ponto-fixo iterativo** (modelo de Poisson de Maher, conceitualmente próximo a Elo/PageRank), conforme abaixo.

#### 4.2.1. Definições

Seja $\mu$ a média de gols marcados por time por partida no histórico agregado. Para cada partida em que o time $i$ enfrentou o time $o$:

- Espera-se que $i$ marque $\mu \cdot O_i \cdot D_o$ gols.
- Espera-se que $i$ sofra $\mu \cdot O_o \cdot D_i$ gols.

#### 4.2.2. Inicialização

$$
O_i \leftarrow 1, \quad D_i \leftarrow 1 \quad \text{para todo time } i \text{ das 48 seleções.}
$$

#### 4.2.3. Iteração (até convergência)

Repetir, para cada time $i$, até que a variação máxima entre iterações seja inferior a $\varepsilon$ (ex.: $10^{-4}$):

$$
O_i \leftarrow \frac{\text{total de gols marcados por } i}{\displaystyle\sum_{\text{partidas de } i} \mu \cdot D_{o}}
\qquad
D_i \leftarrow \frac{\text{total de gols sofridos por } i}{\displaystyle\sum_{\text{partidas de } i} \mu \cdot O_{o}}
$$

Times fortes ofensivamente marcam muito **mesmo contra defesas sólidas** (baixo $D_o$); times defensivamente frágeis sofrem muito **mesmo contra ataques fracos** (baixo $O_o$). A iteração propaga essas relações por toda a rede de confrontos até estabilizar.

#### 4.2.4. Tratamento de "força mínima"

Adversários históricos fora das 48 seleções não participam da iteração: recebem valores fixos de força mínima — baixo poder ofensivo e alta fragilidade defensiva:

$$
O_{\text{ext}} = O_{\min}, \quad D_{\text{ext}} = D_{\max}
$$

calibrados como percentis extremos observados no histórico (ex.: 5º percentil de $O$ e 95º percentil de $D$).

#### 4.2.5. Regularização (encolhimento)

Com poucas partidas (a janela de 90 dias rende ~10 a 15 jogos por seleção), o
ajuste por máxima verossimilhança produz ratings instáveis — uma goleada isolada
pode disparar $O$ ou $D$ para valores irreais. Aplica-se então um **encolhimento
empírico-Bayes**: adicionam-se $r$ partidas virtuais contra um adversário médio
($O = D = 1$), nas quais o time marca e sofre exatamente $\mu$ gols. As equações
de atualização passam a ser:

$$
O_i \leftarrow \frac{\text{gols marcados} + r\mu}{\mu\left(\sum D_o + r\right)}
\qquad
D_i \leftarrow \frac{\text{gols sofridos} + r\mu}{\mu\left(\sum O_o + r\right)}
$$

Times com muitos jogos quase não são afetados; times com amostra pequena são
puxados para $1$. Como bônus, o adversário virtual **ancora a escala**,
eliminando a indeterminação $O_i \cdot c$ / $D_j / c$ do modelo puro. O padrão
adotado é $r = 2$.

### 4.3. Etapa 3 — Estimativa de gols esperados

Para a partida $A \times B$, os gols esperados de cada time são:

$$
\lambda_A = \mu \cdot O_A \cdot D_B
\qquad
\lambda_B = \mu \cdot O_B \cdot D_A
$$

Modela-se o número de gols de cada time como uma **distribuição de Poisson** independente. A probabilidade de o time $A$ marcar exatamente $x$ gols e o time $B$ marcar $y$ gols é:

$$
P(x, y) = \underbrace{\frac{e^{-\lambda_A}\,\lambda_A^{\,x}}{x!}}_{P_A(x)} \cdot \underbrace{\frac{e^{-\lambda_B}\,\lambda_B^{\,y}}{y!}}_{P_B(y)}
$$

Isso gera uma **matriz de probabilidades** sobre todos os placares plausíveis (ex.: $x, y \in \{0, 1, \dots, 8\}$).

### 4.4. Etapa 4 — Otimização do palpite

O objetivo é escolher o palpite $(p_A, p_B)$ que **maximiza os pontos esperados**:

$$
(p_A^*, p_B^*) = \arg\max_{(p_A, p_B)} \; \sum_{x, y} P(x, y) \cdot \text{Pontos}\big((p_A, p_B), (x, y)\big)
$$

**Conjunto de candidatos.** A intuição original ("margem de ±1 gol") corresponde a avaliar os candidatos em torno dos gols esperados:

$$
p_A \in \{\lfloor\lambda_A\rceil - 1,\; \lfloor\lambda_A\rceil,\; \lfloor\lambda_A\rceil + 1\}, \quad
p_B \in \{\lfloor\lambda_B\rceil - 1,\; \lfloor\lambda_B\rceil,\; \lfloor\lambda_B\rceil + 1\}
$$

> **Recomendação:** como o cálculo é barato, avaliar a **grade completa** de placares plausíveis (ex.: $0$ a $6$ para cada time) em vez de apenas a janela ±1. Isso garante o ótimo global de pontos esperados, e não apenas o ótimo local em torno da média — relevante porque o placar de maior probabilidade nem sempre é o de maior pontuação esperada.

O placar vencedor $(p_A^*, p_B^*)$ é o palpite final.

### 4.5. Resumo do fluxo

```
[Seleção dos times A e B]
            │
            ▼
[Coleta: histórico de 90 dias via API]
            │
            ▼
[Força: O_i, D_i por iteração de ponto-fixo]   ◄── força mínima p/ times externos
            │
            ▼
[Gols esperados: λ_A, λ_B  →  matriz Poisson P(x,y)]
            │
            ▼
[Otimização: argmax dos pontos esperados]
            │
            ▼
[Palpite ótimo (p_A*, p_B*)]
```

---

## 5. Interface (Streamlit)

### 5.1. Requisitos funcionais

| ID | Requisito |
|---|---|
| UI-1 | Dois seletores (dropdown) para escolher o time A e o time B entre as 48 seleções. |
| UI-2 | Botão para disparar a análise. |
| UI-3 | Exibição do histórico recente (últimos 90 dias) de cada time, com placares. |
| UI-4 | Exibição da força calculada ($O$, $D$) de cada time. |
| UI-5 | Exibição dos gols esperados ($\lambda_A$, $\lambda_B$). |
| UI-6 | Exibição do **palpite ótimo** com sua pontuação esperada. |
| UI-7 | Visualização gráfica (`matplotlib`) da matriz de probabilidades de placares. |

### 5.2. Esboço de layout

```
┌────────────────────────────────────────────────┐
│   Previsor Copa 2026                            │
├────────────────────────────────────────────────┤
│   Time A: [ Brasil  ▼ ]   Time B: [ França ▼ ]  │
│                  [ Analisar ]                    │
├────────────────────────────────────────────────┤
│   Histórico (90d)     │   Força (O / D)          │
│   ...                 │   ...                    │
├────────────────────────────────────────────────┤
│   Gols esperados: λ_A = 1.8   λ_B = 1.2         │
│   ► Palpite ótimo: 2 x 1   (E[pontos] = 4.3)    │
│   [ heatmap de probabilidades de placar ]       │
└────────────────────────────────────────────────┘
```

---

## 6. Requisitos Não-Funcionais

| ID | Requisito |
|---|---|
| NF-1 | A análise de uma partida deve concluir em poucos segundos após a coleta dos dados. |
| NF-2 | Resultados de chamadas à API devem ser **cacheados** para evitar requisições repetidas e respeitar limites de taxa (rate limits). |
| NF-3 | O algoritmo deve ser **determinístico**: mesmos dados de entrada produzem o mesmo palpite. |
| NF-4 | Falhas na coleta (API indisponível, time sem histórico suficiente) devem ser tratadas com mensagens claras ao usuário. |
| NF-5 | O código deve separar claramente as camadas de coleta, cálculo e interface, para permitir testes unitários do algoritmo isoladamente. |

---

## 7. Premissas e Decisões de Projeto

| Tema | Decisão | Justificativa |
|---|---|---|
| Circularidade da força | Ponto-fixo iterativo (estilo Elo/Maher) | Resolve corretamente a dependência mútua entre forças dos times. |
| Bônus de pontuação | Vale apenas o maior (não acumulam) | Interpretação literal de "vale o maior" nas premissas originais. |
| Fonte de dados | API pública de futebol | Dados estruturados e confiáveis; mais robusto que web scraping. |
| Distribuição de gols | Poisson independente | Padrão consagrado para modelagem de gols no futebol; simples e eficaz. |
| Independência entre times | Assumida | Simplificação aceita na v1.0; pode ser refinada (ver Seção 8). |

---

## 8. Verificação e Análise

### 8.1. Artigo e análise empírica

A metodologia, a verificação e a análise de desempenho estão documentadas em
um artigo em LaTeX em [`artigo/forca-probabilidades-copa-2026.tex`](artigo/forca-probabilidades-copa-2026.tex).
O artigo inclui:

- **Metodologia:** resumo das seções 4.1–4.4 deste PRD.
- **Backtest walk-forward:** implementado em [`backtest.py`](src/copa2026/backtest.py),
  testa o previsor em histórico real sem vazamento de dados (look-ahead bias).
  Fornece o grau de confiança empírico (taxa de acerto dos resultados previstos).
- **Probabilidade de título:** implementado em [`championship.py`](src/copa2026/championship.py),
  estima a probabilidade de cada seleção sagrar-se campeã por programação
  dinâmica sobre o chaveamento, somando sobre a distribuição de adversários.
- **Formatadores LaTeX:** implementados em [`relatorio.py`](src/copa2026/relatorio.py),
  geram tabelas e figuras prontas para inclusão no documento.
- **Script regenerável:** [`scripts/gerar_analise.py`](scripts/gerar_analise.py)
  executa o backtest, calcula probabilidades de título e regenera a figura e as
  tabelas do artigo em uma única chamada.

Para regenerar: `python scripts/gerar_analise.py` e recompilar com
`latexmk -pdf artigo/forca-probabilidades-copa-2026.tex`.

### 8.2. Trabalhos Futuros

- **Correlação de placares:** substituir o Poisson independente por um modelo Dixon-Coles, que corrige a dependência em placares baixos (0-0, 1-1).
- **Ponderação temporal:** dar mais peso a partidas mais recentes dentro da janela de 90 dias.
- **Fator mando de campo / sede neutra:** incorporar (ou explicitamente neutralizar) o efeito de jogar em casa.
- **Calibração via `sklearn`:** ajustar os parâmetros do modelo por regressão sobre resultados históricos do bolão.
- **Simulação de torneio:** estender a previsão de partida única para projeção de chaveamento completo.

---

## 9. Aba "Tabela da Copa"

### 9.1. Objetivo

Exibir o chaveamento completo da Copa 2026 preenchido até a final: jogos já
disputados com resultado real, jogos futuros com o palpite ótimo do previsor.
A aba vive em `app.py` ao lado da aba original "Previsor" e usa exclusivamente
os módulos descritos abaixo — não modifica a lógica do pipeline existente.

### 9.2. Fonte de dados

A API football-data.org (`/competitions/WC/matches`, via `FootballDataSource`)
retorna todos os jogos da Copa em uma única chamada: fase de grupos, resultados
reais e calendário futuro.

O que a API **não** fornece é o chaveamento do mata-mata (quem joga contra
quem com base nos classificados). Esse mapeamento está embutido em
`bracket_data.py` como dicionário estático (`MATCHES`, jogos 73–104), derivado
do regulamento FIFA. Os confrontos dos 16 melhores terceiros colocados seguem
a tabela oficial de alocação FIFA, gerada em `third_place_data.py` (495 linhas,
produzidas pelo script `scripts/generate_third_place_data.py` — não editar à
mão).

### 9.3. Força global

A força das 48 seleções é calculada **uma única vez** por `compute_global_ratings`
(`ratings.py`), reunindo o histórico de todas as seleções e rodando o modelo
iterativo de ponto-fixo (PRD §4.2) sobre esse pool comum. Isso permite prever
as ~100 partidas do torneio sem recalcular ratings por par de times. Por design,
o ajuste global (uma calibração sobre todos os 48 times) pode produzir λ e
palpites ligeiramente diferentes dos gerados pelo Previsor, que recalcula ratings
por par em `pipeline.predict_match` — a diferença é esperada e reflete os dois
modos de uso.

### 9.4. Regra de mistura real/previsto

Para cada jogo da fase de grupos (`GROUP_STAGE`):

- **Disputado (`FINISHED`):** usa o placar real da API.
- **Não disputado:** usa o palpite ótimo de `predict_scoreline` (`ratings.py`),
  que aplica as etapas 3 e 4 do algoritmo (λ + argmax de pontos esperados).

Para os jogos do mata-mata (73–104), a mesma regra se aplica: placar real se
`FINISHED`, previsto caso contrário. A API não vincula o jogo ao slot no
chaveamento; a correspondência é feita por ordem cronológica dentro de cada
fase (limitação documentada em `tournament.py`).

### 9.5. Classificação de grupo (FIFA)

Implementada em `standings.py` (`compute_group_table`). Ordem dos critérios:

1. Pontos (geral).
2. Saldo de gols (geral).
3. Gols marcados (geral).
4. Dentro do grupo empatado nos três anteriores: pontos, saldo e gols marcados
   **apenas nos confrontos diretos**.
5. Desempate determinístico por ordem alfabética de nome canônico (substituto
   para fair-play/sorteio, indisponíveis sem dados de cartões).

Os oito melhores terceiros são selecionados por `rank_third_places` (pontos →
saldo → gols pró → grupo) e alocados conforme `BEST_THIRD_ALLOCATION`
(`third_place_data.py`).

### 9.6. Vencedor no mata-mata

`knockout_winner` (`ratings.py`) determina o time que avança:

- **Palpite com vencedor:** avança quem marcou mais no palpite.
- **Palpite empatado:** avança o time de maior λ (gols esperados); se λ
  empatar, o de maior qualidade ofensiva/defensiva ($O/D$). O placar é
  exibido com o sufixo **(pên.)** na interface.

O simulador (`simulate_tournament`, `tournament.py`) propaga os vencedores
pelos slots `WM`/`LM` do `bracket_data.py`, iterando os jogos 73→104 em
ordem crescente para garantir que dependências já estejam resolvidas.

### 9.7. Resumo dos módulos

| Módulo | Responsabilidade |
|---|---|
| `ratings.py` | `compute_global_ratings`, `predict_scoreline`, `knockout_winner` |
| `standings.py` | `compute_group_table`, `rank_third_places` (critérios FIFA) |
| `bracket_data.py` | Mapa estático do chaveamento (jogos 73–104) |
| `third_place_data.py` | Tabela oficial de alocação dos 8 melhores terceiros (gerado) |
| `tournament.py` | `parse_fixtures`, `fetch_wc_fixtures`, `simulate_tournament`, `knockout_rows` |

---

## Apêndice A — Glossário

| Termo | Definição |
|---|---|
| **Força** | Medida da qualidade de uma seleção, decomposta em poder ofensivo $O$ e fragilidade defensiva $D$. |
| **Força mínima** | Valores fixos de força atribuídos a adversários históricos que não estão entre as 48 seleções da Copa. |
| **Gols esperados ($\lambda$)** | Número médio de gols que um time deve marcar na partida, segundo o modelo. |
| **Pontos esperados** | Média ponderada dos pontos de um palpite sobre todos os placares possíveis e suas probabilidades. |
| **Palpite ótimo** | Placar que maximiza os pontos esperados. |
