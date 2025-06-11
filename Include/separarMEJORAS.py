import pandas as pd

# Ruta local del archivo
ruta_archivo = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\MATRICULAS.xlsx"

# Cargar la hoja 0 del archivo Excel
xls = pd.ExcelFile(ruta_archivo)
nombre_hoja_0 = xls.sheet_names[0]
df = xls.parse(nombre_hoja_0)

# Asegurarse de que la columna 'npn' sea tratada como cadena
df['npn'] = df['npn'].astype(str)

# Extraer el carácter en la posición 22 (índice 21)
df['caracter_22'] = df['npn'].str[21]

# Separar los registros
df_con_5_2 = df[df['caracter_22'].isin(['5', '2'])]
df_con_0 = df[df['caracter_22'] == '0']

# Guardar los resultados en nuevos archivos Excel
ruta_salida_5_2 = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\npn_con_5_2.xlsx"
ruta_salida_0 = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\npn_con_0.xlsx"

df_con_5_2.to_excel(ruta_salida_5_2, index=False)
df_con_0.to_excel(ruta_salida_0, index=False)

print("Archivos generados con éxito.")
