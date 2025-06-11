"""
normalizar_archivos_v26.py
──────────────────────────
• Mismo formato y flujo que la versión v19.
• Añade la 4.ª columna-regla **matriculas_duplicadas**:

      – Lee matriculas_duplicadas.xlsx
      – Conserva SOLO las filas cuya matricula_inmobiliaria
        esté repetida (duplicated keep=False).
      – Crea la hoja detalle_matriculas_duplicadas
      – En la hoja matriz coloca “1” con hipervínculo
        para esos NPN; “0” en los demás.

• Rehace la hoja RESUMEN con 4 métricas totales.
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

    (r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\matriculas_duplicadas.xlsx",
     "matriculas_duplicadas",
     "NPN con matricula_inmobiliaria duplicada"),
]

# ----- AUX -----
def norm(df):
    df.columns = (df.columns.str.strip().str.lower()
                  .map(lambda s: unicodedata.normalize("NFKD", s)
                                 .encode("ascii","ignore").decode()))
    return df.loc[:, ~df.columns.str.contains("^unnamed")]

def safe(txt):                                # nombre ≤ 23 (31-8)
    return re.sub(r"\W+","_",txt.lower())[:23]

def add_table(ws, df, name):
    r, c = df.shape
    ws.add_table(0, 0, r, c-1,
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

# copiar otras hojas (salvo matriz/resumen)
if copy_old:
    try:
        old = pd.ExcelFile(MATRIZ_PATH, engine="openpyxl")
        for sh in old.sheet_names:
            if sh not in ("matriz", "resumen"):
                pd.read_excel(old, sh, engine="openpyxl") \
                  .to_excel(writer, sh, index=False)
    except (BadZipFile, ValueError):
        matriz, col_order = pd.DataFrame().set_index("npn"), []

# ----- VARIABLES RESUMEN -----
detail_destinos = None
poblacion_link  = None

# ----- PROCESAR CRUDOS -----
for ruta, col_mat, desc in CRUDOS:
    ruta = pathlib.Path(ruta)
    if not ruta.exists():
        print("⚠ Falta:", ruta); continue

    df_in = pd.read_excel(ruta, dtype=str).pipe(norm)

    # tratamiento especial duplicadas
    if col_mat == "matriculas_duplicadas":
        if {"npn", "matricula_inmobiliaria"}.issubset(df_in.columns):
            dup_mask = df_in.duplicated("matricula_inmobiliaria", keep=False)
            df = df_in[dup_mask].copy()
        else:
            print("⚠ El archivo duplicadas necesita columnas 'npn' y 'matricula_inmobiliaria'.")
            continue
    elif col_mat == "inconsistencia_destido":
        df = df_in[["npn", "destinos", "motivo_npn"]]
        detail_destinos = df
    else:
        df = df_in

    flujo  = safe(ruta.stem)
    hoja   = f"detalle_{flujo}"
    df.to_excel(writer, sheet_name=hoja, index=False)
    add_table(writer.sheets[hoja], df, f"tbl_{flujo}")

    set_npn = set(df["npn"].astype(str))
    matriz  = matriz.reindex(matriz.index.union(set_npn))

    # población
    if col_mat is None:
        poblacion_link = f"internal:'{hoja}'!A1"
        log(col_mat, desc)
        continue

    # columna-regla
    if col_mat not in matriz.columns:
        matriz[col_mat] = "0"
        col_order.append(col_mat)

    matriz.loc[list(set_npn), col_mat] = f"internal:'{hoja}'!A1"
    log(col_mat, desc)

# ----- GUARDAR MATRIZ -----
matriz = matriz[col_order].reset_index()
matriz.to_excel(writer, "matriz", index=False)
ws_mat = writer.sheets["matriz"]

# hipervínculos npn
if poblacion_link:
    for r in range(1, len(matriz)+1):
        ws_mat.write_url(r, 0, poblacion_link, string=matriz.iat[r-1,0])
# hipervínculos 1/0
for r in range(1, len(matriz)+1):
    for c in range(1, len(col_order)+1):
        v = matriz.iat[r-1, c]
        if isinstance(v,str) and v.startswith("internal:"):
            ws_mat.write_url(r, c, v, string="1")

# ----- RECREAR RESUMEN -----
total_npn = len(matriz)
rows = [["Total NPN", total_npn]]
for col in col_order:
    aff = (matriz[col].str.startswith("internal")).sum()
    rows += [[f"NPN con {col}", aff],
             [f"% afectación {col}", f"{aff/total_npn:.2%}"]]

pd.DataFrame(rows, columns=["Métrica","Valor"]) \
  .to_excel(writer, "resumen", index=False)

writer.close()
print("\n✅ MATRIZ_NPN.xlsx actualizado con la columna 'matriculas_duplicadas' "
      "y resumen de 4 métricas.\n"
      "⚠ Guarda como .xlsm si necesitas seguir usando la macro de filtros.")
