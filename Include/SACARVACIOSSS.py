import pandas as pd

# ------------------------------------------------------------ #
# RUTAS DE ENTRADA Y SALIDA
# ------------------------------------------------------------ #
archivo_entrada = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTAS_CARTAGO_30_05\inconsistentes_npn.xlsx"
archivo_salida = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTAS_CARTAGO_30_05\inconsistentes_npn_con_sin_dominante.xlsx"

# ------------------------------------------------------------ #
# 1. Cargar archivo original de inconsistencias
# ------------------------------------------------------------ #
print("→ Leyendo archivo de inconsistencias...")
df = pd.read_excel(archivo_entrada)

# ------------------------------------------------------------ #
# 2. Filtrar registros sin categoría dominante y con error de destino
# ------------------------------------------------------------ #
print("→ Filtrando registros sin unidad dominante...")
filtro = (df["ok_dominio_area"] == False) & (df["categoria_dominante"].isna())
df_sin_dominante = df[filtro]

# ------------------------------------------------------------ #
# 3. Guardar archivo con dos hojas: todos + filtrados
# ------------------------------------------------------------ #
print("→ Guardando nuevo archivo Excel con dos hojas...")
with pd.ExcelWriter(archivo_salida, engine="xlsxwriter") as writer:
    df.to_excel(writer, sheet_name="inconsistentes", index=False)
    df_sin_dominante.to_excel(writer, sheet_name="sin_dominante", index=False)

# ------------------------------------------------------------ #
# 4. Confirmación final
# ------------------------------------------------------------ #
print("✔️ Archivo exportado exitosamente:")
print("📄", archivo_salida)
