"""
REVISION_PROPIETARIOS.py
Flujo 2 – Verifica propietarios a partir del archivo Excel:

    D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\propietarios.xlsx   (hoja 3)

Definiciones
------------
Fila con propietario      : interesado_id no es nulo ni cadena vacía.
Fila “solo cartográfica”  : interesado_id vacío pero alfa_carto_id sí tiene valor.
Fila “huérfana”           : interesado_id y alfa_carto_id ambos vacíos.

Un NPN se reporta como “sin propietario” si NINGUNA de sus filas
contiene un interesado_id válido.

Archivos de salida
------------------
1) propietarios_resumen.xlsx
2) npn_sin_propietario.xlsx
"""

import pandas as pd
import os

# --------------------------------------------------------------
# 1 · Parámetros de entrada y salida
# --------------------------------------------------------------
XLSX_PATH = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\propietarios.xlsx"
SHEET_IDX = 0  # hoja 3 (índice 0-based)

OUT_DIR   = os.path.dirname(XLSX_PATH)
RESUMEN_XLS = os.path.join(OUT_DIR, "propietarios_resumen.xlsx")
NO_OWNER_XLS = os.path.join(OUT_DIR, "npn_sin_propietario.xlsx")

# --------------------------------------------------------------
# 2 · Cargar datos
# --------------------------------------------------------------
df = pd.read_excel(
    XLSX_PATH,
    sheet_name=SHEET_IDX,
    dtype={"npn": str, "interesado_id": str, "alfa_carto_id": str}
)

df.columns = df.columns.str.strip().str.lower()

# --------------------------------------------------------------
# 3 · Clasificación de cada fila
# --------------------------------------------------------------
# (a) interesado_id válido ⇒ propietario presente
df["tiene_propietario"] = (
    df["interesado_id"]
      .fillna("")
      .str.strip()
      .ne("")
)

# (b) fila huérfana ⇒ sin interesado_id y sin alfa_carto_id
df["fila_huerfana"] = (
    df["interesado_id"].fillna("").str.strip().eq("") &
    df["alfa_carto_id"].fillna("").str.strip().eq("")
)

# --------------------------------------------------------------
# 4 · Resumen por NPN
# --------------------------------------------------------------
resumen = (
    df.groupby("npn", as_index=False)
      .agg(
          unidades_total     = ('npn', 'size'),
          filas_propietario  = ('tiene_propietario', 'sum'),
          filas_huerfanas    = ('fila_huerfana', 'sum')
      )
)

# npn sin propietario → filas_propietario == 0
sin_propietario = resumen[resumen["filas_propietario"] == 0] \
                  .drop(columns="filas_propietario")

# --------------------------------------------------------------
# 5 · Exportar resultados
# --------------------------------------------------------------
with pd.ExcelWriter(RESUMEN_XLS, engine="xlsxwriter") as w:
    resumen.to_excel(w, index=False, sheet_name="resumen_prop")

with pd.ExcelWriter(NO_OWNER_XLS, engine="xlsxwriter") as w:
    sin_propietario.to_excel(w, index=False, sheet_name="sin_propietario")

print("Flujo 2 completado.")
print(f"→ Resumen propietarios : {RESUMEN_XLS}")
print(f"→ NPN sin propietario  : {NO_OWNER_XLS}")
