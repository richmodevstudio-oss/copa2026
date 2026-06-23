"""Interface Streamlit do Previsor da Copa 2026 (PRD Seção 5).

Executar com:  streamlit run app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))


def _load_env_file(path: Path) -> None:
    """Carrega variáveis de um arquivo .env (KEY=VALUE), sem sobrescrever as já
    definidas no ambiente. Sem dependências externas."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(Path(__file__).parent / ".env")

from copa2026.bracket_data import STAGE_LABEL_PT, STAGE_OF  # noqa: E402
from copa2026.data_source import (  # noqa: E402
    CombinedDataSource,
    FootballDataSource,
    HardcodedDataSource,
)
from copa2026.pipeline import MatchPrediction, predict_match  # noqa: E402
from copa2026.ratings import compute_global_ratings  # noqa: E402
from copa2026.teams import WORLD_CUP_2026_TEAMS, display_pt  # noqa: E402
from copa2026.tournament import (  # noqa: E402
    TournamentResult,
    fetch_wc_fixtures,
    finished_results,
    simulate_tournament,
)

st.set_page_config(page_title="Previsor Copa 2026", page_icon="⚽", layout="wide")

MAX_GOALS = 8

_STAGE_ORDER = ["LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS",
                "THIRD_PLACE", "FINAL"]


@st.cache_data(show_spinner="Calculando com dados reais...")
def _run_real(home: str, away: str, fd_api_key: str, max_goals: int) -> MatchPrediction:
    # Base: histórico pré-Copa embutido. Com a chave da football-data,
    # acrescenta os jogos da própria Copa em tempo real.
    sources = [HardcodedDataSource()]
    if fd_api_key:
        sources.append(FootballDataSource(api_key=fd_api_key))
    source = CombinedDataSource(*sources)
    return predict_match(home, away, source, max_goals=max_goals)


def _history_df(prediction: MatchPrediction, team: str) -> pd.DataFrame:
    linhas = [
        {
            "Data": m.played_on.isoformat() if m.played_on else "-",
            "Mandante": display_pt(m.home),
            "Placar": f"{m.home_goals} x {m.away_goals}",
            "Visitante": display_pt(m.away),
        }
        for m in prediction.history
        if team in (m.home, m.away)
    ]
    df = pd.DataFrame(linhas)
    return df.sort_values("Data", ascending=False) if not df.empty else df


def _heatmap(prediction: MatchPrediction):
    m = prediction.prob_matrix
    max_goals = m.shape[0] - 1
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(m, origin="lower", cmap="viridis")
    ax.set_xlabel(f"Gols {display_pt(prediction.away)}")
    ax.set_ylabel(f"Gols {display_pt(prediction.home)}")
    ax.set_xticks(range(max_goals + 1))
    ax.set_yticks(range(max_goals + 1))
    px, py = prediction.palpite
    ax.scatter([py], [px], marker="*", s=260, color="red", edgecolors="white",
               label="Palpite ótimo")
    ax.legend(loc="upper right")
    fig.colorbar(im, ax=ax, label="Probabilidade")
    fig.tight_layout()
    return fig


def _knockout_rows(result: TournamentResult) -> dict[str, list[dict]]:
    """Linhas de exibição do mata-mata, agrupadas por rótulo de fase (em ordem)."""
    rows: dict[str, list[dict]] = {STAGE_LABEL_PT[s]: [] for s in _STAGE_ORDER}
    for k in result.knockout:
        origem = "✅ Real" if k.real else "🔮 Previsto"
        placar = f"{k.home_goals} x {k.away_goals}"
        if k.penalties:
            placar += " (pên.)"
        rows[STAGE_LABEL_PT[k.stage]].append(
            {
                "Jogo": f"{display_pt(k.home)} x {display_pt(k.away)}",
                "Placar": placar,
                "Avança": display_pt(k.winner),
                "Origem": origem,
            }
        )
    return rows


@st.cache_data(ttl=600, show_spinner="Buscando jogos e simulando o torneio...")
def _run_tournament(fd_api_key: str) -> TournamentResult:
    source = FootballDataSource(api_key=fd_api_key)
    fixtures = fetch_wc_fixtures(source)                      # única chamada à API
    wc_source = HardcodedDataSource(finished_results(fixtures), last=50)
    combined = CombinedDataSource(HardcodedDataSource(), wc_source)  # pré-Copa + Copa, sem rede extra
    ratings, mu = compute_global_ratings(combined)
    return simulate_tournament(fixtures, ratings, mu)


def _render_tabela(fd_api_key: str) -> None:
    st.subheader("🏆 Tabela da Copa — real + previsto")
    if not fd_api_key:
        st.info(
            "Defina FOOTBALL_DATA_API_KEY no .env para montar a tabela com os "
            "jogos e resultados reais da Copa."
        )
        return
    if st.button("🔄 Atualizar resultados"):
        _run_tournament.clear()
    try:
        result = _run_tournament(fd_api_key)
    except Exception as exc:  # rede/API
        st.error(f"Falha ao montar a tabela: {exc}")
        return

    st.markdown("### Fase de grupos")
    cols = st.columns(3)
    for idx, gr in enumerate(result.groups):
        with cols[idx % 3]:
            st.caption(f"Grupo {gr.group}")
            df = pd.DataFrame(
                [
                    {
                        "Seleção": display_pt(r.team), "P": r.points,
                        "J": r.played, "SG": r.goal_diff, "GP": r.goals_for,
                    }
                    for r in gr.table
                ]
            )
            st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("### Mata-mata")
    st.caption("✅ Real = já disputado · 🔮 Previsto = palpite do modelo")
    for label, linhas in _knockout_rows(result).items():
        if not linhas:
            continue
        st.markdown(f"**{label}**")
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)


st.title("⚽ Previsor de Resultados — Copa 2026")
st.caption(
    "Gera o palpite que maximiza os pontos esperados do bolão, "
    "a partir do histórico recente das seleções."
)

fd_api_key = os.environ.get("FOOTBALL_DATA_API_KEY", "")

aba_previsor, aba_tabela = st.tabs(["🎯 Previsor de placar", "🏆 Tabela da Copa"])

with aba_previsor:
    cfg1, cfg2, cfg3 = st.columns([2, 2, 1])
    with cfg1:
        home = st.selectbox(
            "Mandante", WORLD_CUP_2026_TEAMS,
            index=WORLD_CUP_2026_TEAMS.index("Brazil"), format_func=display_pt,
        )
    with cfg2:
        away = st.selectbox(
            "Visitante", WORLD_CUP_2026_TEAMS,
            index=WORLD_CUP_2026_TEAMS.index("France"), format_func=display_pt,
        )
    with cfg3:
        st.markdown("<div style='height: 1.75rem'></div>", unsafe_allow_html=True)
        analisar = st.button("Analisar", type="primary", use_container_width=True)

    st.divider()

    if home == away:
        st.warning("Selecione duas seleções diferentes.")
    elif analisar:
        try:
            pred = _run_real(home, away, fd_api_key, MAX_GOALS)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        except Exception as exc:  # erros de rede / API
            st.error(f"Falha ao buscar dados reais: {exc}")
            st.stop()

        st.subheader(f"{display_pt(pred.home)} x {display_pt(pred.away)}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Palpite ótimo", f"{pred.palpite[0]} x {pred.palpite[1]}")
        c2.metric("Pontos esperados", f"{pred.expected_points:.2f}")
        c3.metric("Gols esperados (λ)", f"{pred.lambda_home:.2f} x {pred.lambda_away:.2f}")

        if pred.low_confidence:
            st.warning(
                "⚠️ Previsão pouco confiável: histórico escasso "
                f"({display_pt(pred.home)}: {pred.home_matches} jogo(s), "
                f"{display_pt(pred.away)}: {pred.away_matches} jogo(s))."
            )

        st.subheader("Força das seleções (ataque O / fragilidade defensiva D)")
        forca = pd.DataFrame(
            {
                "Seleção": [display_pt(pred.home), display_pt(pred.away)],
                "Ataque (O)": [pred.home_ratings.attack, pred.away_ratings.attack],
                "Defesa (D)": [pred.home_ratings.defense, pred.away_ratings.defense],
            }
        )
        st.dataframe(forca, hide_index=True, use_container_width=True)

        st.subheader("Probabilidade de cada placar")
        st.pyplot(_heatmap(pred))

        prob_palpite = float(pred.prob_matrix[pred.palpite])
        st.subheader("Leitura")
        st.markdown(
            f"- **Placar mais valioso:** {pred.palpite[0]} x {pred.palpite[1]}\n"
            f"- **Probabilidade desse placar:** {prob_palpite:.1%}\n"
            f"- **Média de gols da base (μ):** {pred.mu:.2f}\n"
            f"- **Partidas no histórico:** {len(pred.history)}"
        )
        st.info(
            "O palpite é escolhido por **valor esperado de pontos**, não pelo "
            "placar mais provável — por isso pode diferir do pico do mapa."
        )

        st.subheader("Histórico recente (90 dias)")
        aba_home, aba_away = st.tabs([display_pt(pred.home), display_pt(pred.away)])
        with aba_home:
            st.dataframe(_history_df(pred, pred.home), hide_index=True,
                         use_container_width=True)
        with aba_away:
            st.dataframe(_history_df(pred, pred.away), hide_index=True,
                         use_container_width=True)
    else:
        st.info("Selecione as seleções acima e clique em **Analisar**.")

with aba_tabela:
    _render_tabela(fd_api_key)

st.divider()
if fd_api_key:
    st.caption("✅ Histórico pré-Copa + jogos da Copa (football-data.org).")
else:
    st.caption(
        "Histórico pré-Copa embutido. Defina FOOTBALL_DATA_API_KEY no .env "
        "para incluir os jogos da própria Copa."
    )
