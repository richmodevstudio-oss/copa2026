# CLAUDE.md

Orientações para o Claude Code trabalhar neste repositório.

## O que é

Análise estatística da Copa 2026: modela a força das seleções (forma recente +
Poisson) e, sobre o mesmo modelo, entrega (a) um **app Streamlit** que sugere o
placar de maior valor esperado para um bolão e (b) um **artigo** (`artigo/`) com
a verificação empírica do modelo e a probabilidade de título. O raciocínio
completo está em [`prd.md`](prd.md); o resumo de uso, no [`README.md`](README.md).

Pipeline em 4 etapas: **coleta** do histórico recente → **força** (ratings
ofensivo/defensivo por ponto-fixo) → **previsão** (gols esperados λ + matriz
Poisson de placares) → **otimização** (placar de maior valor esperado).

## Arquitetura

Lógica em `src/copa2026/` (pacote importável; `pythonpath = src` no `pytest.ini`):

- `models.py` — `Match`, `TeamRatings`.
- `teams.py` — as 48 seleções (nome canônico, rótulo PT, apelidos) + `display_pt`.
- `scoring.py` — pontuação do bolão (PRD §3).
- `strength.py` — força iterativa (PRD §4.2).
- `prediction.py` — λ + matriz Poisson (PRD §4.3).
- `optimizer.py` — palpite ótimo (PRD §4.4).
- `data_source.py` — fontes: `HardcodedDataSource`, `FootballDataSource`,
  `CombinedDataSource`, `SyntheticDataSource`.
- `pre_wc_data.py` — histórico pré-Copa embutido (**gerado**, não editar à mão).
- `pipeline.py` — orquestra as 4 etapas via `predict_match`.
- `ratings.py` — força global (1×) + `predict_scoreline` + `knockout_winner` (PRD §4.2–4.4).
- `standings.py` — classificação de grupo pelos critérios FIFA.
- `bracket_data.py` — mapa fixo do chaveamento (jogos 73–104, escrito à mão).
- `third_place_data.py` — tabela oficial dos 8 melhores terceiros (**gerado**, não editar à mão).
- `tournament.py` — simulação do torneio completo (real + previsto) via `simulate_tournament`.
- `backtest.py` — verificação walk-forward (grau de confiança = acerto do vencedor).
- `championship.py` — probabilidade de título por DP no chaveamento.
- `relatorio.py` — formatadores LaTeX das análises do artigo.

`app.py` é a UI Streamlit com duas abas: **Previsor** (palpite por partida) e
**Tabela da Copa** (chaveamento completo até a final). O artigo em `artigo/` é
gerado por `scripts/gerar_analise.py` (tabelas/figura) + `latexmk`.

## Dados

Nenhuma API gratuita serve a forma recente das seleções, então o histórico
pré-Copa é **hardcoded** em `pre_wc_data.py`. Para incluir os jogos da própria
Copa em tempo real, defina `FOOTBALL_DATA_API_KEY` no `.env` (não versionado);
`CombinedDataSource` junta as duas fontes sem duplicatas.

Regenerar o histórico embutido: `python scripts/generate_pre_wc_data.py`.

Regenerar a tabela dos melhores terceiros: `python scripts/generate_third_place_data.py`.

## Comandos

```bash
pip install -r requirements.txt   # dependências
python -m pytest                  # testes (suíte em tests/, TDD)
streamlit run app.py              # interface local
```

## Convenções

- **TDD**: há suíte em `tests/`; ao mexer na lógica, escreva/atualize o teste antes.
- Strings da UI e docs em **português**.
- Toda fórmula/etapa referencia a seção correspondente do `prd.md` — mantenha
  esse mapeamento ao alterar a lógica.
