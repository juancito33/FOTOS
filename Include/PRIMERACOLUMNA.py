"""
normalizar_archivos_v9.py
─────────────────────────
• Población inicial en columna npn con hipervínculo.
• Flujos posteriores añaden columnas-regla 1/0 con hipervínculo.
• Copia hojas antiguas sólo si el libro es válido; si ‘BadZipFile’ se
  produce en cualquier intento, se elimina el archivo y se crea de cero.
"""

import pandas as pd, unicodedata, re, pathlib, os
from datetime import datetime
from zipfile import BadZipFile

# ---------- 1 ▸ CONFIG ---------
BASE = pathlib.Path(r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\RESULTADOS_CONSULTAS")

CRUDOS = [
    (r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\alcala_destino_.xlsx",
     None,
     "Población inicial de NPN (consulta Destinos)"),
    # (r"...\propietarios.xlsx", "Fl_Propietarios", "NPN sin propietario"),
]

MATRIZ_PATH   = BASE / "MATRIZ_NPN.xls"
HISTORIAL_TXT = BASE / "HISTORIAL_REGLAS.txt"
BASE.mkdir(parents=True, exist_ok=True)

# ---------- 2 ▸ HELPERS --------
def norm_cols(df):
    df.columns = (df.columns.str.strip().str.lower()
                  .map(lambda s: unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode()))
    return df.loc[:, ~df.columns.str.contains("^unnamed")]

safe_sheet = lambda t: re.sub(r"\W+","_",t.lower())[:25]

def log_regla(col, desc):
    t = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(HISTORIAL_TXT, "a", encoding="utf-8") as f:
        f.write(f"{t} | {col or 'POBLACION'} | {desc}\n")

# ---------- 3 ▸ INTENTAR CARGAR MATRIZ --------
copy_old = False
try:
    matriz = (pd.read_excel(MATRIZ_PATH, sheet_name="matriz",
                            dtype=str, engine="openpyxl")
                .set_index("npn"))
    col_order = list(matriz.columns)
    copy_old  = True
except (FileNotFoundError, BadZipFile, ValueError):
    matriz    = pd.DataFrame().set_index(pd.Index([], name="npn"))
    col_order = []
    if MATRIZ_PATH.exists():
        MATRIZ_PATH.unlink(missing_ok=True)   # elimina corrupto

# ---------- 4 ▸ CREAR WRITER ----------
writer = pd.ExcelWriter(MATRIZ_PATH, engine="xlsxwriter")

# copiar hojas antiguas sólo si realmente podemos abrir el libro
if copy_old:
    try:
        old_wb = pd.ExcelFile(MATRIZ_PATH, engine="openpyxl")
        for hoja in old_wb.sheet_names:
            if hoja != "matriz":
                pd.read_excel(old_wb, sheet_name=hoja, engine="openpyxl") \
                  .to_excel(writer, sheet_name=hoja, index=False)
    except (BadZipFile, ValueError):
        print("↺ Libro previo corrupto durante la copia; se recreará limpio.")
        matriz    = pd.DataFrame().set_index(pd.Index([], name="npn"))
        col_order = []
        copy_old  = False

# ---------- 5 ▸ PROCESAR CRUDOS ----------
poblacion_link = None

for ruta_crudo, col_mat, desc in CRUDOS:
    ruta = pathlib.Path(ruta_crudo)
    if not ruta.exists():
        print("⚠ Falta:", ruta); continue

    df = pd.read_excel(ruta, dtype={"npn":str}).pipe(norm_cols)

    flujo    = safe_sheet(ruta.stem)
    hoja_det = f"detalle_{flujo}"
    df.to_excel(writer, sheet_name=hoja_det, index=False)

    npn_set = set(df["npn"].astype(str))
    matriz  = matriz.reindex(matriz.index.union(npn_set))

    if col_mat is None:
        poblacion_link = f"internal:'{hoja_det}'!A1"
        print(f"✔ Población inicial: {len(npn_set)} NPN")
    else:
        if col_mat not in matriz.columns:
            matriz[col_mat] = ""
            col_order.append(col_mat)
        link = f"internal:'{hoja_det}'!A1"
        matriz.loc[matriz.index.isin(npn_set), col_mat] = link
        print(f"✔ {col_mat}: {len(npn_set)} NPN afectados")

    log_regla(col_mat, desc)

# ---------- 6 ▸ ESCRIBIR MATRIZ ----------
matriz = matriz[col_order].reset_index()
matriz.to_excel(writer, sheet_name="matriz", index=False)
ws = writer.sheets["matriz"]

# hipervínculo en npn
if poblacion_link:
    for r in range(1, len(matriz)+1):
        ws.write_url(r, 0, poblacion_link, string=matriz.iat[r-1, 0])

# hipervínculos 1/0 en columnas-regla
for r in range(1, len(matriz)+1):
    for c, col in enumerate(col_order, start=1):
        v = matriz.iat[r-1, c]
        if isinstance(v, str) and v.startswith("internal:"):
            ws.write_url(r, c, v, string="1")

writer.close()

print("\n✅ MATRIZ guardada en:", MATRIZ_PATH)
print("✅ HISTORIAL actualizado en:", HISTORIAL_TXT)
