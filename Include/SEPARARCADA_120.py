import pandas as pd
import os

# Ruta absoluta del archivo original
ruta_excel = r"D:\TRABAJO_VA_GEOINFORMATCA\PSNR_DIGITACION_1_actualizado_modificado1.xlsx"

# Directorio donde se encuentra el archivo original
directorio = os.path.dirname(ruta_excel)

# Leer todas las hojas del Excel
excel_dict = pd.read_excel(ruta_excel, sheet_name=None)

# Verificar que la hoja "predio" exista
if 'predio' not in excel_dict:
    print("La hoja 'predio' no se encontró en el archivo.")
else:
    # Obtener el DataFrame de la hoja "predio"
    df_predio = excel_dict['predio']
    
    # Cantidad de filas en la hoja "predio"
    total_filas = len(df_predio)
    
    # Definir el tamaño del chunk (120 filas)
    chunk_size = 120
    
    # Crear los trozos (chunks) de 120 filas cada uno
    chunks = [df_predio.iloc[i:i + chunk_size] for i in range(0, total_filas, chunk_size)]
    
    # Procesar cada chunk
    for index, chunk in enumerate(chunks, start=1):
        # Definir el rango de filas (considerando que la primera fila de datos es la 1)
        fila_inicio = (index - 1) * chunk_size + 1
        fila_fin = fila_inicio + len(chunk) - 1
        
        # Construir el nuevo diccionario de hojas
        nuevo_excel = {}
        # Reemplazamos la hoja "predio" por el chunk actual
        nuevo_excel['predio'] = chunk
        
        # Agregar el resto de hojas sin modificaciones
        for sheet_name, df in excel_dict.items():
            if sheet_name != 'predio':
                nuevo_excel[sheet_name] = df
        
        # Definir el nombre del nuevo archivo (por ejemplo, "archivo_1_120.xlsx")
        nuevo_nombre = f'archivo_{fila_inicio}_{fila_fin}.xlsx'
        ruta_salida = os.path.join(directorio, nuevo_nombre)
        
        # Guardar el nuevo Excel con pandas (sin conservar formatos originales)
        with pd.ExcelWriter(ruta_salida, engine='xlsxwriter') as writer:
            for hoja, df in nuevo_excel.items():
                df.to_excel(writer, sheet_name=hoja, index=False)
        
        print(f"Archivo guardado: {ruta_salida}")
