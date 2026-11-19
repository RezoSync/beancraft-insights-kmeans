"""
Segmentación de lotes de café con K-Means
Proyecto integrador - Unidad 3 (Minería de datos)
Autor: Vladimir Emanuel Alcala Feliz - IDGS 9-3

Ejecutar desde la raíz del repositorio:
    python src/analisis_kmeans.py

Genera:
    data/processed/coffee_clusters.csv   (dataset procesado con clúster)
    outputs/resultados.json              (métricas, centroides, conteos)
    outputs/*.csv                        (tablas de apoyo)
    docs/figuras/*.png                   (gráficas del análisis)
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score,
                             davies_bouldin_score, silhouette_score)
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw" / "coffee_ratings.csv"
PROC = RAIZ / "data" / "processed" / "coffee_clusters.csv"
OUT = RAIZ / "outputs"
FIG = RAIZ / "docs" / "figuras"
for p in (PROC.parent, OUT, FIG):
    p.mkdir(parents=True, exist_ok=True)

SEMILLA = 42
sns.set_theme(style="whitegrid", font_scale=1.0)
COLORES = ["#6F4E37", "#2A9D8F", "#E9A23B", "#C8553D", "#5B7DB1", "#8E6C8A"]
log = {}  # bitácora de limpieza y resultados


def titulo(txt):
    print("\n" + "=" * 70 + f"\n{txt}\n" + "=" * 70)


# ---------------------------------------------------------------------
# PARTE 2. OBTENCIÓN Y EXPLORACIÓN
# ---------------------------------------------------------------------
titulo("PARTE 2. EXPLORACIÓN DEL DATASET")
df_raw = pd.read_csv(RAW)  # read_csv()
print("Primeros 10 registros:")
print(df_raw.head(10).iloc[:, :12].to_string())
print(f"\nDimensiones: {df_raw.shape}")
print("\nTipos de datos:")
print(df_raw.dtypes.value_counts())
print("\nEstadísticas descriptivas (variables numéricas):")
print(df_raw.describe().T.round(2).to_string())

nulos = df_raw.isna().sum()
nulos = nulos[nulos > 0].sort_values(ascending=False)
print("\nValores nulos por columna:\n", nulos)
dup_exacto = int(df_raw.duplicated().sum())
cols_dup = ["country_of_origin", "farm_name", "total_cup_points", "aroma", "flavor",
            "acidity", "body", "balance"]
dup_logico = int(df_raw.duplicated(subset=cols_dup).sum())
print(f"\nDuplicados exactos: {dup_exacto} | duplicados por clave sensorial+origen: {dup_logico}")

log["raw"] = {
    "registros": int(df_raw.shape[0]),
    "columnas": int(df_raw.shape[1]),
    "nulos_altitud": int(df_raw["altitude_mean_meters"].isna().sum()),
    "nulos_variedad": int(df_raw["variety"].isna().sum()),
    "nulos_proceso": int(df_raw["processing_method"].isna().sum()),
    "duplicados_exactos": dup_exacto,
    "duplicados_logicos": dup_logico,
    "columnas_con_nulos": int((df_raw.isna().sum() > 0).sum()),
}

# Gráficas exploratorias (antes de limpiar)
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
sns.histplot(df_raw["total_cup_points"], bins=35, color=COLORES[0], ax=ax[0])
ax[0].set_title("Distribución de la puntuación total (SCA)")
ax[0].set_xlabel("total_cup_points")
top = df_raw["country_of_origin"].value_counts().head(10)
sns.barplot(x=top.values, y=top.index, color=COLORES[1], ax=ax[1])
ax[1].set_title("Top 10 países por número de lotes")
ax[1].set_xlabel("Lotes")
ax[1].set_ylabel("")
sns.boxplot(x=df_raw["altitude_mean_meters"].clip(upper=5000), color=COLORES[2], ax=ax[2])
ax[2].set_title("Altitud (m) con valores atípicos\n(eje recortado en 5,000 m)")
ax[2].set_xlabel("altitude_mean_meters")
plt.tight_layout()
plt.savefig(FIG / "01_exploratorias.png", dpi=170)
plt.close()

sens = ["aroma", "flavor", "aftertaste", "acidity", "body", "balance",
        "altitude_mean_meters", "moisture", "category_two_defects"]
plt.figure(figsize=(7.5, 6))
sns.heatmap(df_raw[sens].corr(), annot=True, fmt=".2f", cmap="BrBG", center=0,
            cbar_kws={"shrink": .8})
plt.title("Correlación entre variables candidatas")
plt.tight_layout()
plt.savefig(FIG / "02_correlacion.png", dpi=170)
plt.close()

# ---------------------------------------------------------------------
# PARTE 3. LIMPIEZA Y PREPARACIÓN
# ---------------------------------------------------------------------
titulo("PARTE 3. LIMPIEZA Y PREPARACIÓN")
df = df_raw.copy()
n0 = len(df)

# 3.1 Registro inconsistente: lote con todas las puntuaciones en 0
cero = df["total_cup_points"] == 0
df = df.loc[~cero].copy()
log["registros_puntaje_cero_eliminados"] = int(cero.sum())

# 3.2 Duplicados
antes = len(df)
df = df.drop_duplicates()
df = df.drop_duplicates(subset=cols_dup)
log["duplicados_eliminados"] = int(antes - len(df))

# 3.3 Nombres de país con formato inconsistente y país nulo
df["country_of_origin"] = (df["country_of_origin"]
                           .replace({"Tanzania, United Republic Of": "Tanzania",
                                     "United States (Hawaii)": "Hawaii (EE.UU.)",
                                     "United States": "EE.UU.",
                                     "Cote d?Ivoire": "Costa de Marfil"})
                           .fillna("Desconocido"))

# 3.4 Altitud: valores imposibles (<100 m o >3,000 m) => nulos y luego imputación
alt = df["altitude_mean_meters"].copy()
invalidas = ((alt < 100) | (alt > 3000)) & alt.notna()
log["altitud_invalida"] = int(invalidas.sum())
alt[invalidas] = np.nan
log["altitud_nulos_total"] = int(alt.isna().sum())
alt = alt.fillna(alt.groupby(df["country_of_origin"]).transform("median"))
alt = alt.fillna(alt.median())  # países sin ningún dato
df["altitud_m"] = alt

# 3.5 Humedad = 0 % no es físicamente posible en café verde => dato faltante
cero_h = df["moisture"] == 0
log["humedad_cero_imputada"] = int(cero_h.sum())
df["humedad"] = df["moisture"].where(~cero_h)
df["humedad"] = df["humedad"].fillna(df["humedad"].median())

# 3.6 Nulos en variables categóricas -> "Desconocido"
for c in ["variety", "processing_method"]:
    log[f"nulos_{c}"] = int(df[c].isna().sum())
    df[c] = df[c].fillna("Desconocido")
df["processing_method"] = df["processing_method"].replace(
    {"Washed / Wet": "Lavado", "Natural / Dry": "Natural",
     "Semi-washed / Semi-pulped": "Semilavado", "Pulped natural / honey": "Honey",
     "Other": "Otro"})

# 3.7 Tipos de datos (harvest_year es texto con formatos "2014/2015", etc.)
df["anio_cosecha"] = pd.to_numeric(df["harvest_year"].astype(str).str[:4], errors="coerce")

# 3.8 Variable derivada: defectos totales
df["defectos"] = df["category_one_defects"] + df["category_two_defects"]

# 3.9 Valores atípicos (IQR) - justificación en la documentación
def iqr_out(s):
    q1, q3 = s.quantile([.25, .75])
    i = q3 - q1
    return int(((s < q1 - 1.5 * i) | (s > q3 + 1.5 * i)).sum())

vars_k = ["flavor", "acidity", "body", "balance", "altitud_m", "humedad", "defectos"]
atip = {v: iqr_out(df[v]) for v in vars_k}
log["atipicos_iqr"] = atip
print("Atípicos por IQR:", atip)

# Tratamiento: defectos tienen cola larga (hasta 63) -> log1p ; sensoriales se conservan
# (son puntuaciones reales, los lotes de baja calidad son justamente de interés)
df["log_defectos"] = np.log1p(df["defectos"])

# Gráfica antes/después del tratamiento de atípicos y altitud
fig, ax = plt.subplots(1, 3, figsize=(15, 4))
sns.boxplot(x=df_raw["altitude_mean_meters"].clip(upper=5000), color="#bbb", ax=ax[0])
ax[0].set_title("Altitud ANTES (recortada a 5,000 m)")
sns.boxplot(x=df["altitud_m"], color=COLORES[2], ax=ax[1])
ax[1].set_title("Altitud DESPUÉS de limpieza")
sns.histplot(df["defectos"], bins=30, color="#bbb", label="defectos", ax=ax[2])
sns.histplot(df["log_defectos"] * 10, bins=30, color=COLORES[3], alpha=.6,
             label="log(1+defectos) × 10", ax=ax[2])
ax[2].legend()
ax[2].set_title("Defectos: transformación logarítmica")
plt.tight_layout()
plt.savefig(FIG / "03_limpieza_atipicos.png", dpi=170)
plt.close()

# 3.10 Codificación (para el análisis posterior de los grupos; no entra al modelo)
df["es_mexico"] = (df["country_of_origin"] == "Mexico").astype(int)
df["especie_cod"] = df["species"].map({"Arabica": 0, "Robusta": 1})

# 3.11 Escalamiento
# "humedad" se excluye del modelo: 264 lotes reportan 0 % (dato faltante imputado), por lo que
# aportaría ruido; se conserva solo para describir los grupos.
vars_modelo = ["flavor", "acidity", "body", "balance", "altitud_m", "log_defectos"]
X = df[vars_modelo]
scaler = StandardScaler()
X_esc = scaler.fit_transform(X)

log["limpieza"] = {
    "registros_antes": int(n0),
    "registros_despues": int(len(df)),
    "nulos_restantes_vars_modelo": int(X.isna().sum().sum()),
    "variables_modelo": vars_modelo,
    "media_post_escala": [round(float(v), 6) for v in X_esc.mean(axis=0)],
    "desv_post_escala": [round(float(v), 6) for v in X_esc.std(axis=0)],
}
print(json.dumps(log["limpieza"], indent=2, ensure_ascii=False))
print(f"Registros finales: {len(df)}  | nulos en variables del modelo: {X.isna().sum().sum()}")

# ---------------------------------------------------------------------
# PARTE 4. K-MEANS
# ---------------------------------------------------------------------
titulo("PARTE 4. IMPLEMENTACIÓN DE K-MEANS")
filas = []
for k in range(2, 9):  # 7 valores de K
    m = KMeans(n_clusters=k, n_init=10, random_state=SEMILLA).fit(X_esc)
    filas.append({"K": k, "inercia": m.inertia_,
                  "silueta": silhouette_score(X_esc, m.labels_),
                  "davies_bouldin": davies_bouldin_score(X_esc, m.labels_),
                  "calinski_harabasz": calinski_harabasz_score(X_esc, m.labels_)})
met = pd.DataFrame(filas)
print(met.round(3).to_string(index=False))
met.to_csv(OUT / "metricas_por_k.csv", index=False)

fig, ax = plt.subplots(1, 3, figsize=(15, 4))
ax[0].plot(met.K, met.inercia, "o-", color=COLORES[0])
ax[0].set_title("Método del codo (inercia)")
ax[1].plot(met.K, met.silueta, "o-", color=COLORES[1])
ax[1].set_title("Coeficiente de silueta (↑ mejor)")
ax[2].plot(met.K, met.davies_bouldin, "o-", color=COLORES[3])
ax[2].set_title("Índice Davies-Bouldin (↓ mejor)")
for a in ax:
    a.set_xlabel("Número de clústeres K")
    a.set_xticks(met.K)
plt.tight_layout()
plt.savefig(FIG / "04_seleccion_k.png", dpi=170)
plt.close()


# Selección de K: K=2 solo separa "buen/mal café" (silueta máxima pero poco informativa).
# K=4 conserva una silueta similar a K=3, reduce la inercia y entrega perfiles interpretables.
K_FINAL = 4
K_ALT = 3

# ---- Configuración A (final): K=4 ----
km = KMeans(n_clusters=K_FINAL, n_init=10, random_state=SEMILLA)
df["cluster_id"] = km.fit_predict(X_esc)  # fit_predict()
# ---- Configuración B (comparación): K=3 ----
km3 = KMeans(n_clusters=K_ALT, n_init=10, random_state=SEMILLA)
lab3 = km3.fit_predict(X_esc)

comp = pd.DataFrame({
    "Configuración": [f"A: K={K_FINAL} (final)", f"B: K={K_ALT}"],
    "Inercia": [km.inertia_, km3.inertia_],
    "Silueta": [silhouette_score(X_esc, km.labels_), silhouette_score(X_esc, lab3)],
    "Davies-Bouldin": [davies_bouldin_score(X_esc, km.labels_), davies_bouldin_score(X_esc, lab3)],
    "Calinski-Harabasz": [calinski_harabasz_score(X_esc, km.labels_), calinski_harabasz_score(X_esc, lab3)],
    "Iteraciones": [km.n_iter_, km3.n_iter_],
})
ari = adjusted_rand_score(df["cluster_id"], lab3)
print(comp.round(3).to_string(index=False))
print(f"Índice Rand ajustado entre A y B: {ari:.3f}")
comp.to_csv(OUT / "comparacion_configuraciones.csv", index=False)

# ---- Centroides en escala original ----
cent = pd.DataFrame(scaler.inverse_transform(km.cluster_centers_), columns=vars_modelo)
cent["defectos"] = np.expm1(cent["log_defectos"])
cent = cent.drop(columns="log_defectos")
cent.index.name = "cluster_id"
print("\nCentroides (escala original):\n", cent.round(2))
print("\nRegistros por clúster:\n", df["cluster_id"].value_counts().sort_index())

# ---- Nombres descriptivos (según el perfil de cada centroide) ----
resumen = df.groupby("cluster_id").agg(
    flavor=("flavor", "mean"), alt=("altitud_m", "mean"), defectos=("defectos", "mean"))
orden_calidad = resumen["flavor"].sort_values()
id_bajo = orden_calidad.index[0]
id_alto = orden_calidad.index[-1]
medios = [i for i in resumen.index if i not in (id_bajo, id_alto)]
id_med_alta = max(medios, key=lambda i: resumen.loc[i, "alt"])
id_med_baja = [i for i in medios if i != id_med_alta][0]
NOMBRES = {
    id_alto: "Café de especialidad",
    id_med_alta: "Calidad media de altura",
    id_med_baja: "Calidad media de baja altitud",
    id_bajo: "Calidad baja con defectos",
}
df["cluster"] = df["cluster_id"].map(NOMBRES)
cent["Nombre"] = cent.index.map(NOMBRES)
orden_nombres = ["Café de especialidad", "Calidad media de altura",
                 "Calidad media de baja altitud", "Calidad baja con defectos"]
PALETA = dict(zip(orden_nombres, ["#2A9D8F", "#5B7DB1", "#E9A23B", "#C8553D"]))
cent.to_csv(OUT / "centroides.csv")

# ---- PCA solo para visualizar ----
pca = PCA(n_components=2, random_state=SEMILLA)
pc = pca.fit_transform(X_esc)
df["pca1"], df["pca2"] = pc[:, 0], pc[:, 1]
var_exp = pca.explained_variance_ratio_

fig, ax = plt.subplots(1, 2, figsize=(14, 5.5))
sns.scatterplot(data=df, x="pca1", y="pca2", hue="cluster", hue_order=orden_nombres,
                palette=PALETA, s=22, alpha=.75, ax=ax[0])
cp = pca.transform(km.cluster_centers_)
for i, (x, y) in enumerate(cp):
    ax[0].scatter(x, y, marker="X", s=260, c="black", edgecolor="white", linewidth=1.5, zorder=5)
ax[0].set_title(f"Clústeres en 2 componentes principales\n(varianza explicada: {var_exp.sum()*100:.1f} %)")
ax[0].set_xlabel(f"PC1 ({var_exp[0]*100:.1f} %)")
ax[0].set_ylabel(f"PC2 ({var_exp[1]*100:.1f} %)")
ax[0].legend(title="", fontsize=8)
sns.scatterplot(data=df, x="altitud_m", y="flavor", hue="cluster", hue_order=orden_nombres,
                palette=PALETA, s=22, alpha=.75, ax=ax[1], legend=False)
ax[1].set_title("Sabor (flavor) vs. altitud")
ax[1].set_xlabel("Altitud (m)")
plt.tight_layout()
plt.savefig(FIG / "05_clusters_scatter.png", dpi=170)
plt.close()

# ---------------------------------------------------------------------
# PARTE 5. ANÁLISIS POR CLÚSTER
# ---------------------------------------------------------------------
titulo("PARTE 5. ANÁLISIS DE RESULTADOS")
vars_desc = ["total_cup_points", "flavor", "acidity", "body", "balance", "aroma",
             "altitud_m", "defectos", "humedad"]
estad = df.groupby("cluster")[vars_desc].agg(["mean", "median", "std", "min", "max"]).round(2)
estad = estad.loc[orden_nombres]
estad.to_csv(OUT / "estadisticas_por_cluster.csv")

tabla = df.groupby("cluster").agg(
    Lotes=("flavor", "size"),
    Puntaje_total=("total_cup_points", "mean"),
    Sabor=("flavor", "mean"), Acidez=("acidity", "mean"),
    Cuerpo=("body", "mean"), Balance=("balance", "mean"),
    Altitud_m=("altitud_m", "mean"), Defectos=("defectos", "mean"),
    Pct_Mexico=("es_mexico", lambda s: s.mean() * 100),
    Pct_Natural=("processing_method", lambda s: (s == "Natural").mean() * 100),
    Pct_Lavado=("processing_method", lambda s: (s == "Lavado").mean() * 100),
).loc[orden_nombres]
tabla["Pct_Lotes"] = tabla["Lotes"] / tabla["Lotes"].sum() * 100
tabla.round(2).to_csv(OUT / "tabla_comparativa.csv")
print(tabla.round(2).to_string())

# Gráficas de comparación
fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
sns.countplot(data=df, y="cluster", order=orden_nombres, palette=PALETA, hue="cluster",
              legend=False, ax=ax[0])
ax[0].set_title("Lotes por clúster"); ax[0].set_ylabel(""); ax[0].set_xlabel("Lotes")
for c in ax[0].containers:
    ax[0].bar_label(c, padding=3)
sns.boxplot(data=df, x="cluster", y="total_cup_points", order=orden_nombres,
            palette=PALETA, hue="cluster", legend=False, ax=ax[1])
ax[1].set_title("Puntaje total por clúster"); ax[1].set_xlabel("")
ax[1].tick_params(axis="x", rotation=25)
sns.boxplot(data=df, x="cluster", y="altitud_m", order=orden_nombres,
            palette=PALETA, hue="cluster", legend=False, ax=ax[2])
ax[2].set_title("Altitud por clúster"); ax[2].set_xlabel("")
ax[2].tick_params(axis="x", rotation=25)
plt.tight_layout()
plt.savefig(FIG / "06_comparacion_clusters.png", dpi=170)
plt.close()

z = pd.DataFrame(km.cluster_centers_, columns=vars_modelo)
z.index = z.index.map(NOMBRES)
z = z.loc[orden_nombres]
z.columns = ["Sabor", "Acidez", "Cuerpo", "Balance", "Altitud", "Defectos (log)"]
plt.figure(figsize=(8, 3.8))
sns.heatmap(z, annot=True, fmt=".2f", cmap="BrBG", center=0, cbar_kws={"label": "Centroide (z-score)"})
plt.title("Centroides estandarizados por clúster")
plt.ylabel("")
plt.tight_layout()
plt.savefig(FIG / "07_centroides_heatmap.png", dpi=170)
plt.close()

# Hallazgos numéricos
mx_por_c = df.groupby("cluster")["es_mexico"].mean().mul(100).round(1).to_dict()
mex = df[df.es_mexico == 1]
mex_dist = mex["cluster"].value_counts(normalize=True).mul(100).round(1).to_dict()
glob_dist = df["cluster"].value_counts(normalize=True).mul(100).round(1).to_dict()
proc = pd.crosstab(df["processing_method"], df["cluster"], normalize="index").mul(100).round(1)
proc.to_csv(OUT / "proceso_vs_cluster.csv")
top_paises = (df[df.cluster == "Café de especialidad"]["country_of_origin"]
              .value_counts().head(5).to_dict())
pais_pct = (df.groupby("country_of_origin")
            .agg(n=("cluster", "size"),
                 pct_esp=("cluster", lambda s: (s == "Café de especialidad").mean() * 100))
            .query("n >= 20").sort_values("pct_esp", ascending=False).round(1))
pais_pct.to_csv(OUT / "paises_pct_especialidad.csv")
corr_alt = float(df[["altitud_m", "total_cup_points"]].corr().iloc[0, 1])

resultados = {
    "proyecto": "Segmentación de lotes de café mediante K-Means",
    "k_final": K_FINAL,
    "variables_modelo": vars_modelo,
    "metricas_por_k": met.round(4).to_dict(orient="records"),
    "comparacion": comp.round(4).to_dict(orient="records"),
    "ari_k4_k3": round(float(ari), 4),
    "silueta_final": round(float(silhouette_score(X_esc, km.labels_)), 4),
    "davies_bouldin_final": round(float(davies_bouldin_score(X_esc, km.labels_)), 4),
    "calinski_final": round(float(calinski_harabasz_score(X_esc, km.labels_)), 2),
    "inercia_final": round(float(km.inertia_), 2),
    "iteraciones_final": int(km.n_iter_),
    "centroides": cent.round(3).reset_index().to_dict(orient="records"),
    "conteo": df["cluster"].value_counts().to_dict(),
    "pca_var": [round(float(v), 4) for v in var_exp],
    "limpieza": log,
    "hallazgos": {
        "mexico_total": int(len(mex)),
        "mexico_dist": mex_dist,
        "global_dist": glob_dist,
        "pct_mexico_por_cluster": mx_por_c,
        "top_paises_especialidad": top_paises,
        "corr_altitud_puntaje": round(corr_alt, 3),
        "pct_especialidad_por_pais": pais_pct["pct_esp"].head(5).to_dict(),
    },
}
with open(OUT / "resultados.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------
# DATASET PROCESADO
# ---------------------------------------------------------------------
cols_out = ["cluster_id", "cluster", "country_of_origin", "species", "variety",
            "processing_method", "anio_cosecha", "total_cup_points", "aroma", "flavor",
            "aftertaste", "acidity", "body", "balance", "uniformity", "clean_cup",
            "sweetness", "cupper_points", "altitud_m", "humedad", "category_one_defects",
            "category_two_defects", "defectos", "log_defectos", "number_of_bags",
            "es_mexico", "especie_cod", "pca1", "pca2"]
df[cols_out].rename(columns={"country_of_origin": "pais", "species": "especie",
                             "variety": "variedad", "processing_method": "proceso"}
                    ).to_csv(PROC, index=False, encoding="utf-8")
print(f"\nDataset procesado guardado en {PROC.relative_to(RAIZ)}  ({len(df)} filas)")
print("Hallazgos:", json.dumps(resultados["hallazgos"], ensure_ascii=False, indent=1))
print(proc)
