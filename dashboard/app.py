"""
Dashboard interactivo - Segmentación de lotes de café con K-Means
Autor: Vladimir Emanuel Alcala Feliz - IDGS 9-3

Ejecutar desde la raíz del repositorio:
    streamlit run dashboard/app.py
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data" / "processed" / "coffee_clusters.csv"
RES = RAIZ / "outputs" / "resultados.json"
LOGOS = RAIZ / "assets"

ORDEN = ["Café de especialidad", "Calidad media de altura",
         "Calidad media de baja altitud", "Calidad baja con defectos"]
PALETA = dict(zip(ORDEN, ["#2A9D8F", "#5B7DB1", "#E9A23B", "#C8553D"]))
CAFE = "#6F4E37"

st.set_page_config(page_title="BeanCraft Insights", page_icon="☕", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 3.2rem; max-width: 1350px;}
div[data-testid="stMetric"] {background:#f7f3ee; border-left:5px solid #6F4E37;
    padding:12px 16px; border-radius:6px;}
div[data-testid="stMetric"] label, div[data-testid="stMetric"] label p {color:#5a4636 !important;}
div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] div {color:#2b2118 !important;}
[data-testid="stImage"] img {background:#fff; border-radius:6px; padding:4px;}
.card {background:#fbf9f6; border:1px solid #e6ddd2; border-left:6px solid var(--c);
    padding:12px 16px; border-radius:6px; margin-bottom:10px; color:#2b2118;}
.card h4 {margin:0 0 4px 0; color:#2b2118;}
.card p {margin:0; font-size:0.93rem;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def cargar():
    df = pd.read_csv(DATA)
    with open(RES, encoding="utf-8") as f:
        res = json.load(f)
    return df, res


df, res = cargar()

# ------------------------------ Encabezado ------------------------------
c1, c2, c3 = st.columns([1, 4, 1])
with c1:
    if (LOGOS / "utslrc.png").exists():
        st.image(str(LOGOS / "utslrc.png"), width=170)
with c2:
    st.markdown("<h1 style='text-align:center;margin-bottom:0;font-size:2.1rem'>☕ BeanCraft Insights: "
                "segmentación de lotes de café con K-Means</h1>"
                "<p style='text-align:center;color:#6b5a4b;margin-top:2px;font-size:1rem'>"
                "Calidad sensorial, altitud y defectos · Datos del Coffee Quality Institute</p>", unsafe_allow_html=True)
with c3:
    if (LOGOS / "idgs.png").exists():
        st.image(str(LOGOS / "idgs.png"), width=130)

# ------------------------------ Filtros ---------------------------------
st.sidebar.header("Filtros")
paises = sorted(df["pais"].unique())
f_pais = st.sidebar.multiselect("País de origen", paises, placeholder="Todos los países")
procesos = sorted(df["proceso"].unique())
f_proc = st.sidebar.multiselect("Método de procesamiento", procesos,
                                placeholder="Todos los métodos")
a_min, a_max = int(df["altitud_m"].min()), int(df["altitud_m"].max())
f_alt = st.sidebar.slider("Altitud (m)", a_min, a_max, (a_min, a_max))
st.sidebar.caption("Los filtros se aplican a ambas páginas.")

dff = df.copy()
if f_pais:
    dff = dff[dff["pais"].isin(f_pais)]
if f_proc:
    dff = dff[dff["proceso"].isin(f_proc)]
dff = dff[dff["altitud_m"].between(*f_alt)]

st.sidebar.markdown("---")
st.sidebar.markdown("**Vladimir Emanuel Alcala Feliz**  \nIDGS 9-3  \nMtra. Julia Elizabeth Garcia Herrera")

pagina = st.sidebar.radio("Página", ["1. Análisis general", "2. Segmentación K-Means"])

if dff.empty:
    st.warning("No hay lotes con los filtros seleccionados. Amplía los filtros.")
    st.stop()


def layout(fig, h=360):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=45, b=10),
                      font=dict(size=12), legend_title_text="")
    return fig


# ======================================================================
# PÁGINA 1
# ======================================================================
if pagina.startswith("1"):
    st.subheader("Análisis general del dataset")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Lotes analizados", f"{len(dff):,}")
    k2.metric("Puntaje total promedio", f"{dff['total_cup_points'].mean():.2f}")
    k3.metric("Altitud promedio", f"{dff['altitud_m'].mean():,.0f} m")
    k4.metric("Lotes ≥ 85 pts (especialidad SCA)",
              f"{(dff['total_cup_points'] >= 85).mean() * 100:.1f} %")

    a, b = st.columns(2)
    with a:
        fig = px.histogram(dff, x="total_cup_points", nbins=30, color_discrete_sequence=[CAFE],
                           title="Distribución del puntaje total",
                           labels={"total_cup_points": "Puntaje total"})
        st.plotly_chart(layout(fig), width="stretch")
    with b:
        top = dff["pais"].value_counts().head(10).reset_index()
        top.columns = ["pais", "lotes"]
        fig = px.bar(top.sort_values("lotes"), x="lotes", y="pais", orientation="h",
                     title="Top 10 países por número de lotes",
                     color_discrete_sequence=["#2A9D8F"])
        fig.update_yaxes(title="")
        st.plotly_chart(layout(fig), width="stretch")

    a, b = st.columns(2)
    with a:
        fig = px.scatter(dff, x="altitud_m", y="total_cup_points", opacity=.5,
                         color_discrete_sequence=[CAFE], trendline="ols",
                         title="Altitud vs. puntaje total",
                         labels={"altitud_m": "Altitud (m)", "total_cup_points": "Puntaje total"})
        st.plotly_chart(layout(fig), width="stretch")
    with b:
        pr = dff.groupby("proceso")["total_cup_points"].agg(["mean", "size"]).reset_index()
        pr = pr[pr["size"] >= 5].sort_values("mean")
        fig = px.bar(pr, x="mean", y="proceso", orientation="h",
                     title="Puntaje promedio por método de procesamiento",
                     color_discrete_sequence=["#E9A23B"], labels={"mean": "Puntaje promedio"})
        fig.update_xaxes(range=[pr["mean"].min() - 1, pr["mean"].max() + 0.5])
        fig.update_yaxes(title="")
        st.plotly_chart(layout(fig), width="stretch")

    st.markdown("##### Estadísticas descriptivas de los lotes filtrados")
    cols = {"total_cup_points": "Puntaje total", "flavor": "Sabor", "acidity": "Acidez",
            "body": "Cuerpo", "balance": "Balance", "altitud_m": "Altitud (m)",
            "defectos": "Defectos"}
    st.dataframe(dff[list(cols)].rename(columns=cols).describe().T.round(2),
                 width="stretch")

# ======================================================================
# PÁGINA 2
# ======================================================================
else:
    st.subheader("Segmentación mediante K-Means (K = 4)")
    f_cl = st.multiselect("Filtrar clústeres", ORDEN, default=ORDEN)
    d = dff[dff["cluster"].isin(f_cl)]
    if d.empty:
        st.warning("Selecciona al menos un clúster con datos.")
        st.stop()

    esp = d[d["cluster"] == "Café de especialidad"]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Lotes segmentados", f"{len(d):,}")
    k2.metric("Clústeres (K)", f"{d['cluster'].nunique()} de {res['k_final']}")
    k3.metric("% café de especialidad", f"{len(esp) / len(d) * 100:.1f} %")
    k4.metric("Silueta del modelo", f"{res['silueta_final']:.3f}",
              help="Calculada sobre todo el dataset (no cambia con los filtros).")

    a, b = st.columns(2)
    with a:
        cnt = d["cluster"].value_counts().reindex(ORDEN).dropna().reset_index()
        cnt.columns = ["cluster", "lotes"]
        fig = px.bar(cnt, x="cluster", y="lotes", color="cluster", color_discrete_map=PALETA,
                     text="lotes", title="Distribución de lotes por clúster")
        fig.update_layout(showlegend=False)
        fig.update_xaxes(title="")
        st.plotly_chart(layout(fig), width="stretch")
    with b:
        fig = px.scatter(d, x="pca1", y="pca2", color="cluster", color_discrete_map=PALETA,
                         category_orders={"cluster": ORDEN}, opacity=.75,
                         hover_data=["pais", "proceso", "total_cup_points", "altitud_m"],
                         title="Agrupamientos (proyección PCA)",
                         labels={"pca1": f"PC1 ({res['pca_var'][0] * 100:.1f} %)",
                                 "pca2": f"PC2 ({res['pca_var'][1] * 100:.1f} %)"})
        st.plotly_chart(layout(fig), width="stretch")

    a, b = st.columns(2)
    with a:
        fig = px.box(d, x="cluster", y="total_cup_points", color="cluster",
                     color_discrete_map=PALETA, category_orders={"cluster": ORDEN},
                     title="Puntaje total por clúster",
                     labels={"total_cup_points": "Puntaje total"})
        fig.update_layout(showlegend=False)
        fig.update_xaxes(title="")
        st.plotly_chart(layout(fig), width="stretch")
    with b:
        prom = d.groupby("cluster")[["flavor", "acidity", "body", "balance"]].mean() \
            .reindex([c for c in ORDEN if c in d["cluster"].unique()])
        cat = ["Sabor", "Acidez", "Cuerpo", "Balance"]
        fig = go.Figure()
        for c in prom.index:
            fig.add_trace(go.Scatterpolar(r=prom.loc[c].tolist() + [prom.loc[c].iloc[0]],
                                          theta=cat + [cat[0]], name=c,
                                          line_color=PALETA[c]))
        fig.update_layout(title="Perfil sensorial promedio",
                          polar=dict(radialaxis=dict(range=[6.9, 8.1])))
        st.plotly_chart(layout(fig), width="stretch")

    st.markdown("##### Estadísticas descriptivas por clúster (promedio)")
    t = d.groupby("cluster").agg(
        Lotes=("flavor", "size"), Puntaje=("total_cup_points", "mean"),
        Sabor=("flavor", "mean"), Acidez=("acidity", "mean"), Cuerpo=("body", "mean"),
        Balance=("balance", "mean"), Altitud_m=("altitud_m", "mean"),
        Defectos=("defectos", "mean"), Desv_puntaje=("total_cup_points", "std"),
    ).reindex([c for c in ORDEN if c in d["cluster"].unique()]).round(2)
    t = t.rename(columns={"Defectos": "Defectos (promedio)"})
    st.dataframe(t, width="stretch")

    st.markdown("##### Descripción de los grupos identificados")
    desc = {
        "Café de especialidad": "Los mejores perfiles sensoriales (sabor, acidez, cuerpo y balance ≈ 7.9), "
                                "altitud alta (~1,510 m) y 2.4 defectos por lote en promedio. Los países con más lotes en este grupo son Colombia, Guatemala y Etiopía.",
        "Calidad media de altura": "Perfil sensorial promedio (~7.55) con altitud alta (~1,520 m) pero más "
                                   "defectos (4.2 por lote) que los grupos de mayor calidad. Es el grupo más grande.",
        "Calidad media de baja altitud": "Mismo nivel sensorial que el grupo anterior pero cultivado a baja altitud "
                                         "(~830 m), con 2.0 defectos por lote y mayor presencia de proceso natural.",
        "Calidad baja con defectos": "Puntajes sensoriales más bajos (~7.1) y el mayor número de defectos "
                                     "(7.4 por lote). El 35 % de sus lotes son de México.",
    }
    cc = st.columns(2)
    for i, n in enumerate(ORDEN):
        cc[i % 2].markdown(f"<div class='card' style='--c:{PALETA[n]}'><h4>{n}</h4>"
                           f"<p>{desc[n]}</p></div>", unsafe_allow_html=True)

    st.markdown("##### Principales hallazgos y recomendaciones")
    h, r = st.columns(2)
    with h:
        st.markdown("""
**Hallazgos**
1. Solo ~19 % de los lotes es *café de especialidad* y se distingue por sus puntajes sensoriales, no por la altitud.
2. La altitud ayuda pero no determina la calidad: el grupo de baja altitud con pocos defectos iguala en sabor al de altura.
3. Los defectos separan al grupo de calidad baja: 7.4 por lote contra 2.4 en especialidad y 2.0 en baja altitud.
4. El 43.6 % de los lotes de México cae en *calidad baja con defectos* (vs. 21.8 % global).
5. La estructura es débil (silueta ≈ 0.18): los grupos se traslapan.
""")
    with r:
        st.markdown("""
**Recomendaciones**
1. Reducir defectos en origen (selección, secado y clasificación) para subir lotes del grupo de calidad baja.
2. Valorar lotes de baja altitud con pocos defectos como alternativa de calidad media estable.
3. Enfocar la compra de especialidad en orígenes con mayor proporción de lotes de especialidad (Etiopía ≈ 77 %, Kenia ≈ 68 %, Uganda ≈ 42 %).
4. Dar seguimiento a los lotes mexicanos con capacitación en postcosecha y control de defectos.
""")
    st.caption("Los grupos se calcularon en Python (scikit-learn, K-Means con StandardScaler) y se "
               "leen de data/processed/coffee_clusters.csv.")
