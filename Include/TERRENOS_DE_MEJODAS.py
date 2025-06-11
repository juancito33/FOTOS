import pandas as pd

# Leer el archivo Excel
archivo = r"D:\TRABAJO_MEJORAS_JESUS\R.xlsx" # <- cámbialo por tu ruta real
df = pd.read_excel(archivo)

def modificar_npn_viejo(npn):
    npn_str = str(npn)
    # Asegurar que tenga al menos 30 caracteres
    if len(npn_str) >= 30:
        lista = list(npn_str)
        lista[21] = '0'      # Posición 22 (índice 21 en Python)
        lista[28] = '0'      # Posición 29
        lista[29] = '0'      # Posición 30
        return ''.join(lista)
    return npn  # Devolver original si es muy corto

# Aplicar la función a la columna 'NPN VIEJO'
df['NPN VIEJO MODIFICADO'] = df['NPN VIEJO'].apply(modificar_npn_viejo)

# Guardar el resultado en un nuevo Excel
df.to_excel("npn_modificado_terrenos_sebastian.xlsx", index=False)
