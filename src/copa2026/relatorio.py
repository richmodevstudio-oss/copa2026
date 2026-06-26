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


def macros_tex(
    resultado: BacktestResult,
    favorito: str,
    data_iso: str,
    por_time: dict[str, dict[str, float]],
) -> str:
    """Macros LaTeX com os números da análise (confiança, favorito e Brasil).

    ``por_time`` é o resultado de ``championship.probabilidades_titulo``; dele se
    extraem a probabilidade do favorito e a probabilidade e a posição do Brasil.
    """
    ranking = sorted(
        por_time, key=lambda t: por_time[t].get("CAMPEAO", 0.0), reverse=True
    )
    prob_favorito = por_time.get(favorito, {}).get("CAMPEAO", 0.0)
    prob_brasil = por_time.get("Brazil", {}).get("CAMPEAO", 0.0)
    pos_brasil = ranking.index("Brazil") + 1 if "Brazil" in ranking else 0
    linhas = [
        r"% gerado por scripts/gerar_analise.py — não editar à mão",
        r"\newcommand{\grauConfianca}{" + pct(resultado.confianca) + "}",
        r"\newcommand{\nJogosBacktest}{" + str(resultado.total) + "}",
        r"\newcommand{\nDecididos}{" + str(resultado.decididos) + "}",
        r"\newcommand{\nAcertos}{" + str(resultado.acertos) + "}",
        r"\newcommand{\nEmpatesExcluidos}{" + str(resultado.empates) + "}",
        r"\newcommand{\favoritoTitulo}{" + display_pt(favorito) + "}",
        r"\newcommand{\probFavorito}{" + pct(prob_favorito) + "}",
        r"\newcommand{\probBrasil}{" + pct(prob_brasil) + "}",
        r"\newcommand{\posBrasil}{" + str(pos_brasil) + r"\textsuperscript{o}}",
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
