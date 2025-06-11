"""
normalizar_archivos_v14.py
──────────────────────────
• Igual que v13 + hoja RESUMEN con conteos:
    – total NPN población
    – total con inconsistencia_destido = 1
    – % afectación
    – desglose por ‘destinos’ de los inconsistentes
"""

import pandas as pd, unicodedata, re, pathlib, os
from datetime import datetime
from zipfile import BadZipFile

# ---------------- 1 · CONFIG -----------------
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
]

# ---------------- 2 · AUX --------------------
def norm_cols(df):
    df.columns = (df.columns.str.strip().str.lower()
                  .map(lambda s: unicodedata.normalize("NFKD", s)
                                 .encode("ascii","ignore").decode()))
    return df.loc[:, ~df.columns.str.contains("^unnamed")]

safe_sheet = lambda t: re.sub(r"\W+","_",t.lower())[:25]

def log_regla(col, desc):
    t = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(HISTORIAL_TXT, "a", encoding="utf-8") as f:
        f.write(f"{t} | {col or 'POBLACION'} | {desc}\n")

# ---------------- 3 · CARGAR MATRIZ ----------
try:
    matriz = (pd.read_excel(MATRIZ_PATH, "matriz",
                            dtype=str, engine="openpyxl")
                .set_index("npn"))
    col_order, copy_old = list(matriz.columns), True
except (FileNotFoundError, BadZipFile, ValueError):
    matriz    = pd.DataFrame().set_index(pd.Index([], name="npn"))
    col_order, copy_old = [], False
    MATRIZ_PATH.unlink(missing_ok=True)

# ---------------- 4 · WRITER -----------------
writer = pd.ExcelWriter(MATRIZ_PATH, engine="xlsxwriter")

if copy_old:
    try:
        old = pd.ExcelFile(MATRIZ_PATH, engine="openpyxl")
        for sh in old.sheet_names:
            if sh not in ("matriz", "resumen"):
                pd.read_excel(old, sh, engine="openpyxl") \
                  .to_excel(writer, sh, index=False)
    except (BadZipFile, ValueError):
        matriz    = pd.DataFrame().set_index(pd.Index([], name="npn"))
        col_order = []

detalle_df_incons = None   # guardaremos dataframe para resumen
poblacion_link = None

# ---------------- 5 · PROCESAR CRUDOS --------
for ruta, col_mat, desc in CRUDOS:
    ruta = pathlib.Path(ruta)
    if not ruta.exists():
        print("⚠ Falta:", ruta); continue

    df = pd.read_excel(ruta, dtype={"npn":str}).pipe(norm_cols)

    if col_mat == "inconsistencia_destido":
        df = df[["npn", "destinos", "motivo_npn"]]
        detalle_df_incons = df.copy()

    flujo    = safe_sheet(ruta.stem)
    hoja_det = f"detalle_{flujo}"
    df.to_excel(writer, hoja_det, index=False)

    # crear tabla con encabezados
    ws = writer.sheets[hoja_det]
    rows, cols = df.shape
    headers = [{"header": h} for h in df.columns]
    ws.add_table(0, 0, rows, cols-1,
                 {"header_row": True,
                  "columns": headers,
                  "name": f"tbl_{flujo}"})

    # actualizar matriz
    npn_set  = set(df["npn"].astype(str))
    matriz   = matriz.reindex(matriz.index.union(npn_set))

    if col_mat is None:
        poblacion_link = f"internal:'{hoja_det}'!A1"
    else:
        if col_mat not in matriz.columns:
            matriz[col_mat] = "0"
            col_order.append(col_mat)
        link = f"internal:'{hoja_det}'!A1"
        for npn in npn_set:
            matriz.at[npn, col_mat] = link

    log_regla(col_mat, desc)

# ---------------- 6 · GUARDAR MATRIZ ---------
matriz = matriz[col_order].reset_index()
matriz.to_excel(writer, "matriz", index=False)
ws_mat = writer.sheets["matriz"]

# hipervínculo npn
if poblacion_link:
    for r in range(1, len(matriz)+1):
        ws_mat.write_url(r, 0, poblacion_link, string=matriz.iat[r-1, 0])

# hipervínculos 1/0
for r in range(1, len(matriz)+1):
    for c in range(1, len(col_order)+1):
        v = matriz.iat[r-1, c]
        if isinstance(v, str) and v.startswith("internal:"):
            ws_mat.write_url(r, c, v, string="1")

# ---------------- 7 · RESUMEN ----------------
if detalle_df_incons is not None:
    total_npn  = len(matriz)
    total_inc  = detalle_df_incons["npn"].nunique()
    pct_inc    = total_inc / total_npn if total_npn else 0

    resumen_df = pd.DataFrame({
        "Métrica": ["Total NPN", "NPN con inconsistencia_destido", "% afectación"],
        "Valor":   [total_npn, total_inc, f"{pct_inc:.2%}"]
    })

    # desglose por destino
    tabla_dest = (detalle_df_incons.groupby("destinos")["npn"]
                    .nunique().reset_index()
                    .rename(columns={"npn":"NPN_inconsistentes"}))

    resumen_df.to_excel(writer, "resumen", index=False, startrow=0)
    tabla_dest.to_excel(writer, "resumen", index=False, startrow=6)

writer.close()
print("\n✅ MATRIZ_NPN.xlsx actualizado con hoja RESUMEN.")
print("⚠ Inserta/actualiza la macro y guarda como .xlsm para usarla con filtros.")
