"""Genera docs/Documentacion_Proyecto.pdf a partir de outputs/ y docs/figuras/.
Ejecutar después de analisis_kmeans.py:  python src/generar_pdf.py
"""
import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)
from PIL import Image as PILImage

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
try:
    from reportlab.pdfbase.pdfmetrics import registerFontAlias
except ImportError:
    from copy import copy

    def registerFontAlias(alias, font_name):
        font = copy(pdfmetrics.getFont(font_name))
        font.fontName = alias
        pdfmetrics.registerFont(font)

FONT_NAMES = ("Arial", "Arial-Bold", "Arial-Italic", "Arial-BoldItalic")
FONT_SETS = [
    [Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
     Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
     Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf"),
     Path("/usr/share/fonts/truetype/liberation2/LiberationSans-BoldItalic.ttf")],
    [Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
     Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
     Path("/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"),
     Path("/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf")],
    [Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf"),
     Path("C:/Windows/Fonts/ariali.ttf"), Path("C:/Windows/Fonts/arialbi.ttf")],
]
for font_dir in (Path("/Library/Fonts"), Path("/System/Library/Fonts/Supplemental")):
    FONT_SETS.append([font_dir / "Arial.ttf", font_dir / "Arial Bold.ttf",
                      font_dir / "Arial Italic.ttf", font_dir / "Arial Bold Italic.ttf"])

font_files = next((files for files in FONT_SETS if all(path.is_file() for path in files)), None)
if font_files:
    for name, path in zip(FONT_NAMES, font_files):
        pdfmetrics.registerFont(TTFont(name, str(path)))
else:
    for alias, font_name in zip(FONT_NAMES, ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique")):
        registerFontAlias(alias, font_name)
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold",
                              italic="Arial-Italic", boldItalic="Arial-BoldItalic")

RAIZ = Path(__file__).resolve().parent.parent
FIG, CAP, OUT, ASS = (RAIZ / "docs" / "figuras", RAIZ / "docs" / "capturas",
                      RAIZ / "outputs", RAIZ / "assets")
res = json.load(open(OUT / "resultados.json", encoding="utf-8"))
lim = res["limpieza"]
tabla = pd.read_csv(OUT / "tabla_comparativa.csv")
cent = pd.read_csv(OUT / "centroides.csv")
metk = pd.read_csv(OUT / "metricas_por_k.csv")
estad = pd.read_csv(OUT / "estadisticas_por_cluster.csv", header=[0, 1], index_col=0)
estad = estad.drop(index="cluster", errors="ignore")
comp = pd.DataFrame(res["comparacion"])

CAFE = colors.HexColor("#6F4E37")
CLARO = colors.HexColor("#F4EEE7")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Arial-Bold", fontSize=16, leading=24,
                    textColor=CAFE, spaceBefore=4, spaceAfter=8, keepWithNext=1, alignment=TA_JUSTIFY)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Arial-Bold", fontSize=12, leading=18,
                    textColor=CAFE, spaceBefore=8, spaceAfter=4, keepWithNext=1, alignment=TA_JUSTIFY)
P = ParagraphStyle("P", parent=ss["BodyText"], fontName="Arial", fontSize=12, leading=18,
                   alignment=TA_JUSTIFY, spaceAfter=6)
B = ParagraphStyle("B", parent=P, leftIndent=16, bulletIndent=2, spaceAfter=3)
CAPT = ParagraphStyle("CAPT", parent=P, fontSize=12, leading=18, textColor=colors.HexColor("#555555"),
                      alignment=TA_JUSTIFY, spaceAfter=10)
C = ParagraphStyle("C", parent=P, alignment=TA_CENTER)
TC = ParagraphStyle("TC", parent=P, fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=0)
TH = ParagraphStyle("TH", parent=TC, textColor=colors.white, fontName="Arial-Bold")


def p(t): return Paragraph(t, P)
def bl(items): return [Paragraph(i, B, bulletText="•") for i in items]


def img(path, w):
    iw, ih = PILImage.open(path).size
    return Image(str(path), width=w, height=w * ih / iw)


def img_fit(path, max_w=18 * cm, max_h=21 * cm):
    iw, ih = PILImage.open(path).size
    w = min(max_w, max_h * iw / ih)
    return Image(str(path), width=w, height=w * ih / iw)


def fig(name, w, caption):
    return KeepTogether([img(FIG / name, w), Paragraph(caption, CAPT)])


def tbl(data, widths, hdr=True):
    rows = [[Paragraph(str(c), TH if (hdr and i == 0) else TC) for c in r] for i, r in enumerate(data)]
    k = 18 * cm / sum(widths)
    t = Table(rows, colWidths=[w * k for w in widths], repeatRows=1)
    st = [("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#CFC3B6")),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if hdr:
        st += [("BACKGROUND", (0, 0), (-1, 0), CAFE)]
        st += [("BACKGROUND", (0, i), (-1, i), CLARO) for i in range(2, len(rows), 2)]
    t.setStyle(TableStyle(st))
    return KeepTogether([t])


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 9)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(1.8 * cm, 1.2 * cm, "Segmentación de lotes de café con K-Means · V. E. Alcala Feliz · IDGS 9-3")
    canvas.drawRightString(letter[0] - 1.8 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


def nm(x): return f"{x:,.0f}"


_raw = pd.read_csv(RAIZ / "data" / "raw" / "coffee_ratings.csv")
_h = _raw.head(10)[["country_of_origin", "processing_method", "total_cup_points", "aroma", "flavor", "acidity",
                    "body", "balance", "altitude_mean_meters", "moisture"]].copy()
_h["country_of_origin"] = _h["country_of_origin"].fillna("N/D").astype(str)
_h["processing_method"] = _h["processing_method"].fillna("N/D").astype(str).str.replace(" / ", "/").replace("nan", "N/D")
_h["country_of_origin"] = _h["country_of_origin"].replace("nan", "N/D")
HEAD10 = tbl([["País", "Proceso", "Total", "Arom.", "Sabor", "Acid.", "Cuer.", "Bal.", "Alt. (m)", "Hum."]] +
             [[r.country_of_origin, r.processing_method, f"{r.total_cup_points:.2f}", f"{r.aroma:.2f}", f"{r.flavor:.2f}",
               f"{r.acidity:.2f}", f"{r.body:.2f}", f"{r.balance:.2f}", "NaN" if pd.isna(r.altitude_mean_meters) else nm(r.altitude_mean_meters),
               f"{r.moisture:.2f}"] for r in _h.itertuples()],
            [2.4, 3.0, 1.5, 1.5, 1.5, 1.5, 1.5, 1.4, 1.8, 1.4])
_d = _raw[["total_cup_points", "aroma", "flavor", "acidity", "body", "balance", "altitude_mean_meters", "moisture",
           "category_one_defects"]].describe().T
DESC = tbl([["Variable", "Registros", "Media", "Desv.", "Mín.", "Máx."]] +
           [[i, nm(r["count"]), f"{r['mean']:.2f}", f"{r['std']:.2f}", f"{r['min']:.2f}", f"{r['max']:,.2f}"]
            for i, r in _d.iterrows()], [4.6, 2.2, 2.4, 2.4, 2.2, 2.8])

S = []
# ----------------------------- 1. PORTADA -----------------------------
logos = Table([[img(ASS / "utslrc.png", 5.2 * cm), img(ASS / "idgs.png", 4 * cm)]],
              colWidths=[9 * cm, 8 * cm])
logos.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "LEFT"),
                           ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
S += [Spacer(1, 10), logos, Spacer(1, 2.2 * cm),
      Paragraph("Universidad Tecnológica de San Luis Río Colorado", C),
      Paragraph("Ingeniería en Desarrollo y Gestión de Software · Minería de datos", C),
      Spacer(1, 1.8 * cm),
      Paragraph("<font size=24 color='#6F4E37'><b>Segmentación de lotes de café mediante K-Means y "
                "dashboard interactivo</b></font>", ParagraphStyle("t", parent=C, leading=30)),
      Spacer(1, .6 * cm),
      Paragraph("Proyecto integrador · Tercera unidad", C),
      Spacer(1, 2.2 * cm)]
datos = [["Integrante", "Vladimir Emanuel Alcala Feliz"], ["Grupo", "IDGS 9-3"],
         ["Docente", "Mtra. Julia Elizabeth Garcia Herrera"], ["Fecha", "23 de noviembre de 2026"],
         ["Herramientas", "Python, Pandas, Scikit-learn, Matplotlib, Seaborn, Streamlit"]]
t = Table([[Paragraph(f"<b>{a}</b>", TC), Paragraph(b, TC)] for a, b in datos], colWidths=[4 * cm, 14 * cm])
t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), CLARO), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#CFC3B6")),
                       ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
S += [t, PageBreak()]

# ----------------------------- 2. INTRODUCCIÓN -----------------------------
S += [Paragraph("2. Introducción y planteamiento del problema", H1)]
S += [p("<b>Temática.</b> El café es uno de los productos agrícolas más comercializados del mundo y su precio depende "
        "en gran medida de su calidad en taza. La Specialty Coffee Association (SCA) evalúa cada lote con catadores "
        "certificados que califican atributos como sabor, acidez, cuerpo y balance, y un lote con 85 puntos o más se "
        "considera de especialidad. Además de la calidad sensorial intervienen factores del origen como la altitud "
        "de cultivo y el número de defectos físicos del grano."),
      p("<b>Problemática.</b> Los compradores, cooperativas y productores manejan miles de lotes y suelen "
        "clasificarlos con un solo número (el puntaje total). Ese número esconde información: dos lotes con el mismo "
        "puntaje pueden tener orígenes, altitudes y niveles de defectos muy distintos. No es evidente qué tipos de "
        "lote existen realmente ni qué los diferencia."),
      p("<b>Justificación.</b> Segmentar los lotes con un algoritmo no supervisado permite descubrir perfiles de café "
        "sin etiquetas previas, apoyar decisiones de compra y detectar dónde conviene mejorar la producción "
        "(por ejemplo, el control de defectos). El proyecto aplica el ciclo completo de minería de datos: "
        "exploración, limpieza, modelado, interpretación y comunicación mediante un dashboard."),
      p("<b>Qué se busca identificar con K-Means.</b> Grupos de lotes con características similares en cuatro "
        "atributos sensoriales (sabor, acidez, cuerpo, balance), la altitud y los defectos, por ejemplo un "
        "grupo de café de especialidad, grupos de calidad media que se distinguen por su altitud y un grupo de "
        "baja calidad asociado a defectos.")]

# ----------------------------- 3. OBJETIVOS -----------------------------
S += [Paragraph("3. Objetivos", H1),
      p("<b>Objetivo general.</b> Identificar perfiles de lotes de café mediante el algoritmo K-Means, a partir de su "
        "calidad sensorial, altitud y defectos, y presentar los resultados en un dashboard interactivo que "
        "facilite el análisis y la toma de decisiones."),
      p("<b>Objetivos específicos.</b>")]
S += bl(["Explorar y limpiar el dataset del Coffee Quality Institute corrigiendo nulos, valores imposibles y duplicados.",
         "Preparar las variables (transformación logarítmica y escalamiento con StandardScaler) para el algoritmo.",
         "Evaluar valores de K de 2 a 8 con inercia, silueta, Davies-Bouldin y Calinski-Harabasz, y elegir el más adecuado.",
         "Interpretar los centroides, nombrar cada clúster y compararlos mediante estadísticas descriptivas.",
         "Construir un dashboard en Streamlit con dos páginas, indicadores, gráficas y filtros interactivos.",
         "Derivar hallazgos, recomendaciones y limitaciones, y publicar todo en un repositorio de GitHub."])

# ----------------------------- 4. DATASET -----------------------------
S += [Paragraph("4. Descripción del dataset", H1),
      p("<b>Fuente.</b> <i>Coffee Quality Database</i> del Coffee Quality Institute (CQI), publicado como dataset "
        "abierto en el proyecto TidyTuesday (semana del 7 de julio de 2020, archivo <i>coffee_ratings.csv</i>). "
        "Cada fila es un lote de café evaluado por catadores certificados. El archivo original se incluye en "
        "<i>data/raw/coffee_ratings.csv</i>."),
      p(f"<b>Tamaño.</b> {res['limpieza']['raw']['registros']:,} registros y {res['limpieza']['raw']['columnas']} variables "
        "(requisito: mínimo 500 registros y 5 variables), con lotes de 36 países y 46 años/ciclos de cosecha "
        "reportados. Las variables se agrupan así:")]
S += [tbl([
    ["Grupo", "Variables principales", "Tipo"],
    ["Calidad sensorial (0-10)", "aroma, flavor, aftertaste, acidity, body, balance, cupper_points", "Numérica"],
    ["Puntaje", "total_cup_points (suma SCA, 0-100)", "Numérica"],
    ["Puntajes de limpieza", "uniformity, clean_cup, sweetness", "Numérica"],
    ["Origen", "country_of_origin, region, farm_name, altitude_mean_meters", "Categórica / numérica"],
    ["Proceso y variedad", "processing_method, variety, species, color", "Categórica"],
    ["Calidad física", "moisture, category_one_defects, category_two_defects, quakers", "Numérica"],
    ["Administrativas", "owner, company, certification_*, grading_date, expiration, number_of_bags", "Texto / numérica"],
], [3.8 * cm, 9.5 * cm, 3.7 * cm]), Spacer(1, 8)]
S += [p("<b>Calidad de los datos.</b> En el archivo original 19 columnas tienen valores nulos (por ejemplo 230 sin altitud, "
        "226 sin variedad y 170 sin método de procesamiento). No hay duplicados exactos, pero sí un duplicado lógico "
        "(mismo origen, finca y puntajes). Se detectaron también altitudes imposibles, humedad de 0 % en 264 lotes y "
        "un lote con todas las calificaciones en cero."),
      p("<b>Primeros 10 registros</b> (columnas seleccionadas) cargados con <i>read_csv()</i>:"),
      HEAD10, Spacer(1, 8),
      p("<b>Estadísticas descriptivas</b> de las variables numéricas principales del archivo original:"),
      DESC, Spacer(1, 8),
      fig("01_exploratorias.png", 18 * cm,
          "Figura 1. Exploración inicial: distribución del puntaje total, países con más lotes y altitud con valores atípicos."),
      p("<b>Variables elegidas para el agrupamiento (6).</b> <i>flavor, acidity, body, balance, altitud_m</i> y "
        "<i>log_defectos</i>. Justificación: (1) sabor, acidez, cuerpo y balance son los atributos que describen la "
        "taza; (2) la altitud y los defectos describen el origen y la calidad física del grano, información "
        "complementaria al perfil sensorial; (3) se descartó <i>aroma</i> y <i>aftertaste</i> porque están "
        "fuertemente correlacionados con sabor (r ≈ 0.8) y aportarían información redundante; (4) se descartó la "
        "humedad porque 264 lotes reportan 0 %, un dato faltante disfrazado que sólo introduciría ruido."),
      fig("02_correlacion.png", 14 * cm,
          "Figura 2. Matriz de correlación: los atributos sensoriales se mueven juntos; altitud y humedad son casi independientes.")]

# ----------------------------- 5. DESARROLLO -----------------------------
S += [PageBreak(), Paragraph("5. Desarrollo del proyecto", H1), Paragraph("5.1 Limpieza y preparación", H2)]
S += [tbl([
    ["Problema encontrado", "Cantidad", "Tratamiento y justificación"],
    ["Lote con todas las calificaciones en 0", "1", "Eliminado: es un registro vacío, no un café real."],
    ["Duplicado lógico (mismo origen, finca y puntajes)", "1", "Eliminado para no contar dos veces el mismo lote."],
    ["Altitud imposible (&lt; 100 m o &gt; 3,000 m; hay valores de 190,164 m)", "35",
     "Convertida a nulo (errores de captura); el café no se cultiva a esas alturas."],
    ["Altitud nula (original + inválidas)", "265", "Imputada con la mediana de su país; si el país no tiene datos, mediana global."],
    ["Humedad = 0 % (físicamente imposible)", "264", "Tratada como faltante; sólo se usa de forma descriptiva."],
    ["Variedad / método de proceso nulos", "226 / 169", "Se etiquetan como «Desconocido» para no perder lotes."],
    ["Nombres de país con formato inconsistente", "varios", "Homologados (p. ej. «Tanzania, United Republic Of» → «Tanzania»)."],
    ["Tipos de dato (harvest_year texto «2014/2015»)", "-", "Convertido a numérico (primer año del ciclo)."],
    ["Defectos con cola larga (hasta 63 por lote; 90 atípicos IQR)", "90",
     "Transformación log(1 + defectos): reduce el efecto de los extremos sin borrar lotes reales."],
    ["Atípicos sensoriales (24 a 43 por variable)", "-", "Se conservan: son lotes de calidad baja o excepcional, justo lo que se quiere segmentar."],
], [6.2 * cm, 2.5 * cm, 8.3 * cm]), Spacer(1, 6),
      p(f"Tras la limpieza el dataset quedó con <b>{lim['limpieza']['registros_despues']:,} registros</b> y "
        "<b>0 nulos</b> en las variables del modelo. Se creó la variable derivada <i>defectos</i> (categoría 1 + categoría 2) "
        "y variables codificadas (<i>es_mexico</i>, <i>especie_cod</i>) para el análisis posterior de los grupos. "
        f"La única columna del dataset procesado con nulos es <i>anio_cosecha</i> ({lim['anio_cosecha_nulos']}); "
        "no entra al modelo y no se imputó para no inventar años."),
      fig("03_limpieza_atipicos.png", 18 * cm,
          "Figura 3. Efecto de la limpieza: altitud antes y después, y transformación logarítmica de defectos."),
      p("<b>Escalamiento.</b> Se aplicó <i>StandardScaler</i> (media 0 y desviación 1 en las seis variables). K-Means "
        "usa distancia euclidiana: sin escalar, la altitud (cientos de metros) dominaría sobre los atributos sensoriales "
        "(rango de 6 a 9). Con el escalamiento todas las variables pesan igual.")]

S += [Paragraph("5.2 Implementación de K-Means", H2),
      p("Se usó <i>sklearn.cluster.KMeans</i> con inicialización k-means++, <i>n_init</i> = 10 y <i>random_state</i> = 42 "
        "para que los resultados sean reproducibles. Se evaluaron <b>siete valores de K (2 a 8)</b> con cuatro métricas:")]
mt = [["K", "Inercia", "Silueta", "Davies-Bouldin", "Calinski-Harabasz"]] + \
     [[int(r.K), nm(r.inercia), f"{r.silueta:.3f}", f"{r.davies_bouldin:.3f}", f"{r.calinski_harabasz:.1f}"]
      for r in metk.itertuples()]
S += [tbl(mt, [2 * cm, 3.4 * cm, 3 * cm, 3.6 * cm, 4 * cm]), Spacer(1, 6),
      fig("04_seleccion_k.png", 18 * cm, "Figura 4. Método del codo, silueta y Davies-Bouldin para K = 2 a 8."),
      p("<b>Selección de K = 4.</b> K = 2 tiene la silueta más alta (0.255), pero sólo separa «buen café» de «mal café» y "
        "no distingue el papel de la altitud ni de los defectos. A partir de K = 3 la silueta se estabiliza (~0.18) y la "
        "inercia baja de forma gradual (el codo es suave). K = 4 entrega cuatro perfiles claramente diferentes e "
        "interpretables, por lo que se eligió como mejor equilibrio entre ajuste y utilidad práctica. "
        "El modelo final se entrenó con <i>fit_predict()</i>, asignando un clúster a cada lote.")]

# ----------------------------- 6. RESULTADOS -----------------------------
S += [PageBreak(), Paragraph("6. Resultados y análisis", H1), Paragraph("6.1 Número de clústeres y métricas", H2),
      p(f"Con K = 4 el modelo convergió en {res['iteraciones_final']} iteraciones. Inercia = {nm(res['inercia_final'])}, "
        f"silueta = {res['silueta_final']:.3f}, Davies-Bouldin = {res['davies_bouldin_final']:.3f} y "
        f"Calinski-Harabasz = {res['calinski_final']:.1f}.")]
ct = [["Configuración", "Inercia", "Silueta", "Davies-B.", "Calinski-H.", "Iteraciones"]] + \
     [[r["Configuración"], nm(r["Inercia"]), f"{r['Silueta']:.3f}", f"{r['Davies-Bouldin']:.3f}",
       f"{r['Calinski-Harabasz']:.1f}", r["Iteraciones"]] for r in res["comparacion"]]
S += [Paragraph("6.2 Comparación de dos configuraciones (K = 4 vs. K = 3)", H2), tbl(ct, [4 * cm, 2.4 * cm, 2.2 * cm, 2.6 * cm, 2.8 * cm, 2.6 * cm]),
      Spacer(1, 6),
      p(f"K = 3 obtiene una silueta ligeramente mayor (0.191 vs. 0.184) y mejor Calinski-Harabasz, pero K = 4 reduce la "
        f"inercia un 11 % y mejora Davies-Bouldin (1.52 vs. 1.59). La diferencia clave es cualitativa: con K = 3 los lotes de "
        f"calidad media se funden en un solo grupo y se pierde la distinción entre <i>media de altura</i> y <i>media de baja "
        f"altitud</i>. El índice de Rand ajustado entre ambas particiones es {res['ari_k4_k3']:.2f}, es decir, "
        "coinciden sólo parcialmente: K = 4 no es un simple refinamiento de K = 3.")]

S += [Paragraph("6.3 Centroides", H2),
      p("Sabor, acidez, cuerpo, balance y altitud son los centroides en escala original. El modelo usó "
        "log(1+defectos); en esta tabla se muestra el promedio real de defectos de cada grupo para que coincida "
        "con la tabla comparativa.")]
ce = [["Clúster", "Sabor", "Acidez", "Cuerpo", "Balance", "Altitud (m)", "Defectos (promedio)"]]
orden = ["Café de especialidad", "Calidad media de altura", "Calidad media de baja altitud", "Calidad baja con defectos"]
for n in orden:
    r = cent[cent.Nombre == n].iloc[0]
    ce.append([n, f"{r.flavor:.2f}", f"{r.acidity:.2f}", f"{r.body:.2f}", f"{r.balance:.2f}",
               nm(r.altitud_m), f"{r['Defectos (promedio)']:.1f}"])
S += [tbl(ce, [5 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 2.2 * cm, 2.6 * cm]), Spacer(1, 6),
      fig("07_centroides_heatmap.png", 16 * cm,
          "Figura 5. Centroides estandarizados: el café de especialidad está +1.4 desviaciones sobre la media en sensorial; el grupo bajo, -1.4.")]

S += [PageBreak(), Paragraph("6.4 Agrupamientos y comparación entre grupos", H2),
      fig("05_clusters_scatter.png", 18 * cm,
          "Figura 6. Izquierda: clústeres proyectados con PCA (68.9 % de varianza; X = centroides). Derecha: sabor vs. altitud."),
      fig("06_comparacion_clusters.png", 18 * cm,
          "Figura 7. Lotes por clúster, puntaje total y altitud por clúster.")]

tt = [["Clúster", "Lotes", "%", "Puntaje", "Sabor", "Altitud (m)", "Defectos (promedio)", "% México", "% Natural"]]
for r in tabla.itertuples():
    tt.append([r.cluster, int(r.Lotes), f"{r.Pct_Lotes:.1f}", f"{r.Puntaje_total:.2f}", f"{r.Sabor:.2f}",
               nm(r.Altitud_m), f"{r.Defectos:.1f}", f"{r.Pct_Mexico:.1f}", f"{r.Pct_Natural:.1f}"])
S += [Paragraph("6.5 Tabla comparativa e interpretación de los grupos", H2),
      tbl(tt, [4.1 * cm, 1.2 * cm, 1.1 * cm, 1.6 * cm, 1.3 * cm, 1.8 * cm, 2.7 * cm, 1.8 * cm, 1.9 * cm]), Spacer(1, 6)]
for variable, etiqueta in (("total_cup_points", "Puntaje total"),
                           ("altitud_m", "Altitud (m)"), ("defectos", "Defectos")):
    filas = [["Clúster", "Media", "Mediana", "Desv. est.", "Mín.", "Máx."]]
    for nombre in orden:
        valores = [estad.loc[nombre, (variable, medida)] for medida in ("mean", "median", "std", "min", "max")]
        filas.append([nombre] + [f"{float(valor):,.2f}" for valor in valores])
    S += [p(f"<b>{etiqueta} por clúster</b>"), tbl(filas, [5.4 * cm, 2.4 * cm, 2.4 * cm, 2.7 * cm, 2.4 * cm, 2.7 * cm]), Spacer(1, 4)]
S += bl(["<b>Café de especialidad (254 lotes, 19 %).</b> Mejores perfiles sensoriales (~7.9), puntaje promedio 84.9, altitud "
         "alta y 2.4 defectos por lote en promedio. Origen principal: Colombia, Guatemala y Etiopía.",
         "<b>Calidad media de altura (476 lotes, 36 %).</b> Perfil sensorial promedio (~7.55) con altitud alta (~1,520 m) y "
         "defectos moderados-altos (4.2). Es el grupo más grande.",
         "<b>Calidad media de baja altitud (315 lotes, 24 %).</b> Mismo nivel sensorial pero a ~830 m, con los menos defectos "
         "(2.0) y mayor proporción de proceso natural (37 %).",
         "<b>Calidad baja con defectos (292 lotes, 22 %).</b> Sensorial más bajo (~7.1), puntaje 78.9 y 7.4 defectos por "
         "lote en promedio; 35 % de sus lotes son de México."])
S += [Spacer(1, 4),
      p("<b>Similitudes y diferencias.</b> Los dos grupos de calidad media son casi idénticos en la taza; los separan la "
        "altitud (≈ 690 m de diferencia) y los defectos. El grupo de especialidad y el de calidad media de altura "
        "comparten altitud, así que la altura por sí sola no explica la excelencia (correlación altitud-puntaje de "
        f"sólo {res['hallazgos']['corr_altitud_puntaje']:.2f}).")]

S += [Paragraph("6.6 Hallazgos", H2)]
h = res["hallazgos"]
S += bl([f"Sólo el 19 % de los lotes forma el grupo de especialidad; su rasgo distintivo es el perfil sensorial, no la altitud.",
         "Un grupo de baja altitud con pocos defectos iguala en sabor a uno de altura: el manejo del grano puede compensar la altitud.",
         "Los defectos separan con claridad al grupo de baja calidad: 7.4 por lote contra 2.4 en especialidad y 2.0 en baja altitud.",
         f"Etiopía (77 %), Kenia (68 %) y Uganda (42 %) son los orígenes con mayor proporción de lotes de especialidad (países con 20 o más lotes).",
         f"El {h['mexico_dist']['Calidad baja con defectos']:.1f} % de los {h['mexico_total']} lotes de México cae en «calidad baja con defectos» "
         f"(global: {h['global_dist']['Calidad baja con defectos']:.1f} %) y sólo el {h['mexico_dist']['Café de especialidad']:.1f} % en especialidad."])

# ----------------------------- 7. DASHBOARD -----------------------------
S += [PageBreak(), Paragraph("7. Dashboard", H1),
      p("El dashboard se desarrolló con <b>Streamlit</b> y <b>Plotly</b>, y lee exclusivamente el dataset procesado en Python "
        "(<i>data/processed/coffee_clusters.csv</i>) y las métricas del modelo (<i>outputs/resultados.json</i>). "
        "Se ejecuta con <i>streamlit run dashboard/app.py</i>. Lleva el título <i>BeanCraft Insights</i>, los logotipos institucionales y dos páginas:"),
      Paragraph("Funciones principales", H2)]
S += bl(["<b>Tres filtros interactivos</b> en la barra lateral, funcionales en ambas páginas: país de origen, método de "
         "procesamiento y rango de altitud. En la página 2 se añade además un filtro de clústeres.",
         "<b>Página 1 · Análisis general:</b> cuatro KPI (lotes, puntaje promedio, altitud promedio, % de lotes con 85 puntos o más), "
         "histograma del puntaje, top de países, altitud vs. puntaje con línea de tendencia, puntaje por método de procesamiento y "
         "tabla de estadísticas descriptivas.",
         "<b>Página 2 · Segmentación K-Means:</b> cuatro KPI (lotes segmentados, clústeres, % de especialidad, silueta), distribución "
         "de lotes por clúster, dispersión PCA de los grupos, caja de puntaje por clúster, radar del perfil sensorial, tabla de "
         "estadísticas por clúster, descripción de cada grupo y sección de hallazgos y recomendaciones."])
S += [KeepTogether([img_fit(CAP / "dashboard_pagina1.png"), Paragraph("Figura 8. Dashboard, página 1: análisis general.", CAPT)])]
S += [PageBreak(), KeepTogether([img_fit(CAP / "dashboard_pagina2.png"), Paragraph("Figura 9. Dashboard, página 2: segmentación mediante K-Means.", CAPT)])]
S += [PageBreak(), KeepTogether([img_fit(CAP / "dashboard_pagina2_filtro_mexico.png"), Paragraph("Figura 10. Filtro «País = Mexico» aplicado: los KPI, gráficas y tablas se recalculan (236 lotes).", CAPT)])]

# ----------------------------- 8. CONCLUSIONES -----------------------------
S += [PageBreak(), Paragraph("8. Conclusiones y recomendaciones", H1), Paragraph("Conclusiones", H2),
      p("K-Means permitió segmentar 1,337 lotes de café en cuatro perfiles interpretables que el puntaje total por sí solo no "
        "revela. La calidad en taza, la altitud y los defectos físicos combinan para formar los grupos, y se confirma que la "
        "altitud ayuda, pero no es el factor decisivo de la calidad. El proceso de limpieza fue determinante: altitudes "
        "imposibles de hasta 190,164 m y humedades en 0 % habrían distorsionado por completo las distancias del algoritmo."),
      Paragraph("Recomendaciones", H2)]
S += bl(["<b>Reducir defectos en origen</b> (selección, secado y clasificación del grano): es la característica que más separa al grupo de calidad baja.",
         "<b>Valorar los lotes de baja altitud con pocos defectos</b> como una fuente de calidad media estable y confiable.",
         "<b>Orientar la compra de café de especialidad</b> hacia orígenes con alta proporción de lotes del grupo de especialidad (Etiopía, Kenia, Uganda).",
         "<b>Capacitar en postcosecha a los productores con lotes en el grupo de calidad baja</b>, empezando por los de mayor incidencia de defectos, "
         "como una buena parte de los lotes mexicanos del dataset."])
S += [Paragraph("Limitaciones del modelo", H2)]
S += bl([f"<b>Estructura de grupos débil:</b> la silueta es 0.18, lo que indica clústeres que se traslapan; son segmentos útiles, no categorías naturales separadas.",
         "<b>K-Means supone grupos esféricos</b> y es sensible a la escala y a los valores extremos; se mitigó con StandardScaler y la transformación logarítmica.",
         "<b>Imputación de altitud:</b> 265 lotes (≈ 20 %) tienen altitud estimada con la mediana de su país, lo que puede suavizar diferencias reales.",
         "<b>Sesgo de muestra:</b> los lotes son los enviados al CQI para evaluación y no representan toda la producción de cada país; "
         "las conclusiones sobre México describen únicamente esos 236 lotes.",
         "<b>Variables omitidas:</b> no se incluyeron variedad, región, finca ni precio, que podrían refinar la segmentación.",
         "<b>Los nombres de los clústeres son interpretaciones</b> basadas en los centroides; K-Means no entrega etiquetas por sí mismo."])

doc = SimpleDocTemplate(str(RAIZ / "docs" / "Documentacion_Proyecto.pdf"), pagesize=letter,
                        leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
                        title="BeanCraft Insights: segmentación de lotes de café mediante K-Means",
                        author="Vladimir Emanuel Alcala Feliz")
doc.build(S, onFirstPage=lambda c, d: None, onLaterPages=pie)
print("PDF generado")
