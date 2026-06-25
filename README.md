# Copa do Mundo 2026 — Análise Estatística

Modela a **força ofensiva e defensiva** das seleções a partir da forma recente
(janela de 90 dias) e, com a distribuição de **Poisson**, estima probabilidades
de resultado e de título para a Copa do Mundo de 2026. A metodologia está
detalhada no [`prd.md`](prd.md) e no artigo em [`artigo/`](artigo/).

O projeto tem duas faces sobre o mesmo modelo:

- **Artigo** ([`artigo/`](artigo/)) — análise estatística: verificação empírica
  do modelo (*backtest*) e probabilidade de cada seleção ser campeã.
- **App Streamlit** ([`app.py`](app.py)) — aplicação prática que sugere, para um
  bolão, o placar de **maior valor esperado de pontos**, além de uma tabela da
  Copa com o chaveamento real + previsto.

## Como funciona (resumo)

1. **Coleta** o histórico de 90 dias das duas seleções.
2. **Força** — calcula ratings ofensivo/defensivo (`O`/`D`) por ponto-fixo
   iterativo, resolvendo a circularidade entre as forças.
3. **Previsão** — estima os gols esperados (`λ`) e a matriz de probabilidades
   de cada placar via Poisson.
4. **Otimização** — escolhe o placar de maior **valor esperado de pontos**.

## Artigo

Um artigo em LaTeX com a metodologia, a verificação empírica (backtest) e a
probabilidade de título está em [`artigo/`](artigo/). Regenerar os números:
`python scripts/gerar_analise.py` e recompilar com
`latexmk -pdf artigo/forca-probabilidades-copa-2026.tex`.

## Instalação

```bash
pip install -r requirements.txt
```

## Interface

```bash
streamlit run app.py
```

Os controles (mandante, visitante e o botão **Analisar**) ficam no topo da tela,
sem barra lateral — pensado para funcionar bem também no celular. O máximo de gols
da grade é fixo em 8.

A interface usa sempre **dados reais**: a forma recente das 48 seleções (amistosos
e eliminatórias de 2026, anteriores ao início da Copa) vem **embutida** em
`copa2026/pre_wc_data.py`. Para incluir os jogos da própria Copa conforme
acontecem, configure a chave gratuita da
[football-data.org](https://www.football-data.org/) em um arquivo `.env`:

```bash
cp .env.example .env
# edite .env e preencha FOOTBALL_DATA_API_KEY=...
```

O `.env` é lido automaticamente pelo app e **não é versionado** (ver `.gitignore`).
A fonte combinada (`CombinedDataSource`) junta o histórico pré-Copa (hardcoded) com
os jogos da Copa (football-data.org), sem duplicatas. Sem a chave, usa apenas o
histórico pré-Copa.

> Há ainda uma fonte **sintética** determinística (`SyntheticDataSource`) usada nos
> testes e disponível para uso programático, mas não exposta na interface.

> **Por que hardcoded?** Nenhuma API gratuita serve a forma recente das seleções:
> football-data.org (free) só dá jogos da própria Copa, e API-Football (free) só
> libera temporadas 2022–2024. Os dados pré-Copa foram coletados da ESPN e
> embutidos. Para atualizar: `python scripts/generate_pre_wc_data.py`.

## Uso programático

```python
from copa2026.data_source import HardcodedDataSource
from copa2026.pipeline import predict_match

pred = predict_match("Brazil", "France", HardcodedDataSource())
print(pred.palpite, pred.expected_points)
```

## Testes

```bash
python -m pytest
```

## Estrutura

```
src/copa2026/
  models.py        # Match, TeamRatings
  teams.py         # as 48 seleções (nome canônico, rótulo PT, apelidos)
  scoring.py       # função de pontuação do bolão (PRD §3)
  strength.py      # cálculo de força iterativo (PRD §4.2)
  prediction.py    # gols esperados + matriz Poisson (PRD §4.3)
  optimizer.py     # palpite que maximiza pontos esperados (PRD §4.4)
  data_source.py   # fontes de dados: hardcoded / combinada / football-data / sintética
  pre_wc_data.py   # histórico pré-Copa embutido (gerado)
  pipeline.py      # orquestra as 4 etapas (PRD §4.5)
  ratings.py       # força global (1×) + predict_scoreline + knockout_winner
  standings.py     # classificação de grupo (critérios FIFA)
  bracket_data.py  # mapa fixo do chaveamento (jogos 73–104)
  third_place_data.py  # tabela oficial dos 8 melhores terceiros (gerado)
  tournament.py    # simulação do torneio (real + previsto)
  backtest.py      # verificação walk-forward (grau de confiança)
  championship.py  # probabilidade de título por DP no chaveamento
  relatorio.py     # formatadores LaTeX da análise
app.py             # interface Streamlit (previsor + tabela da Copa)
artigo/            # artigo LaTeX (metodologia, backtest, prob. de título)
scripts/
  generate_pre_wc_data.py       # regenera pre_wc_data.py
  generate_third_place_data.py  # regenera third_place_data.py
  gerar_analise.py              # regenera as tabelas/figura do artigo
tests/             # suíte de testes (TDD)
```
