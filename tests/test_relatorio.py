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
