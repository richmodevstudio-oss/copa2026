# CLAUDE.md

Orientações para o Claude Code trabalhar neste repositório.

## O que é

Previsor de placares para a Copa 2026: gera o palpite que **maximiza os pontos
esperados** do bolão. O raciocínio completo está em [`prd.md`](prd.md); o resumo
de uso, no [`README.md`](README.md).

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

`app.py` é a UI Streamlit (camada fina sobre `pipeline.predict_match`).

## Dados

Nenhuma API gratuita serve a forma recente das seleções, então o histórico
pré-Copa é **hardcoded** em `pre_wc_data.py`. Para incluir os jogos da própria
Copa em tempo real, defina `FOOTBALL_DATA_API_KEY` no `.env` (não versionado);
`CombinedDataSource` junta as duas fontes sem duplicatas.

Regenerar o histórico embutido: `python scripts/generate_pre_wc_data.py`.

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

## Deploy

Produção em **https://palpites.richmo.media** (VPS, Streamlit sob systemd +
nginx + TLS Let's Encrypt). Provisionamento em `scripts/deploy_server.sh`
(rodar no servidor como root). Para atualizar o app já no ar: enviar os arquivos
alterados para `/opt/copa2026/` e `systemctl restart copa2026`.
