"""
normalizar_archivos_v29.py
──────────────────────────
• Igual al v28, pero añade la 7.ª columna-regla:
      unidades_singeometria
  –  Lee UNIDADES_SINGEOMETRIA.xlsx
  –  Conserva SOLO la columna npn y elimina duplicados
  –  Crea la hoja detalle_unidades_singeometria
  –  Hipervínculo “1” en la matriz
  –  Actualiza el RESUMEN (ahora 7 métricas)
"""

import pandas as pd, unicodedata, re, pathlib
from zipfile import BadZipFile, LargeZipFile
from datetime import datetime

# ───── CONFIG
BASE = pathlib.Path(
    r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\RESULTADOS_CONSULTAS"
)
MATRIZ_PATH = BASE / "MATRIZ_NPN.xlsx"
HIST_LOG    = BASE / "HISTORIAL_REGLAS.txt"
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

    (r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\propietarios_error_digitacion.xlsx",
     "error_digitacion_prop",
     "Propietarios con posible error de digitación"),

    (r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\TERRENOS_SINUNIDADES.xlsx",
     "terrenos_sin_unidades",
     "Terrenos que no tienen unidades asociadas"),

    (r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\UNIDADES_SINGEOMETRIA.xlsx",
     "unidades_singeometria",
     "NPN con unidades constructivas sin geometría"),
]

# ───── HELPERS
def norm(df):
    df.columns = (df.columns.str.strip().str.lower()
                  .map(lambda s: unicodedata.normalize("NFKD", s)
                                 .encode("ascii", "ignore").decode()))
    return df.loc[:, ~df.columns.str.contains("^unnamed")]

safe = lambda t: re.sub(r"\W+", "_", t.lower())[:23]

def add_table(ws, df, name):
    r, c = df.shape
    ws.add_table(0, 0, r, c-1,
                 {"header_row": True,
                  "columns": [{"header": h} for h in df.columns],
                  "name": name})

def log(col, text):
    with open(HIST_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M}|{col or 'POBLACION'}|{text}\n")

# ───── CARGAR MATRIZ
try:
    matriz = (pd.read_excel(MATRIZ_PATH, "matriz", dtype=str,
                            engine="openpyxl").set_index("npn"))
    col_order, copy_old = list(matriz.columns), True
except (FileNotFoundError, ValueError, BadZipFile, LargeZipFile):
    matriz, col_order, copy_old = pd.DataFrame().set_index("npn"), [], False
    MATRIZ_PATH.unlink(missing_ok=True)

# ───── WRITER
writer = pd.ExcelWriter(MATRIZ_PATH, engine="xlsxwriter")
if copy_old:
    try:
        old = pd.ExcelFile(MATRIZ_PATH, engine="openpyxl")
        for sh in old.sheet_names:
            if sh not in ("matriz", "resumen"):
                pd.read_excel(old, sh, engine="openpyxl") \
                  .to_excel(writer, sh, index=False)
    except Exception:
        pass

# ───── PROCESAR CRUDOS
poblacion_link = None
for ruta, col_mat, desc in CRUDOS:
    ruta = pathlib.Path(ruta)
    if not ruta.exists():
        print("⚠ Falta:", ruta); continue

    df_in = pd.read_excel(ruta, dtype=str).pipe(norm)

    # Procesamiento especial
    if col_mat == "matriculas_duplicadas":
        if {"npn", "matricula_inmobiliaria"}.issubset(df_in.columns):
            df = df_in[df_in.duplicated("matricula_inmobiliaria", keep=False)]
        else:
            print("⚠", ruta.name, "requiere 'npn' y 'matricula_inmobiliaria'."); continue

    elif col_mat == "inconsistencia_destido":
        df = df_in[["npn", "destinos", "motivo_npn"]]

    elif col_mat == "error_digitacion_prop":
        needed = {"npn", "documento_identidad"}
        if not needed.issubset(df_in.columns):
            print("⚠", ruta.name, "requiere 'npn' y 'documento_identidad'."); continue
        extra = [c for c in df_in.columns if re.search(r"(nombre|razon)", c)]
        df = df_in[list(needed) + extra]

    elif col_mat in ("terrenos_sin_unidades", "unidades_singeometria"):
        if "npn" not in df_in.columns:
            print("⚠", ruta.name, "requiere columna 'npn'."); continue
        df = df_in[["npn"]].drop_duplicates()

    else:
        df = df_in

    hoja = f"detalle_{safe(ruta.stem)}"
    df.to_excel(writer, hoja, index=False)
    add_table(writer.sheets[hoja], df, f"tbl_{safe(ruta.stem)}")

    set_npn = set(df["npn"].astype(str))
    matriz  = matriz.reindex(matriz.index.union(set_npn))

    if col_mat is None:           # población
        poblacion_link = f"internal:'{hoja}'!A1"
        log(col_mat, desc)
        continue

    if col_mat not in matriz.columns:
        matriz[col_mat] = "0"
        col_order.append(col_mat)

    matriz.loc[list(set_npn), col_mat] = f"internal:'{hoja}'!A1"
    log(col_mat, desc)

# ───── GUARDAR MATRIZ
matriz = matriz[col_order].reset_index()
matriz.to_excel(writer, "matriz", index=False)
ws = writer.sheets["matriz"]

if poblacion_link:
    for r in range(1, len(matriz)+1):
        ws.write_url(r, 0, poblacion_link, string=matriz.iat[r-1, 0])
for r in range(1, len(matriz)+1):
    for c in range(1, len(col_order)+1):
        val = matriz.iat[r-1, c]
        if isinstance(val, str) and val.startswith("internal:"):
            ws.write_url(r, c, val, string="1")

# ───── RESUMEN
total = len(matriz)
rows = [["Total NPN", total]]
for col in col_order:
    aff = (matriz[col].str.startswith("internal")).sum()
    rows += [[f"NPN con {col}", aff],
             [f"% afectación {col}", f"{aff/total:.2%}"]]

pd.DataFrame(rows, columns=["Métrica", "Valor"]).to_excel(writer, "resumen", index=False)

writer.close()
print("\n✅ MATRIZ_NPN.xlsx actualizado con la columna 'unidades_singeometria' y resumen de 7 métricas.")
