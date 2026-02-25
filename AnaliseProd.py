# ─────────────────────────────────────────────────────────────────────
#  Dashboard de Produção Diária — CAMESA
# ─────────────────────────────────────────────────────────────────────
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# ── Configuração da página ──────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Produção — CAMESA",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personalizado ───────────────────────────────────────────────
st.markdown("""
<style>
    /* cards dos KPIs */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,.25);
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-size: 0.82rem !important;
        text-transform: uppercase;
        letter-spacing: .5px;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #f1f5f9 !important;
        font-size: 1.55rem !important;
        font-weight: 700;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
    }
    section[data-testid="stSidebar"] {
        background: #0f172a;
    }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Fonte de dados ──────────────────────────────────────────────────
URL_CSV = (
    "https://docs.google.com/spreadsheets/d/"
    "15s_ZttYG4UkSprgp4V_9gUBSgg7p8JRTiSQZL4xBi6Y/export?format=csv&gid=783677968"
)

# Meta diária fixa por facção
META_FACCAO = {
    "VANIA": 2000,
    "CAROL": 5000,
    "NATCHELLY": 2000,
    "MARCIA": 1500,
    "RUTE": 3000,
    "JÔ": 1000,
    "PREVITTEX": 2500,
    "FERNANDA": 3000,
}

MESES_NOME = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

# ── Helpers ─────────────────────────────────────────────────────────
def fmt_br(v, decimals=0):
    """Formata número no padrão brasileiro (ponto como milhar, vírgula decimal)."""
    txt = f"{v:,.{decimals}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def dias_uteis(datas):
    """Conta dias úteis (seg-sex) no conjunto de datas."""
    d = pd.to_datetime(datas).dropna().dt.normalize().drop_duplicates()
    return int((d.dt.weekday <= 4).sum())


# ── Carga e tratamento ──────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Carregando dados da planilha…")
def carregar_dados():
    df_raw = pd.read_csv(URL_CSV, header=1)
    df_raw.columns = [str(c).strip() for c in df_raw.columns]

    id_cols = ["FACÇÃO", "PRODUTO", "Meta Diária"]
    excluir = {"QTDE PRODUZIDA", "META MENSAL", "META DIARIA", "FALTA"}

    date_cols = []
    for c in df_raw.columns:
        if c in id_cols or c in excluir or c.startswith("Column"):
            continue
        try:
            pd.to_datetime(c, dayfirst=True)
            date_cols.append(c)
        except Exception:
            continue

    df = df_raw.melt(
        id_vars=id_cols, value_vars=date_cols,
        var_name="Data", value_name="Produzido",
    )
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, format="mixed", errors="coerce")
    df["FACÇÃO"] = df["FACÇÃO"].astype(str).str.strip().str.upper()
    df["Produzido"] = (
        pd.to_numeric(df["Produzido"].replace("-", "0"), errors="coerce")
        .fillna(0)
    )
    df = df.dropna(subset=["Data"]).copy()
    df = df[
        df["FACÇÃO"].ne("NAN")
        & df["FACÇÃO"].ne("")
        & df["FACÇÃO"].ne("FACÇÃO")
        & df["FACÇÃO"].notna()
    ]
    df["Ano"] = df["Data"].dt.year
    df["Mês"] = df["Data"].dt.month
    df["Semana"] = df["Data"].dt.isocalendar().week.astype(int)
    df["DiaSemana"] = df["Data"].dt.day_name()
    return df


# ── Dados ───────────────────────────────────────────────────────────
df = carregar_dados()

# ── Sidebar — Filtros ───────────────────────────────────────────────
st.sidebar.image(
    "https://img.icons8.com/fluency/96/combo-chart.png", width=64,
)
st.sidebar.title("📊 Filtros")

anos = sorted(df["Ano"].unique())
ano_sel = st.sidebar.multiselect("Ano", anos, default=anos)
df_f = df[df["Ano"].isin(ano_sel)]

meses_disp = sorted(df_f["Mês"].unique())
mes_sel = st.sidebar.multiselect(
    "Mês", meses_disp, default=meses_disp,
    format_func=lambda m: MESES_NOME[m],
)
df_f = df_f[df_f["Mês"].isin(mes_sel)]

faccoes_disp = sorted(df_f["FACÇÃO"].unique())
facc_sel = st.sidebar.multiselect("Facção", faccoes_disp, default=faccoes_disp)
df_f = df_f[df_f["FACÇÃO"].isin(facc_sel)].copy()

st.sidebar.divider()
st.sidebar.caption("Dados atualizados a cada 5 min.")

# ── Métricas globais ────────────────────────────────────────────────
prod_total = df_f["Produzido"].sum()
meta_dia_total = sum(META_FACCAO.get(f, 0) for f in facc_sel)
d_uteis = dias_uteis(df_f["Data"])
meta_periodo = meta_dia_total * d_uteis
saldo = prod_total - meta_periodo
ating = (prod_total / meta_periodo) if meta_periodo > 0 else 0
media_dia = prod_total / d_uteis if d_uteis else 0

# ── Header ──────────────────────────────────────────────────────────
st.markdown("## 🏭 Dashboard de Produção Diária — CAMESA")
st.markdown("---")

# ── KPI cards (6 colunas) ──────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Produzido", fmt_br(prod_total))
k2.metric("Meta do Período", fmt_br(meta_periodo))
k3.metric("Saldo", fmt_br(saldo), delta=fmt_br(saldo), delta_color="normal")
k4.metric("Atingimento", f"{ating*100:.1f}%",
          delta=f"{(ating-1)*100:+.1f} pp" if meta_periodo else "–")
k5.metric("Média / Dia", fmt_br(media_dia))
k6.metric("Dias Úteis", str(d_uteis))

st.markdown("")  # espaço

# ═════════════════════════════════════════════════════════════════════
#  ABAS
# ═════════════════════════════════════════════════════════════════════
tab_vis, tab_facc, tab_rank, tab_dados = st.tabs(
    ["📈 Visão Geral", "🏢 Por Facção", "🏆 Ranking & Alertas", "📋 Dados"]
)

# ─── Tab 1 — Visão Geral ───────────────────────────────────────────
with tab_vis:

    # 1.1  Produção diária × meta (barras + linha)
    serie = (
        df_f.groupby("Data", as_index=False)["Produzido"]
        .sum()
        .sort_values("Data")
    )
    serie["Meta Dia"] = meta_dia_total
    serie["Acum. Produzido"] = serie["Produzido"].cumsum()
    serie["Acum. Meta"] = serie["Meta Dia"].cumsum()

    fig1 = go.Figure()
    # cores condicionais: verde se atingiu, vermelho se não
    cores = [
        "#22c55e" if p >= m else "#ef4444"
        for p, m in zip(serie["Produzido"], serie["Meta Dia"])
    ]
    fig1.add_bar(
        x=serie["Data"], y=serie["Produzido"],
        name="Produzido", marker_color=cores,
    )
    fig1.add_scatter(
        x=serie["Data"], y=serie["Meta Dia"],
        mode="lines", name="Meta Diária",
        line=dict(color="#facc15", width=2, dash="dash"),
    )
    fig1.update_layout(
        title="Produção Diária × Meta",
        xaxis_title="Data", yaxis_title="Peças",
        template="plotly_dark",
        legend=dict(orientation="h", y=-0.15),
        margin=dict(t=50, b=60),
    )
    st.plotly_chart(fig1, width="stretch")

    # 1.2  Acumulado produzido vs acumulado meta
    col_a, col_b = st.columns(2)

    with col_a:
        fig_acum = go.Figure()
        fig_acum.add_scatter(
            x=serie["Data"], y=serie["Acum. Produzido"],
            mode="lines+markers", name="Produzido Acumulado",
            line=dict(color="#3b82f6", width=3),
        )
        fig_acum.add_scatter(
            x=serie["Data"], y=serie["Acum. Meta"],
            mode="lines", name="Meta Acumulada",
            line=dict(color="#facc15", width=2, dash="dot"),
        )
        fig_acum.update_layout(
            title="Acumulado: Produção × Meta",
            template="plotly_dark",
            legend=dict(orientation="h", y=-0.18),
            margin=dict(t=50, b=60),
        )
        st.plotly_chart(fig_acum, width="stretch")

    # 1.3  Distribuição por dia da semana (box‑plot)
    with col_b:
        ordem_dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        nomes_dias = {"Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua",
                      "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb"}
        dia_df = (
            df_f.groupby(["Data", "DiaSemana"], as_index=False)["Produzido"].sum()
        )
        dia_df["DiaSemana"] = pd.Categorical(
            dia_df["DiaSemana"], categories=ordem_dias, ordered=True,
        )
        dia_df = dia_df.dropna(subset=["DiaSemana"]).sort_values("DiaSemana")
        dia_df["Dia"] = dia_df["DiaSemana"].map(nomes_dias)

        fig_box = px.box(
            dia_df, x="Dia", y="Produzido", color="Dia",
            title="Distribuição da Produção por Dia da Semana",
            template="plotly_dark",
        )
        fig_box.update_layout(showlegend=False, margin=dict(t=50, b=40))
        st.plotly_chart(fig_box, width="stretch")

    # 1.4  Produção por mês (barras agrupadas, ano como cor se > 1 ano)
    mensal = (
        df_f.groupby(["Ano", "Mês"], as_index=False)["Produzido"].sum()
    )
    mensal["MêsNome"] = mensal["Mês"].map(MESES_NOME)
    mensal["Ano"] = mensal["Ano"].astype(str)

    fig_mes = px.bar(
        mensal, x="MêsNome", y="Produzido", color="Ano",
        barmode="group", text_auto=True,
        title="Produção Mensal",
        template="plotly_dark",
    )
    fig_mes.update_layout(
        xaxis_title="Mês", yaxis_title="Peças",
        margin=dict(t=50, b=40),
    )
    st.plotly_chart(fig_mes, width="stretch")

# ─── Tab 2 — Por Facção ────────────────────────────────────────────
with tab_facc:

    # 2.1  Tabela resumo por facção
    tbl = df_f.groupby("FACÇÃO", as_index=False).agg(
        Produzido=("Produzido", "sum"),
        Dias=("Data", "nunique"),
    )
    tbl["Meta Dia"] = tbl["FACÇÃO"].map(META_FACCAO).fillna(0)
    tbl["Meta Período"] = tbl["Meta Dia"] * tbl["Dias"].clip(lower=0)
    tbl["Ating. %"] = np.where(
        tbl["Meta Período"] > 0,
        tbl["Produzido"] / tbl["Meta Período"] * 100, 0,
    )
    tbl["Saldo"] = tbl["Produzido"] - tbl["Meta Período"]
    tbl["Média/Dia"] = np.where(tbl["Dias"] > 0, tbl["Produzido"] / tbl["Dias"], 0)
    tbl = tbl.sort_values("Ating. %", ascending=False)

    st.dataframe(
        tbl.style.format({
            "Produzido": "{:,.0f}",
            "Meta Período": "{:,.0f}",
            "Saldo": "{:,.0f}",
            "Ating. %": "{:.1f}%",
            "Média/Dia": "{:,.0f}",
        }).background_gradient(subset=["Ating. %"], cmap="RdYlGn", vmin=50, vmax=120),
        width="stretch", hide_index=True,
    )

    st.markdown("")
    col_f1, col_f2 = st.columns(2)

    # 2.2  Barras horizontais — atingimento por facção
    with col_f1:
        fig_ating = go.Figure()
        cores_at = [
            "#22c55e" if a >= 100 else "#f97316" if a >= 80 else "#ef4444"
            for a in tbl["Ating. %"]
        ]
        fig_ating.add_bar(
            y=tbl["FACÇÃO"], x=tbl["Ating. %"],
            orientation="h", marker_color=cores_at,
            text=[f"{a:.1f}%" for a in tbl["Ating. %"]],
            textposition="outside",
        )
        fig_ating.add_vline(x=100, line_dash="dash", line_color="#facc15")
        fig_ating.update_layout(
            title="Atingimento por Facção (%)",
            xaxis_title="% Meta", yaxis_title="",
            template="plotly_dark",
            margin=dict(t=50, l=100, r=40, b=40),
        )
        st.plotly_chart(fig_ating, width="stretch")

    # 2.3  Treemap — participação no volume total
    with col_f2:
        fig_tree = px.treemap(
            tbl, path=["FACÇÃO"], values="Produzido",
            color="Ating. %",
            color_continuous_scale="RdYlGn",
            range_color=[50, 120],
            title="Participação no Volume (cor = ating. %)",
            template="plotly_dark",
        )
        fig_tree.update_layout(margin=dict(t=50, b=10))
        st.plotly_chart(fig_tree, width="stretch")

    # 2.4  Linhas de produção diária, uma por facção
    prod_facc = (
        df_f.groupby(["Data", "FACÇÃO"], as_index=False)["Produzido"].sum()
        .sort_values("Data")
    )
    fig_linhas = px.line(
        prod_facc, x="Data", y="Produzido", color="FACÇÃO",
        title="Evolução Diária por Facção",
        template="plotly_dark",
    )
    fig_linhas.update_layout(
        legend=dict(orientation="h", y=-0.18),
        margin=dict(t=50, b=60),
    )
    st.plotly_chart(fig_linhas, width="stretch")

# ─── Tab 3 — Ranking & Alertas ─────────────────────────────────────
with tab_rank:
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("### 🏅 Top 5 Dias Mais Produtivos")
        top5 = (
            df_f.groupby("Data", as_index=False)["Produzido"]
            .sum()
            .nlargest(5, "Produzido")
        )
        top5["Data"] = top5["Data"].dt.strftime("%d/%m/%Y")
        for i, row in enumerate(top5.itertuples(), 1):
            medal = "🥇🥈🥉" [i - 1] if i <= 3 else f"  {i}."
            st.markdown(
                f"**{medal} {row.Data}** — {fmt_br(row.Produzido)} peças"
            )

    with col_r2:
        st.markdown("### ⚠️ Top 5 Dias Menos Produtivos")
        bot5 = (
            df_f.groupby("Data", as_index=False)["Produzido"]
            .sum()
            .nsmallest(5, "Produzido")
        )
        bot5["Data"] = bot5["Data"].dt.strftime("%d/%m/%Y")
        for i, row in enumerate(bot5.itertuples(), 1):
            st.markdown(
                f"**{i}. {row.Data}** — {fmt_br(row.Produzido)} peças"
            )

    st.markdown("---")

    # Facções abaixo de 80% de atingimento
    st.markdown("### 🚨 Facções com Atingimento Abaixo de 80%")
    alerta = tbl[tbl["Ating. %"] < 80][["FACÇÃO", "Produzido", "Meta Período", "Ating. %", "Saldo"]]
    if alerta.empty:
        st.success("Nenhuma facção abaixo de 80% no período selecionado!")
    else:
        st.dataframe(
            alerta.style.format({
                "Produzido": "{:,.0f}", "Meta Período": "{:,.0f}",
                "Ating. %": "{:.1f}%", "Saldo": "{:,.0f}",
            }).map(lambda _: "color: #ef4444", subset=["Ating. %"]),
            width="stretch", hide_index=True,
        )

    st.markdown("---")

    # Heatmap semanal — produção por semana × facção
    st.markdown("### 🗓️ Heatmap — Produção Semanal por Facção")
    heat = df_f.pivot_table(
        index="FACÇÃO", columns="Semana", values="Produzido", aggfunc="sum",
    ).fillna(0)
    fig_heat = px.imshow(
        heat, aspect="auto",
        color_continuous_scale="YlGn",
        title="",
        labels=dict(x="Semana", y="Facção", color="Peças"),
        template="plotly_dark",
    )
    fig_heat.update_layout(margin=dict(t=20, b=40))
    st.plotly_chart(fig_heat, width="stretch")

# ─── Tab 4 — Dados ─────────────────────────────────────────────────
with tab_dados:
    st.markdown("### 📋 Base Filtrada")
    st.dataframe(
        df_f[["Data", "FACÇÃO", "PRODUTO", "Produzido"]]
        .sort_values(["Data", "FACÇÃO"], ascending=[False, True])
        .reset_index(drop=True),
        width="stretch",
        height=500,
    )
    csv = df_f.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Baixar CSV filtrado", csv,
        file_name="producao_filtrada.csv",
        mime="text/csv",
    )