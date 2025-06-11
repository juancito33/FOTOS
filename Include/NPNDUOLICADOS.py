import pandas as pd

# Ruta del archivo original
archivo = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTAS_CARTAGO_30_05\inconsistentes_npn.xlsx"

# Cargar el archivo Excel
df = pd.read_excel(archivo)

# Extraer NPN únicos con su primer destino asociado
npn_destino_unicos = df[['npn', 'destino']].drop_duplicates(subset='npn')

# Guardar en un nuevo archivo Excel
salida = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTAS_CARTAGO_30_05\unicos_destino.xlsx"
npn_destino_unicos.to_excel(salida, index=False)
