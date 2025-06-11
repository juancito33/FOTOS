import pandas as pd

# Rutas locales a los archivos CSV
archivo1 = r"C:\Users\57316\Downloads\VISITADO_CAR_DESTINO.csv"
archivo2 = r"C:\Users\57316\Downloads\CANCELA_CARTAGO_DESTINO.csv"

# Leer y limpiar espacios en todas las columnas como texto
df1 = pd.read_csv(archivo1, dtype=str).fillna('').apply(lambda x: x.str.strip())
df2 = pd.read_csv(archivo2, dtype=str).fillna('').apply(lambda x: x.str.strip())

# ------------------------------
# 1. Coincidencias exactas por (npn, codigo)
# ------------------------------
coinciden = pd.merge(df1, df2, on=['npn', 'codigo'], how='inner')

# ------------------------------
# 2. npn coinciden pero código es diferente
# ------------------------------
merge_npn = pd.merge(df1, df2, on='npn', how='inner', suffixes=('_1', '_2'))
codigo_distinto = merge_npn[merge_npn['codigo_1'] != merge_npn['codigo_2']]

# ------------------------------
# 3. Registros del archivo1 que no existen en archivo2 por (npn, codigo)
# ------------------------------
df1_unicos = df1.merge(df2, on=['npn', 'codigo'], how='left', indicator=True)
no_existen = df1_unicos[df1_unicos['_merge'] == 'left_only'].drop(columns=['_merge'])

# ------------------------------
# Guardar resultados en mismo directorio de descargas
# ------------------------------
coinciden.to_csv(r"C:\Users\57316\Downloads\coinciden_npn_codigo.csv", index=False)
codigo_distinto.to_csv(r"C:\Users\57316\Downloads\npn_mismo_codigo_diferente.csv", index=False)
no_existen.to_csv(r"C:\Users\57316\Downloads\no_existen_en_archivo2.csv", index=False)

# ------------------------------
# Resumen
# ------------------------------
print("✅ Comparación finalizada.")
print(f"- Coincidencias exactas: {len(coinciden)}")
print(f"- npn iguales pero código diferente: {len(codigo_distinto)}")
print(f"- Registros únicos en archivo1 que no están en archivo2: {len(no_existen)}")
