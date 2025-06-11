# import pandas as pd

# ruta = r"D:\TRABAJO_VA_GEOINFORMATCA\1CRUCE_HISTORI.xlsx"      # ← pon aquí la ruta real
# df = pd.read_excel(ruta)      # si tu hoja no es la primera, añade sheet_name="nombre"

# # Muestra la lista de columnas en el mismo orden del archivo
# print(df.columns.tolist())



















import pandas as pd
from pathlib import Path

ruta = Path(r"D:\TRABAJO_VA_GEOINFORMATCA\1CRUCE_HISTORI.xlsx")
df   = pd.read_excel(ruta)

# ─────────────────────────────
# 1.  Normalizar números
# ─────────────────────────────
df['shape_Area'] = (df['shape_Area']
                       .astype(str)
                       .str.replace(' ', '')
                       .str.replace(',', '.')       # coma → punto
                       .str.replace(r'[^\d\.]', '', regex=True)
                   )

for col in ['shape_Area', 'area_construida', 'total_pisos']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Número de la planta (PS-01 → 1, PS-02 → 2…)
df['planta_num'] = (
    df['planta']
      .astype(str)
      .str.extract(r'(\d+)$', expand=False)
      .astype('Int64')
)

# ─────────────────────────────
# 2.  Agrupar por unidad
# ─────────────────────────────
agrup = (df
         .groupby(['npn', 'identifica'], as_index=False)
         .agg(area_shape_sum=('shape_Area', 'sum'),
              pisos_geom    =('planta_num', 'nunique'),
              min_planta    =('planta_num', 'min'),
              area_construida=('area_construida', 'first'),
              total_pisos   =('total_pisos', 'first'),
              identificador =('identificador', 'first'))
)

# ─────────────────────────────
# 3.  Filtrar coincidencias básicas
# ─────────────────────────────
coinc = agrup[
    (agrup['area_shape_sum'] - agrup['area_construida']).abs() <= 1
    & (agrup['pisos_geom'] == agrup['total_pisos'])
]

# ─────────────────────────────
# 4.  Nuevo filtro de piso correcto
# ─────────────────────────────
# Regla: si total_pisos == 1 → min_planta debe ser 1
ok_piso   = coinc[~((coinc['total_pisos'] == 1) & (coinc['min_planta'] != 1))]   # válidos
descartes = coinc[((coinc['total_pisos'] == 1) & (coinc['min_planta'] != 1))]    # piso errado

# (Opcional) Para total_pisos > 1 podrías añadir otras reglas,
# p. ej. exigir que min_planta sea 1 y que max_planta == total_pisos.

# ─────────────────────────────
# 5.  Eliminar duplicados por superficie idéntica
#     (npn + area_construida + total_pisos), guardamos la letra con menor planta
# ─────────────────────────────
ok_piso = (ok_piso
           .sort_values('min_planta')                   # primero la planta 1
           .drop_duplicates(subset=['npn',
                                     'area_construida',
                                     'total_pisos'],
                             keep='first')
          )

# ─────────────────────────────
# 6.  Exportar
# ─────────────────────────────
salida_ok  = ruta.with_name("coincidencias_final.xlsx")
salida_bad = ruta.with_name("coincidencias_descartadas.xlsx")

ok_piso.to_excel(salida_ok,  index=False)
descartes.to_excel(salida_bad, index=False)

print(f"Coincidencias definitivas:   {len(ok_piso)}  →  {salida_ok.name}")
print(f"Descartadas por piso errado: {len(descartes)}  →  {salida_bad.name}")
