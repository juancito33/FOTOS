import pandas as pd
import os

# -----------------------------------------------------
# PARTE 1: Leer el CSV y extraer la columna "predio_id"
# -----------------------------------------------------
# Definir la carpeta de trabajo y la ruta del CSV generado
directorio = r"D:\TRABAJO_MEJORAS_JESUS"
ruta_csv = os.path.join(directorio, "filas_con_errores_segundo_apellido_archivo_1441_1560.csv")

# Leer el archivo CSV
try:
    df_csv = pd.read_csv(ruta_csv)
except Exception as e:
    print(f"Error al leer el archivo CSV: {e}")
    exit()

# Verificar que exista la columna "predio_id"
if 'predio_id' not in df_csv.columns:
    print("La columna 'predio_id' no se encontró en el CSV.")
    exit()

# Extraer la columna "predio_id" y mostrar su contenido en consola
df_predio_id = df_csv[['predio_id']]
print("Contenido de la columna 'predio_id':")
print(df_predio_id)

# Obtener la lista de IDs a eliminar (valores únicos, sin nulos)
ids_a_eliminar = df_predio_id['predio_id'].dropna().unique().tolist()
print("\nIDs a eliminar:")
print(ids_a_eliminar)

# -----------------------------------------------------
# PARTE 2: Abrir el archivo Excel, eliminar filas con errores en ambas hojas, y guardar el resultado
# -----------------------------------------------------
# Definir la ruta del archivo Excel a procesar
ruta_excel = os.path.join(directorio, r"D:\TRABAJO_VA_GEOINFORMATCA\LAURA.xlsx")
# Definir la ruta para guardar el nuevo archivo Excel actualizado
ruta_nuevo_excel = os.path.join(directorio, r"D:\TRABAJO_VA_GEOINFORMATCA\LAURA1.xlsx")

# Leer todas las hojas del archivo Excel
try:
    workbook = pd.read_excel(ruta_excel, sheet_name=None)
except Exception as e:
    print(f"Error al leer el archivo Excel: {e}")
    exit()

# ---------------------------------------------------------------------------
# Actualización de la hoja "interesado": eliminar filas con errores (caracteres especiales)
# ---------------------------------------------------------------------------
if "interesado" not in workbook:
    print("La hoja 'interesado' no se encontró en el archivo Excel.")
    exit()

df_interesado = workbook["interesado"]
if 'predio_id' not in df_interesado.columns:
    print("La columna 'predio_id' no se encontró en la hoja 'interesado'.")
else:
    # Eliminar filas donde el valor de 'predio_id' esté en la lista de IDs a eliminar
    df_interesado_actualizado = df_interesado[~df_interesado['predio_id'].isin(ids_a_eliminar)]
    workbook["interesado"] = df_interesado_actualizado
    print("\nSe han eliminado los registros con caracteres especiales de la hoja 'interesado'.")

# ---------------------------------------------------------------------------
# Actualización de la hoja "predio": eliminar filas cuyo 'id' coincida con algún predio_id a eliminar
# ---------------------------------------------------------------------------
if "predio" not in workbook:
    print("La hoja 'predio' no se encontró en el archivo Excel.")
    exit()

df_predio = workbook["predio"]
if 'id' not in df_predio.columns:
    print("La columna 'id' no se encontró en la hoja 'predio'.")
else:
    df_predio_actualizado = df_predio[~df_predio['id'].isin(ids_a_eliminar)]
    workbook["predio"] = df_predio_actualizado
    print("\nSe han eliminado los registros correspondientes de la hoja 'predio'.")

# ---------------------------------------------------------------------------
# Guardar el archivo Excel actualizado con todas las hojas
# ---------------------------------------------------------------------------
try:
    with pd.ExcelWriter(ruta_nuevo_excel, engine="openpyxl") as writer:
        for hoja, data in workbook.items():
            data.to_excel(writer, sheet_name=hoja, index=False)
    print(f"\nEl archivo Excel actualizado se ha guardado en: {ruta_nuevo_excel}")
except Exception as e:
    print(f"Error al guardar el archivo Excel actualizado: {e}")
