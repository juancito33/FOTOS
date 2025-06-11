# import pandas  as pd
# from pathlib import Path

# csv_path = Path(r"C:\Users\57316\Downloads\data-1746030485269.csv")
# xls_path = Path(r"D:\TRABAJO_VA_GEOINFORMATCA\predios_sin geom_general.xlsx")

# df_csv = pd.read_csv(csv_path, dtype={"npn":str})
# df_xls = pd.read_excel(xls_path, sheet_name=0, dtype={"npn":str})
# print("CSV ---> FILAS"  , len(df_csv),"COLUMNAS",       df_csv.columns.tolist())
# print("XLS ---> FILAS"  , len(df_xls),"COLUMNAS",       df_xls.columns.tolist())

# print("\nHEAD CSV:")
# print(df_csv["npn"].head(), "\n")
# print("HEAD XLS:")
# print(df_xls["npn"].head())
# #llavea = df_csv["npn"].astype(str)
# #llaveb = df_comparar["npn"].astype(str)

# #coincidencias = llavea.isin(llaveb).sum()
# #print(f"{coincidencias} coincidencias de {len(df_csv)} filas pero falta {len(df_comparar)}.")

# #df_coincidencia = df_csv[llavea.isin(llaveb)]
# #df_final = pd.merge(df_coincidencia,df_comparar, left_on="npn", right_on="npn", how="left")

# #df_final.to_excel("fusion.xlsx", index=False)
# #print("resultado guardado en fusion ")

# # Continuamos donde tienes df_csv y df_xls ya leídos
# llave_csv = df_csv["npn"].str.strip()
# llave_xls = df_xls["npn"].str.strip()

# print("Estadísticas de llaves ")
# print("· npn únicos en CSV :", llave_csv.nunique())
# print("· npn únicos en XLS :", llave_xls.nunique())

# # ¿Cuántos coinciden?
# coinciden_bool = llave_csv.isin(llave_xls)
# print("\n· Total coincidencias CSV→XLS :", coinciden_bool.sum())

# # Mostramos hasta 10 ejemplos de cada caso
# print("\nEjemplos en CSV que NO existen en XLS:")
# ej_csv_no = list(set(llave_csv) - set(llave_xls))[:10]
# print(ej_csv_no)

# print("\nEjemplos en XLS que NO existen en CSV:")
# ej_xls_no = list(set(llave_xls) - set(llave_csv))[:10]
# print(ej_xls_no)




























# import pandas as pd
# from pathlib import Path

# # 1. Rutas
# csv_path = Path(r"C:\Users\57316\Downloads\data-1746030485269.csv")
# xls_path = Path(r"D:\TRABAJO_VA_GEOINFORMATCA\predios_sin geom_general.xlsx")

# # 2. Leer archivos (forzamos npn a str)
# df_csv = pd.read_csv(csv_path,  dtype={"npn": str, "identificador": str})
# df_xls = pd.read_excel(xls_path, sheet_name=0,
#                        dtype={"npn": str, "identificador": str})

# # 3. Creamos una clave compuesta en ambos DataFrames
# df_csv["clave"] = df_csv["npn"] + "_" + df_csv["identificador"].str.strip()
# df_xls["clave"] = df_xls["npn"] + "_" + df_xls["identificador"].str.strip()

# # 4. Filtrar filas cuya clave SÓLO está en el CSV
# df_faltantes = df_csv[~df_csv["clave"].isin(df_xls["clave"])]

# print(f"▶ Combinaciones (npn, identificador) exclusivas del CSV: {len(df_faltantes)}")

# # 5. Guardar el resultado con todas las columnas del CSV
# df_faltantes.to_excel("faltantes_npn_identificador.xlsx", index=False)
# print("✅ Archivo 'faltantes_npn_identificador.xlsx' generado.")




















import pandas as pd
from pathlib import Path

# ───────────────────────────────────────────────
# 1. Rutas de entrada
# ───────────────────────────────────────────────
csv_path = Path(r"C:\Users\57316\Downloads\TERRENORE.csv")
xls_path = Path(r"D:\TRABAJO_VA_GEOINFORMATCA\predios_sin geom_general.xlsx")

# ───────────────────────────────────────────────
# 2. Cargar datos (forzamos texto en npn e identificador)
# ───────────────────────────────────────────────
df_csv = pd.read_csv(csv_path,
                     dtype={"npn": str, "area_total": str})

df_xls = pd.read_excel(xls_path, sheet_name=1,
                       dtype={"npn": str, "area_terreno": str})

# ───────────────────────────────────────────────
# 3. Clave compuesta = npn + identificador
# ───────────────────────────────────────────────
df_csv["clave"] = df_csv["npn"] + "_" + df_csv["area_total"].str.strip()
df_xls["clave"] = df_xls["npn"] + "_" + df_xls["area_terreno"].str.strip()

# ───────────────────────────────────────────────
# 4. Determinar coincidencias y exclusiones
# ───────────────────────────────────────────────
# a) Claves presentes en ambos
mascara_coinciden = df_csv["clave"].isin(df_xls["clave"])

# b) Archivos resultantes
df_coinciden   = df_csv[mascara_coinciden]                 # en ambos
df_solo_csv    = df_csv[~mascara_coinciden]                # sólo CSV
df_solo_excel  = df_xls[~df_xls["clave"].isin(df_csv["clave"])]  # sólo Excel

print("Filas coincidentes       :", len(df_coinciden))
print("Filas solo en CSV        :", len(df_solo_csv))
print("Filas solo en Excel      :", len(df_solo_excel))

# ───────────────────────────────────────────────
# 5. Guardar archivos de salida
# ───────────────────────────────────────────────
df_coinciden.to_excel("coinciden.xlsx",   index=False)
df_solo_csv.to_excel("solo_en_csv.xlsx",  index=False)
df_solo_excel.to_excel("solo_en_excel.xlsx", index=False)

print("✅ Se generaron: 'coinciden.xlsx', 'solo_en_csv.xlsx', 'solo_en_excel.xlsx'")
