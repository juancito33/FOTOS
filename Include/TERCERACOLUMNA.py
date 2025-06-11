"""
normalizar_archivos_v19.py
──────────────────────────
• Genera MATRIZ_NPN.xlsx y rehace la hoja RESUMEN
  con métricas de las tres columnas-regla procesadas hasta ahora.
"""

import pandas as pd, unicodedata, re, pathlib, os
from zipfile import BadZipFile
from datetime import datetime

# ----- CONFIG -----
BASE = pathlib.Path(
    r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\RESULTADOS_CONSULTAS"
)
MATRIZ_PATH   = BASE / "MATRIZ_NPN.xlsx"
HISTORIAL_TXT = BASE / "HISTORIAL_REGLAS.txt"
BASE.mkdir(parents=True, exist_ok=True)

CRUDOS = [
    (r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\alcala_destino_.xlsx",
     None,
     "Población inicial de NPN (consulta Destinos)"),

    (r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\inconsistentes_npn.xlsx",
     "inconsistencia_destido",
     "NPN con inconsistencias (área/tipo/destino)"),

    (r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\npn_matricula_vacia_pos22_0.xlsx",
     "matricula_vacia_pos22",
     "NPN cuya matrícula (posición 22) está vacía = 0"),
]

# ----- AUX -------
def norm(df):                                  # normaliza columnas
    df.columns = (df.columns.str.strip().str.lower()
                  .map(lambda s: unicodedata.normalize("NFKD", s)
                                 .encode("ascii","ignore").decode()))
    return df.loc[:, ~df.columns.str.contains("^unnamed")]

def safe(txt):                                 # nombre <= 23 (31-8)
    return re.sub(r"\W+","_",txt.lower())[:23]

def add_table(ws, df, name):
    rows, cols = df.shape
    ws.add_table(0, 0, rows, cols-1,
                 {"header_row": True,
                  "columns":[{"header":h} for h in df.columns],
                  "name": name})

def log(col, desc):
    with open(HISTORIAL_TXT, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} | {col or 'POBLACION'} | {desc}\n")

# ----- CARGAR MATRIZ -----
try:
    matriz = (pd.read_excel(MATRIZ_PATH, "matriz",
                            dtype=str, engine="openpyxl")
                .set_index("npn"))
    col_order, copy_old = list(matriz.columns), True
except (FileNotFoundError, BadZipFile, ValueError):
    matriz, col_order = pd.DataFrame().set_index(pd.Index([], name="npn")), []
    copy_old = False
    MATRIZ_PATH.unlink(missing_ok=True)

# ----- WRITER -----
writer = pd.ExcelWriter(MATRIZ_PATH, engine="xlsxwriter")

# copiamos todas las hojas menos 'matriz' y 'resumen' (las reharemos)
if copy_old:
    try:
        old = pd.ExcelFile(MATRIZ_PATH, engine="openpyxl")
        for sh in old.sheet_names:
            if sh not in ("matriz", "resumen"):
                pd.read_excel(old, sh, engine="openpyxl")\
                  .to_excel(writer, sh, index=False)
    except (BadZipFile, ValueError):
        matriz, col_order = pd.DataFrame().set_index(pd.Index([], name="npn")), []

# ----- VARIABLES para resumen -----
detail_destinos = None
nuevos_matricula, coinc_matricula = set(), 0
poblacion_link = None

# ----- PROCESAR CRUDOS -----
for ruta, col_mat, desc in CRUDOS:
    ruta = pathlib.Path(ruta)
    if not ruta.exists():
        print("⚠ Falta:", ruta); continue

    df = pd.read_excel(ruta, dtype={"npn":str}).pipe(norm)

    if col_mat == "inconsistencia_destido":
        df = df[["npn", "destinos", "motivo_npn"]]
        detail_destinos = df

    flujo  = safe(ruta.stem)
    hoja   = f"detalle_{flujo}"
    df.to_excel(writer, sheet_name=hoja, index=False)
    add_table(writer.sheets[hoja], df, f"tbl_{flujo}")

    set_npn = set(df["npn"].astype(str))
    matriz  = matriz.reindex(matriz.index.union(set_npn))

    # 1) población
    if col_mat is None:
        poblacion_link = f"internal:'{hoja}'!A1"
    # 2) columnas-regla
    else:
        if col_mat not in matriz.columns:
            matriz[col_mat] = "0"
            col_order.append(col_mat)
        link = f"internal:'{hoja}'!A1"
        matriz.loc[list(set_npn), col_mat] = link

        if col_mat == "matricula_vacia_pos22":
            coinc_matricula  = len(matriz.index.intersection(set_npn))
            nuevos_matricula = set_npn.difference(matriz.index)

    log(col_mat, desc)

# ----- GUARDAR MATRIZ -----
matriz = matriz[col_order].reset_index()
matriz.to_excel(writer, "matriz", index=False)
ws_mat = writer.sheets["matriz"]

# hipervínculos en npn y 1/0
if poblacion_link:
    for r in range(1, len(matriz)+1):
        ws_mat.write_url(r, 0, poblacion_link, string=matriz.iat[r-1,0])
for r in range(1, len(matriz)+1):
    for c in range(1, len(col_order)+1):
        v = matriz.iat[r-1, c]
        if isinstance(v,str) and v.startswith("internal:"):
            ws_mat.write_url(r, c, v, string="1")

# ----- RECREAR RESUMEN -----
total_npn = len(matriz)
rows_res  = []

for col in col_order:
    afectados = (matriz[col].str.startswith("internal")).sum()
    rows_res.append([f"NPN con {col}", afectados])
    rows_res.append([f"% afectación {col}", f"{afectados/total_npn:.2%}"])

# bloque general
general = pd.DataFrame(
    [["Total NPN", total_npn]] + rows_res,
    columns=["Métrica","Valor"]
)
general.to_excel(writer, "resumen", index=False, startrow=0)

offset = len(general) + 2

# desglose destino (si existe)
if detail_destinos is not None:
    des = (detail_destinos.groupby("destinos")["npn"]
             .nunique().reset_index()
             .rename(columns={"npn":"NPN_inconsistentes"}))
    des.to_excel(writer, "resumen", index=False, startrow=offset)
    offset += len(des) + 2

# lista nuevos matrícula
if nuevos_matricula:
    pd.DataFrame({"NPN_nuevos_matricula": sorted(nuevos_matricula)}) \
        .to_excel(writer, "resumen", index=False, startrow=offset)

writer.close()
print("\n✅ MATRIZ_NPN.xlsx reconstruido: resumen incluye las 3 columnas-regla.")
print("⚠ Guarda como .xlsm para usar los filtros con la macro.")
