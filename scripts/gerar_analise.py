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

    print(f"Backtest: {backtest.acertos}/{backtest.decididos} jogos decididos "
          f"(confiança {backtest.confianca:.1%}); "
          f"{backtest.empates} empate(s) excluído(s) de {backtest.total}")
    print(f"Favorito ao título: {display_pt(favorito)} "
          f"({por_time[favorito]['CAMPEAO']:.1%})")
    print(f"Artefatos escritos em {GERADO} e {FIGURAS}")


if __name__ == "__main__":
    main()
