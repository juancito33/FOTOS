import pandas as pd
import re
import os
import glob

# -----------------------------------------------------
# Configuración: Define la ruta del archivo, hoja y columna
# -----------------------------------------------------
# Configurar la ruta del archivo, el nombre de la hoja y de la columna a revisar
ruta_archivo = r"D:\TRABAJO_VA_GEOINFORMATCA\LAURA1.xlsx"
#a = glob("D:\TRABAJO_VA_GEOINFORMATCA\*.csv")
#print(a)
nombre_hoja = 'interesado'
nombre_columna = 'segundo_apellido'
# -----------------------------------------------------
# Paso 1: Leer el archivo Excel
# -----------------------------------------------------
try:
    df = pd.read_excel(ruta_archivo, sheet_name=nombre_hoja)
except Exception as e:
    print(f"Error al leer el archivo: {e}")
    exit()

# -----------------------------------------------------
# Paso 2: Definir la función de validación
#   Se permite únicamente letras (mayúsculas y minúsculas) o cadena vacía.
#   La expresión regular usada es r'^[A-Za-z]*$', donde:
#       ^ y $: Anclan el inicio y final de la cadena.
#       [A-Za-z]*: Permite 0 o más letras.
# -----------------------------------------------------
patron = re.compile(r'^[A-Za-zñÑ\t ]*$')
#NUMEROS NO LETAS 
#patron = re.compile(r'^[0-9\-]*$')
#patron = re.compile(r'^[0-9a-zA-ZñÑáéíóúÁÉÍÓÚ\t\s\-.&() ]*$')# CARACTERES DEL DOMINIO RAZON SOCIAL

def caracteres_validos(texto):
    """
    Retorna True si 'texto' contiene únicamente letras (A-Z o a-z) sin acentos,
    sin números ni espacios/tabulados, o si está vacío.
    En caso de valores nulos, se considera cadena vacía.
    """
    if pd.isna(texto):
        texto = ""
    if not isinstance(texto, str):
        texto = str(texto)
    return bool(patron.fullmatch(texto))

# -----------------------------------------------------
# Paso 3: Aplicar la validación a la columna de interés
# -----------------------------------------------------
df['es_valido'] = df[nombre_columna].apply(caracteres_validos)

# -----------------------------------------------------
# Paso 4: Filtrar las filas que no cumplen la condición.
#         Es decir, aquellas que tienen "caracteres extraños" en la columna.
# -----------------------------------------------------
df_errores = df[~df['es_valido']]

# -----------------------------------------------------
# Paso 5: Guardar el resultado en un archivo CSV para su revisión
# -----------------------------------------------------
directorio = os.path.dirname(ruta_archivo)
ruta_csv = os.path.join(directorio, "filas_con_errores_segundo_nombre_archivocheq_1441_1560.csv")
df_errores.to_csv(ruta_csv, index=False)

# Mensajes en consola para confirmar el proceso
total_datos = len(df)
datos_invalidos = len(df_errores)
print(f"Total de filas analizadas en la columna '{nombre_columna}': {total_datos}")
print(f"Cantidad de filas con caracteres extraños: {datos_invalidos}")
print(f"El archivo CSV con los errores se ha guardado en: {ruta_csv}")
