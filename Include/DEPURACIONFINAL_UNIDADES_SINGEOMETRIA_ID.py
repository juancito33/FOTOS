# import pandas as pd

# ruta = r"D:\TRABAJO_VA_GEOINFORMATCA\1CRUCE_HISTORI.xlsx"      # ← pon aquí la ruta real
# df = pd.read_excel(ruta)      # si tu hoja no es la primera, añade sheet_name="nombre"

# # Muestra la lista de columnas en el mismo orden del archivo
# print(df.columns.tolist())













import pandas as pd
from pathlib import Path

# ───────────────────────────────
# CONFIGURACIÓN BÁSICA
# ───────────────────────────────
ruta_excel = Path(r"D:\TRABAJO_VA_GEOINFORMATCA\1CRUCE_HISTORI.xlsx")     # ← ajusta tu ruta
df = pd.read_excel(ruta_excel)

# ───────────────────────────────
# 1. LIMPIEZA Y NORMALIZACIÓN
# ───────────────────────────────
# shape_Area trae coma decimal → la convertimos a punto
df['shape_Area'] = (
    df['shape_Area']
      .astype(str)
      .str.replace(' ', '')
      .str.replace(',', '.')           # coma → punto
      .str.replace(r'[^\d\.]', '', regex=True)
)

for col in ['shape_Area', 'area_construida', 'total_pisos']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Número del piso: PS-01 → 1, PS-02 → 2 ...
df['planta_num'] = (
    df['planta']
      .astype(str)
      .str.extract(r'(\d+)$', expand=False)
      .astype('Int64')
)

# ───────────────────────────────
# 2. AGRUPAR POR UNIDAD (npn + identifica)
# ───────────────────────────────
agrup = (
    df.groupby(['npn', 'identifica'], as_index=False)
      .agg(
          area_shape_sum  = ('shape_Area', 'sum'),
          pisos_geom      = ('planta_num', 'nunique'),
          min_planta      = ('planta_num', 'min'),
          area_construida = ('area_construida', 'first'),
          total_pisos     = ('total_pisos', 'first'),
          identificador   = ('identificador', 'first'),
          id              = ('id', 'first')           # ← id presente
      )
)

# ───────────────────────────────
# 3. FILTRO PRINCIPAL
#    - Áreas ±1 m²
#    - Número de pisos coincide
# ───────────────────────────────
coinc = agrup[
    (agrup['area_shape_sum'] - agrup['area_construida']).abs() <= 1
    & (agrup['pisos_geom'] == agrup['total_pisos'])
]

# ───────────────────────────────
# 4. REGLA ADICIONAL PARA total_pisos = 1
#    Debe existir al menos planta 1
# ───────────────────────────────
validos   = coinc[~((coinc['total_pisos'] == 1) & (coinc['min_planta'] != 1))]
descartes = coinc[((coinc['total_pisos'] == 1) & (coinc['min_planta'] != 1))]

# ───────────────────────────────
# 5. DEDUPLICAR POSIBLES REPETIDOS
#    (npn + área + total_pisos + id)
#    Conservar la unidad cuya planta mínima es menor
# ───────────────────────────────
validos = (
    validos
      .sort_values('min_planta')     # primero la planta 1
      .drop_duplicates(
          subset=['npn', 'area_construida', 'total_pisos', 'id'],
          keep='first'
      )
)

# ───────────────────────────────
# 6. EXPORTAR RESULTADOS
# ───────────────────────────────
salida_ok  = ruta_excel.with_name("coincidencias_finalID.xlsx")
salida_bad = ruta_excel.with_name("coincidencias_descartadasID.xlsx")

validos.to_excel(salida_ok,  index=False)
descartes.to_excel(salida_bad, index=False)

print(f"Coincidencias definitivasID   : {len(validos)}  →  {salida_ok.name}")
print(f"Descartadas por piso erradoID : {len(descartes)}  →  {salida_bad.name}")




