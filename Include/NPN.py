import pandas as pd

# Cargar el CSV
csv_df = pd.read_csv(r"D:\TRABAJO_VA_GEOINFORMATCA\filas_con_errores_documento_identidad_1921_2035.csv", dtype={"predio_id": str})
csv_df['predio_id'] = csv_df['predio_id'].str.strip()

# Cargar la hoja 'predio' del Excel
excel_df = pd.read_excel(r"D:\TRABAJO_VA_GEOINFORMATCA\Copia de PSNR_DIGITACION.xlsx", sheet_name="predio", dtype=str)
excel_df.rename(columns=lambda x: x.strip(), inplace=True)
excel_df['id'] = excel_df['id'].str.strip()  # Asegura que no haya espacios

# Renombrar la columna 'id' a 'predio_id' para que coincidan
excel_df.rename(columns={'id': 'predio_id'}, inplace=True)

# Hacer el merge
resultado = pd.merge(csv_df, excel_df[['predio_id', 'npn']], on='predio_id', how='left')

# Guardar el archivo
#resultado.to_csv("resultado_con_npn_.csv", index=False)

resultado[['npn']].to_csv("solo_npn_filas_con_errores_documento_identidad_1921_2035.csv", index=False)
