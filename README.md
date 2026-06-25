# Previsor de Resultados — Copa 2026

Gera o palpite de placar que **maximiza os pontos esperados** do bolão, conforme
especificado em [`prd.md`](prd.md).

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

## Deploy

A aplicação roda em produção em **https://palpites.richmo.media** (VPS, Streamlit
sob systemd + nginx com TLS Let's Encrypt). O provisionamento do servidor está em
[`scripts/deploy_server.sh`](scripts/deploy_server.sh). Para atualizar o app já
provisionado, basta enviar os arquivos alterados e reiniciar o serviço.

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
app.py             # interface Streamlit (PRD §5)
scripts/
  generate_pre_wc_data.py  # regenera pre_wc_data.py a partir da ESPN
tests/             # suíte de testes (TDD)
```
